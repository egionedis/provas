# src/provas/audit.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import Counter, defaultdict
import re, json

# ---------------- Banners & separators ----------------
BANNER = re.compile(r'^\s*##\s*Quest[ãa]o\s+(\d{1,4})\b', re.I)
SEP    = re.compile(r'^\s*-{2,}\s*$', re.M)

# ---------------- Alternatives detection ----------------
# STRICT (line start). Supports letters A–Z and digits 0–9 as labels:
# Matches lines like: "A) ...", "(b) ...", "C - ...", "D: ...", "1) ...", "2. ..."
ALT_LINE = re.compile(r'(?mi)^\s*[\(\[]?\s*(?P<label>[A-Za-z0-9])\s*[\)\]\.\:\-–—]\s+')

# INLINE (for packed-in-paragraph detection only)
ALT_INLINE_ANY = re.compile(r'(?i)([A-Za-z0-9])\s*[\)\]\.\:\-–—]\s+')

# ===== helpers =====

def _source_file(folder: Path) -> Optional[Path]:
    """
    Use **full_blocks_fix_missing.md** as the reference.
    Skip folder if it doesn't exist (no fallbacks here).
    """
    p = folder / "full_blocks_fix_missing.md"
    return p if p.exists() else None

def _split_blocks(text: str) -> List[str]:
    raw = [b.strip() for b in SEP.split(text)]
    return [b for b in raw if b and BANNER.search(b)]

def _qnum(block: str) -> Optional[int]:
    m = BANNER.search(block)
    return int(m.group(1)) if m else None

def _body_lines(block: str) -> List[str]:
    lines = block.splitlines()
    return lines[1:] if (lines and BANNER.match(lines[0])) else lines[:]

def _best_strict_alt_count(block: str) -> int:
    """
    Count the size of the LARGEST contiguous cluster of line-start alternatives
    anywhere in the block body (more robust than “first cluster”).
    - Allows any number of completely blank lines inside a cluster.
    - Stops a cluster when encountering a non-blank, non-alternative line.
    """
    lines = _body_lines(block)
    best = 0
    i = 0
    while i < len(lines):
        # Start a cluster where we see an alt line
        if ALT_LINE.match(lines[i]):
            count = 1
            j = i + 1
            while j < len(lines):
                if ALT_LINE.match(lines[j]):
                    count += 1
                    j += 1
                else:
                    # allow blank separators within the cluster
                    if lines[j].strip() == "":
                        j += 1
                        continue
                    break  # non-blank, non-alt => end of this cluster
            best = max(best, count)
            i = j
        else:
            i += 1
    return best

def _inline_label_span_count(block: str) -> int:
    """Count distinct inline labels anywhere (used when strict count == 0)."""
    return len({m.group(1).upper() for m in ALT_INLINE_ANY.finditer(block)})

def _collect_banners(text: str) -> List[Tuple[int, int]]:
    """(question_number, line_index) for duplicates/missing stats."""
    lines = text.splitlines()
    out = []
    for i, ln in enumerate(lines):
        m = BANNER.match(ln)
        if m:
            out.append((int(m.group(1)), i))
    return out

def _compact_ranges(nums: List[int]) -> List[List[int]]:
    """Given sorted missing numbers, return compact ranges [[a,b], ...]."""
    if not nums:
        return []
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        a, b = nums[i], nums[j]
        out.append([a, b])
        i = j + 1
    return out

# ===== core audit =====

def _audit_file(md_path: Path) -> Dict:
    """
    Audit full_blocks_fix_missing.md and produce a compact JSON with:
      - file, total_blocks
      - expected_alt_count: {mode, mode_support, histogram}
      - duplicates: { "65": 2, ... }
      - missing_between_ranges: [[a,b], ...]
      - few_alts: [{"q": N, "alt_count": k}, ...]  (STRICT < mode)
      - inline_only: [N, ...]                      (STRICT==0 and inline>=3)
      - no_alts: [N, ...]                          (STRICT==0 and inline<3)
    """
    text   = md_path.read_text(encoding="utf-8", errors="ignore")
    blocks = _split_blocks(text)

    # Per-question strict count (use BEST cluster anywhere in body)
    per_q_strict: Dict[int, int] = {}
    for b in blocks:
        qn = _qnum(b)
        if qn is None:
            continue
        per_q_strict[qn] = _best_strict_alt_count(b)

    # Histogram of strict sizes (>0 only) to infer exam-wide expected alternatives count
    sizes = [c for c in per_q_strict.values() if c > 0]
    hist_counter = Counter(sizes)
    # Serialize histogram with string keys for JSON
    histogram = {str(k): int(v) for k, v in sorted(hist_counter.items())}

    expected_mode = None
    mode_support  = 0
    if hist_counter:
        max_freq = max(hist_counter.values())
        # tie-break by larger size (e.g., prefer 5 over 4 if both appear equally)
        candidates = [s for s, f in hist_counter.items() if f == max_freq]
        expected_mode = max(candidates)
        mode_support  = hist_counter[expected_mode]

    # Duplicates & missing
    banners = _collect_banners(text)
    qnums_all = [n for (n, _) in banners]
    counts = defaultdict(int)
    for n in qnums_all:
        counts[n] += 1
    duplicates = {str(n): c for n, c in sorted(counts.items()) if c > 1}

    unique_qs = sorted(set(qnums_all))
    lo, hi = (min(unique_qs), max(unique_qs)) if unique_qs else (0, 0)
    missing_between = sorted(set(range(lo, hi + 1)) - set(unique_qs))
    missing_between_ranges = _compact_ranges(missing_between)

    # Classify problems
    few_alts: List[Dict[str, int]] = []
    inline_only: List[int]         = []
    no_alts: List[int]             = []

    # If no mode found at all, fall back to “4” as the common case
    fallback_mode = 4
    threshold = expected_mode if expected_mode is not None else fallback_mode

    for b in blocks:
        qn = _qnum(b)
        if qn is None:
            continue
        strict_n = per_q_strict.get(qn, 0)

        if strict_n == 0:
            # check inline packed labels
            inline_n = _inline_label_span_count(b)
            if inline_n >= 3:
                inline_only.append(qn)
            else:
                no_alts.append(qn)
        else:
            if strict_n < threshold:
                few_alts.append({"q": qn, "alt_count": strict_n})

    stats = {
        "file": md_path.name,
        "total_blocks": len(blocks),
        "expected_alt_count": {
            "mode": expected_mode,
            "mode_support": mode_support,
            "histogram": histogram,
        },
        "duplicates": duplicates,                          # {} if none
        "missing_between_ranges": missing_between_ranges,  # [] if none
        "few_alts": sorted(few_alts, key=lambda x: (x["q"], x["alt_count"])),
        "inline_only": sorted(inline_only),
        "no_alts": sorted(no_alts),
    }
    return stats

# ===== CLI =====

def final_audit_batch(base: Path) -> int:
    """
    CLI entry (keeps your existing name/shape).
    - If `base` itself has full_blocks_fix_missing.md, audit just this folder.
    - Else, audit each subfolder that contains full_blocks_fix_missing.md.
    Exit code is non-zero if any audited folder has problems.
    """
    if not base.exists():
        print("❌ Base dir not found:", base)
        return 1

    def _run_one(folder: Path) -> int:
        src = _source_file(folder)
        if not src:
            print(f"⚠️  Skipping {folder.name}: full_blocks_fix_missing.md not found")
            return 0

        stats = _audit_file(src)

        # Write JSON (primary) and a short markdown summary (optional for humans)
        (folder / "final_audit_summary.json").write_text(
            json.dumps(stats, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        md_lines = [
            "# Final Audit (problem-focused)",
            f"- source file: **{stats['file']}**",
            f"- total blocks: {stats['total_blocks']}",
            "",
            "## Expected alternatives pattern",
            f"- mode: {stats['expected_alt_count']['mode']}",
            f"- mode support: {stats['expected_alt_count']['mode_support']}",
            f"- histogram (strict > 0): {stats['expected_alt_count']['histogram']}",
            "",
            "## Structure checks",
            f"- duplicates: {stats['duplicates'] if stats['duplicates'] else 'none'}",
            f"- missing_between_ranges: {stats['missing_between_ranges'] if stats['missing_between_ranges'] else 'none'}",
            "",
            "## Problems",
            f"- few_alts: {len(stats['few_alts'])}",
            f"- inline_only: {len(stats['inline_only'])}",
            f"- no_alts: {len(stats['no_alts'])}",
            "",
        ]
        if stats["few_alts"]:
            md_lines.append("### few_alts")
            for item in stats["few_alts"]:
                md_lines.append(f"- Q{item['q']}: alt_count={item['alt_count']}")
            md_lines.append("")
        if stats["inline_only"]:
            md_lines.append("### inline_only")
            md_lines.append(", ".join(f"Q{q}" for q in stats["inline_only"]))
            md_lines.append("")
        if stats["no_alts"]:
            md_lines.append("### no_alts")
            md_lines.append(", ".join(f"Q{q}" for q in stats["no_alts"]))
            md_lines.append("")

        (folder / "final_audit_summary.md").write_text("\n".join(md_lines), encoding="utf-8")

        has_problems = bool(stats["few_alts"] or stats["inline_only"] or stats["no_alts"])
        print(f"[final-audit] {folder.name}: file={stats['file']} | "
              f"mode={stats['expected_alt_count']['mode']} | "
              f"few={len(stats['few_alts'])} | inline-only={len(stats['inline_only'])} | no-alts={len(stats['no_alts'])}")
        return 1 if has_problems else 0

    # Single-folder mode
    if _source_file(base):
        return _run_one(base)

    # Batch over subfolders
    total = 0
    bad   = 0
    for test_folder in sorted(p for p in base.iterdir() if p.is_dir()):
        if _source_file(test_folder):
            total += 1
            bad += _run_one(test_folder)

    if total == 0:
        print("⚠️  No folders with full_blocks_fix_missing.md were found under", base)
        return 1

    print(f"[done] audited {total} folder(s) | problems in {bad}")
    return 1 if bad else 0
