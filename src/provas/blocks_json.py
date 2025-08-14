# src/provas/full_blocks_json.py
from __future__ import annotations
import sys, re, json
from pathlib import Path
from typing import List, Tuple, Dict, Optional

# ----------- Patterns shared with your pipeline -----------
BANNER = re.compile(r'^\s*##\s*Quest[ãa]o\s+(\d{1,4})\b', re.I)
SEP    = re.compile(r'^\s*-{2,}\s*$', re.M)

# Letters-only alternatives, at line start (matches final formatted blocks)
ALT_LINE = re.compile(r'(?mi)^\s*[\(\[]?\s*([A-Za-z])\s*[\)\]\.\:\-–—]\s+.+$')

def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def _split_blocks(md_text: str) -> List[Tuple[int, str]]:
    """Return list of (qn, block_text) from a final MD like full_blocks_final.md."""
    raw = [b.strip() for b in SEP.split(md_text)]
    out: List[Tuple[int, str]] = []
    for b in raw:
        if not b:
            continue
        m = BANNER.match(b)
        if m:
            try:
                out.append((int(m.group(1)), b))
            except Exception:
                pass
    return out

def _alt_count_strict(block_text: str) -> int:
    """Count line-start lettered alternatives in a final block."""
    # Skip the first header line, count labeled lines until sequence ends
    lines = block_text.splitlines()
    body = lines[1:] if (lines and BANNER.match(lines[0])) else lines[:]
    started = False
    labels = 0
    for ln in body:
        if ALT_LINE.match(ln):
            started = True
            labels += 1
        else:
            if started:
                # allow blank lines inside cluster
                if ln.strip() == "":
                    continue
                break
    return labels

def _read_expected_n(folder: Path) -> int:
    """Prefer expected_alt_count.mode from final_audit_summary.json; fallback parse final summary; else 5."""
    audit_path = folder / "final_audit_summary.json"
    if audit_path.exists():
        try:
            audit = json.loads(_read_text(audit_path) or "{}")
            mode = audit.get("expected_alt_count", {}).get("mode")
            if isinstance(mode, int) and 2 <= mode <= 7:
                return mode
        except Exception:
            pass
    # fallback: try parse from full_blocks_final_summary.md
    final_sum = folder / "full_blocks_final_summary.md"
    if final_sum.exists():
        txt = _read_text(final_sum)
        m = re.search(r'expected alternatives per question.*?:\s*(\d+)', txt, re.I)
        if m:
            try:
                n = int(m.group(1))
                if 2 <= n <= 7:
                    return n
            except Exception:
                pass
    return 5

def build_status_json(folder: Path) -> Path:
    """Create full_blocks_final_status.json for all questions."""
    final_md = folder / "full_blocks_final.md"
    if not final_md.exists():
        # If final file doesn't exist, still produce an empty status with a reason
        payload = {
            "file": None,
            "output": "full_blocks_final.md (missing)",
            "expected_alt_count": None,
            "questions": {},
            "counts": {"ok": 0, "not": 0, "total": 0},
            "details": {},
            "error": "full_blocks_final.md not found"
        }
        out = folder / "full_blocks_final_status.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return out

    expected_n = _read_expected_n(folder)
    final_blocks = _split_blocks(_read_text(final_md))
    width = max(2, len(str(max((qn for qn, _ in final_blocks), default=0))))

    status_map: Dict[str, str] = {}
    details: Dict[str, Dict[str, int]] = {}
    ok_count = not_count = 0

    for qn, raw_block in final_blocks:
        after = _alt_count_strict(raw_block)
        st = "ok" if after == expected_n else "not"
        key = f"{qn:0{width}d}"
        status_map[key] = st
        details[key] = {"alts": after}
        if st == "ok":
            ok_count += 1
        else:
            not_count += 1

    # Try to extract original source filename from the audit
    src_name = None
    audit_path = folder / "final_audit_summary.json"
    if audit_path.exists():
        try:
            audit = json.loads(_read_text(audit_path) or "{}")
            src_name = audit.get("file")
        except Exception:
            pass

    payload = {
        "file": src_name,
        "output": final_md.name,
        "expected_alt_count": expected_n,
        "questions": status_map,                       # <-- { "01": "ok", "02": "ok", "03": "not", ... }
        "counts": {"ok": ok_count, "not": not_count, "total": len(final_blocks)},
        "details": details
    }
    out = folder / "full_blocks_final_status.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out

def build_pipeline_summary_md(folder: Path) -> Path:
    """Create pipeline_full_summary.md combining step summaries + final status table."""
    final_md = folder / "full_blocks_final.md"
    final_sum = folder / "full_blocks_final_summary.md"
    dedup_sum = folder / "full_blocks_fix_dedup_summary.md"
    missing_sum = folder / "full_blocks_fix_missing_summary.md"
    audit_json = folder / "final_audit_summary.json"
    status_json = folder / "full_blocks_final_status.json"

    # Ensure status exists
    if not status_json.exists():
        build_status_json(folder)

    # Load status
    try:
        status = json.loads(_read_text(status_json) or "{}")
    except Exception:
        status = {}

    expected_n = status.get("expected_alt_count", _read_expected_n(folder))

    # Compose
    parts: List[str] = []
    parts.append("# Pipeline Full Summary\n")
    src_name = status.get("file") or "(unknown)"
    parts.append(f"- Source: **{src_name}**")
    parts.append(f"- Final output: **{final_md.name if final_md.exists() else 'full_blocks_final.md (missing)'}**")
    parts.append(f"- Expected alternatives per question: **{expected_n}**\n")

    if dedup_sum.exists():
        parts.append("## Step: full_blocks_fix_dedup_summary.md")
        parts.append(_read_text(dedup_sum).strip() or "_(empty)_")
        parts.append("")
    else:
        parts.append("## Step: full_blocks_fix_dedup_summary.md\n*(missing)*\n")

    if missing_sum.exists():
        parts.append("## Step: full_blocks_fix_missing_summary.md")
        parts.append(_read_text(missing_sum).strip() or "_(empty)_")
        parts.append("")
    else:
        parts.append("## Step: full_blocks_fix_missing_summary.md\n*(missing)*\n")

    if audit_json.exists():
        try:
            audit = json.loads(_read_text(audit_json) or "{}")
            exp = audit.get("expected_alt_count", {})
            few = len(audit.get("few_alts") or [])
            ino = len(audit.get("inline_only") or [])
            noa = len(audit.get("no_alts") or [])
            parts.append("## Step: final_audit_summary.json (compact)")
            parts.append(f"- file: `{audit.get('file','')}`")
            parts.append(f"- expected_alt_count: `{exp}`")
            parts.append(f"- buckets: few_alts={few}, inline_only={ino}, no_alts={noa}\n")
        except Exception:
            parts.append("## Step: final_audit_summary.json (raw)")
            parts.append("```json")
            parts.append(_read_text(audit_json).strip())
            parts.append("```\n")
    else:
        parts.append("## Step: final_audit_summary.json\n*(missing)*\n")

    if final_sum.exists():
        parts.append("## Step: full_blocks_final_summary.md")
        parts.append(_read_text(final_sum).strip() or "_(empty)_")
        parts.append("")
    else:
        parts.append("## Step: full_blocks_final_summary.md\n*(missing)*\n")

    # Final per-question status table
    parts.append("## Final per-question status\n")
    counts = status.get("counts") or {}
    parts.append(f"- OK: **{counts.get('ok', 0)}** &nbsp;&nbsp; NOT: **{counts.get('not', 0)}** &nbsp;&nbsp; TOTAL: **{counts.get('total', 0)}**\n")

    questions = status.get("questions") or {}
    if questions:
        # Keep numeric ordering by question number
        def _qsort_key(k: str) -> int:
            try: return int(k)
            except Exception: return 0
        header = "| Questão | Status |\n|:------:|:------:|"
        rows = [header]
        for qk in sorted(questions.keys(), key=_qsort_key):
            rows.append(f"| {qk} | {questions[qk]} |")
        parts.append("\n".join(rows))
        parts.append("")

    out = folder / "pipeline_full_summary.md"
    out.write_text("\n".join(parts), encoding="utf-8")
    return out

def run(folder: Path) -> None:
    status_path = build_status_json(folder)
    pipeline_path = build_pipeline_summary_md(folder)
    print(f"[full_blocks_json] Wrote: {status_path.name}, {pipeline_path.name} in {folder}")

if __name__ == "__main__":
    base = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    run(base)
