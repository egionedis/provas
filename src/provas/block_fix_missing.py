from __future__ import annotations
from pathlib import Path
import re

# ----- Patterns -----
BANNER_RE = re.compile(r'^\s*##\s*Quest[ãa]o\s+(\d{1,4})\b', re.I)
SEP_RE    = re.compile(r'^\s*-{2,}\s*$', re.M)

# Alternatives like: "(A) ...", "A) ...", "a - ...", "A. ...", "A: ..."
# 🔧 widened to allow an optional leading '(' and ':' as a separator
ALT_RE    = re.compile(r'(?mi)^\s*\(?([A-Ea-e])\s*[\)\.\-–—:]\s+')

# Prompt cue (helps decide if the tail is a new question)
PROMPT_CUE = re.compile(r'(assinale|escolha|marque|analise|considere|indique|complete|correspond[ea])', re.I)

# ----- Helpers -----
def _read_blocks_file(folder: Path) -> tuple[Path, str]:
    # Prefer the dedup output, fallback to raw blocks
    for name in ("full_blocks_fix_dedup.md", "full_blocks.md"):
        p = folder / name
        if p.exists():
            return p, p.read_text(encoding="utf-8", errors="ignore")
    raise FileNotFoundError("full_blocks_fix_dedup.md (or full_blocks.md) not found")

def _split_blocks(text: str) -> list[str]:
    raw = [b.strip() for b in SEP_RE.split(text)]
    return [b for b in raw if b and BANNER_RE.search(b)]

def _qnum(block: str) -> int | None:
    m = BANNER_RE.search(block)
    return int(m.group(1)) if m else None

def _first_alt_cluster_end(lines: list[str], start_idx: int = 1) -> int | None:
    """
    Return the index (in 'lines') of the last line of the FIRST contiguous
    alternatives cluster (A..E). We search starting after the banner (default 1).
    """
    cluster_start = None
    cluster_end = None

    i = start_idx
    while i < len(lines):
        if ALT_RE.match(lines[i]):
            if cluster_start is None:
                cluster_start = i
            cluster_end = i
            i += 1
            continue
        else:
            # If we had started a cluster, it ends before this non-alt line
            if cluster_start is not None:
                break
        i += 1

    return cluster_end

def _has_prompt_cue(s: str) -> bool:
    return bool(PROMPT_CUE.search(s))

def _alt_count(s: str) -> int:
    # Unique letters among A..E
    letters = [m.group(1).upper() for m in ALT_RE.finditer(s)]
    return len(sorted(set([c for c in letters if c in {"A","B","C","D","E"}])))

def _looks_meaningful_tail(tail: str) -> bool:
    # If tail is empty or too tiny, bail
    t = tail.strip()
    if len(t) < 60:
        return False
    if _has_prompt_cue(t):
        return True
    if _alt_count(t) >= 2:
        return True
    if "![" in t:  # image indicates a new stem is likely starting
        return True
    # Long enough fallback
    return len(t) >= 200

def _rebuild(banner_q: int, head_body: str) -> str:
    head_body = head_body.strip()
    if not head_body:
        return f"## Questão {banner_q}"
    return f"## Questão {banner_q}\n{head_body}"

# ----- Core fixer -----
def _fix_missing_in_blocks(blocks: list[str]) -> tuple[list[str], list[str]]:
    """
    Try to repair missing numbers by splitting the previous block
    right after the first alternatives cluster.
    Returns (new_blocks, summary_lines)
    """
    summary: list[str] = []

    # Build index by number
    nums = [(_qnum(b), idx) for idx, b in enumerate(blocks)]
    nums = [(n, i) for (n, i) in nums if n is not None]
    if not nums:
        summary.append("- No '## Questão N' banners found — nothing to fix.")
        return blocks, summary

    # Work list so we can insert while iterating; we’ll loop until stable or 2 passes
    passes = 0
    changed = True
    while changed and passes < 2:
        changed = False
        passes += 1

        # Recompute map each pass
        nums = [(_qnum(b), idx) for idx, b in enumerate(blocks)]
        nums = [(n, i) for (n, i) in nums if n is not None]
        index_by_n = {n: i for n, i in nums}
        present = sorted(index_by_n.keys())

        # Find gaps between consecutive present numbers
        gaps = []
        for a, b in zip(present, present[1:]):
            if b > a + 1:
                gaps.extend(list(range(a + 1, b)))

        if not gaps:
            break

        for missing in gaps:
            prev_n = missing - 1
            if prev_n not in index_by_n:
                continue  # no previous block (we only split previous)
            prev_idx = index_by_n[prev_n]
            block = blocks[prev_idx]
            lines = block.splitlines()

            # find end of first alt cluster (after banner)
            end_idx = _first_alt_cluster_end(lines, start_idx=1)
            if end_idx is None:
                summary.append(f"- Q{missing}: could not split — previous Q{prev_n} has no alternatives cluster.")
                continue

            head = "\n".join(lines[:end_idx+1]).strip()
            tail = "\n".join(lines[end_idx+1:]).strip()

            if not _looks_meaningful_tail(tail):
                summary.append(f"- Q{missing}: tail after options in Q{prev_n} didn’t look like a new question.")
                continue

            # Build two blocks: keep prev_n head, create missing with tail
            new_prev = _rebuild(prev_n, "\n".join(head.splitlines()[1:]))  # drop banner in body
            new_missing = _rebuild(missing, tail)

            # Replace and insert
            blocks[prev_idx] = new_prev
            insert_pos = prev_idx + 1
            blocks.insert(insert_pos, new_missing)

            # Log a tiny diff snippet
            last_opt_line = lines[end_idx].strip()
            first_tail_line = (tail.splitlines()[0] if tail else "").strip()
            summary.append(
                f"- Filled Q{missing} by splitting Q{prev_n} after options:\n"
                f"    last option: {last_opt_line[:120]}\n"
                f"    tail start:  {first_tail_line[:120]}"
            )
            changed = True

    # Final unresolved gaps (if any)
    nums = [(_qnum(b), idx) for idx, b in enumerate(blocks)]
    nums = [(n, i) for (n, i) in nums if n is not None]
    present = sorted(set(n for n, _ in nums))
    unresolved = []
    for a, b in zip(present, present[1:]):
        if b > a + 1:
            unresolved.extend(list(range(a + 1, b)))
    if unresolved:
        summary.append(f"- Unresolved missing: {', '.join(map(str, unresolved))}")

    return blocks, summary

# ----- Public API -----
def fix_missing_one(folder: Path) -> bool:
    try:
        md_in_path, text = _read_blocks_file(folder)
    except FileNotFoundError:
        print(f"⚠️  Skipping {folder}: full_blocks_fix_dedup.md/full_blocks.md not found")
        return False

    blocks = _split_blocks(text)
    if not blocks:
        print(f"⚠️  Skipping {folder}: no '## Questão N' blocks in {md_in_path.name}")
        return False

    fixed_blocks, summary_lines = _fix_missing_in_blocks(blocks)

    out_md = folder / "full_blocks_fix_missing.md"
    out_sum = folder / "full_blocks_fix_missing_summary.md"

    joined = "----\n" + "\n----\n".join(fixed_blocks) + "\n----\n"
    out_md.write_text(joined, encoding="utf-8")

    sum_text = [
        "# Fix Missing Review",
        f"- input: {md_in_path.name}",
        f"- output: {out_md.name}",
        "",
    ] + (summary_lines or ["- No gaps found."])
    out_sum.write_text("\n".join(sum_text) + "\n", encoding="utf-8")

    print(f"[fix-missing] {folder.name}: in={len(blocks)} → out={len(fixed_blocks)} | wrote {out_md.name}")
    return True

def fix_missing_batch(base: Path):
    if not base.exists():
        print("❌ Base dir not found:", base)
        return

    # If base itself has blocks, just fix it
    try:
        _ = _read_blocks_file(base)
        fix_missing_one(base)
        return
    except FileNotFoundError:
        pass

    # Else iterate subfolders
    count = 0
    for test_folder in base.iterdir():
        if not test_folder.is_dir():
            continue
        try:
            _ = _read_blocks_file(test_folder)
        except FileNotFoundError:
            continue    
        if fix_missing_one(test_folder):
            count += 1
    if count:
        print(f"[done] fix-missing processed {count} folder(s)")
    else:
        print("⚠️  No folders with full_blocks_fix_dedup.md/full_blocks.md were found under", base)
