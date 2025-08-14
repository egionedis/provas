# src/provas/final_summary.py
from __future__ import annotations
import re, json
from pathlib import Path
from typing import List, Dict

def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def _read_expected_n(folder: Path) -> int:
    audit = folder / "final_audit_summary.json"
    if audit.exists():
        try:
            data = json.loads(_read_text(audit) or "{}")
            mode = data.get("expected_alt_count", {}).get("mode")
            if isinstance(mode, int) and 2 <= mode <= 7:
                return mode
        except Exception:
            pass
    # fallback parse from final summary
    final_sum = folder / "full_blocks_final_summary.md"
    if final_sum.exists():
        m = re.search(r'expected alternatives per question.*?:\s*(\d+)', _read_text(final_sum), re.I)
        if m:
            try:
                n = int(m.group(1))
                if 2 <= n <= 7: return n
            except Exception:
                pass
    return 5

def _load_status(folder: Path) -> Dict:
    p = folder / "full_blocks_final_status.json"
    if p.exists():
        try:
            return json.loads(_read_text(p) or "{}")
        except Exception:
            pass
    # compute minimal fallback
    return {
        "questions": {},
        "counts": {"ok": 0, "not": 0, "total": 0},
        "expected_alt_count": _read_expected_n(folder),
        "file": None,
        "output": None,
    }

def build_final_summary_md(folder: Path) -> Path:
    final_md   = folder / "full_blocks_final.md"
    final_sum  = folder / "full_blocks_final_summary.md"
    dedup_sum  = folder / "full_blocks_fix_dedup_summary.md"
    missing_sum= folder / "full_blocks_fix_missing_summary.md"
    audit_json = folder / "final_audit_summary.json"
    status_json= folder / "full_blocks_final_status.json"

    status = _load_status(folder)
    expected_n = status.get("expected_alt_count") or _read_expected_n(folder)

    parts: List[str] = []
    parts.append("# Final Pipeline Summary\n")

    # Basic header
    src_name = status.get("file") or "(unknown)"
    parts.append(f"- Source: **{src_name}**")
    parts.append(f"- Final output: **{final_md.name if final_md.exists() else 'full_blocks_final.md (missing)'}**")
    parts.append(f"- Expected alternatives per question: **{expected_n}**\n")

    # Step summaries
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

    # Final per-question status
    parts.append("## Final per-question status\n")
    counts = status.get("counts") or {}
    parts.append(f"- OK: **{counts.get('ok', 0)}** &nbsp;&nbsp; NOT: **{counts.get('not', 0)}** &nbsp;&nbsp; TOTAL: **{counts.get('total', 0)}**\n")

    questions = status.get("questions") or {}
    if questions:
        def _k(k: str) -> int:
            try: return int(k)
            except Exception: return 0
        header = "| Questão | Status |\n|:------:|:------:|"
        rows = [header] + [f"| {k} | {questions[k]} |" for k in sorted(questions.keys(), key=_k)]
        parts.append("\n".join(rows))
        parts.append("")

    out = folder / "final_summary.md"
    out.write_text("\n".join(parts), encoding="utf-8")
    return out

def _looks_like_exam_folder(p: Path) -> bool:
    return (p / "full_blocks_final.md").exists() or (p / "final_audit_summary.json").exists()

def _discover_exam_folders(base: Path) -> List[Path]:
    out: List[Path] = []
    for child in sorted([x for x in base.iterdir() if x.is_dir()]):
        if _looks_like_exam_folder(child):
            out.append(child)
    for p in base.rglob("full_blocks_final.md"):
        cand = p.parent
        if cand not in out and _looks_like_exam_folder(cand):
            out.append(cand)
    return out

def run(base: Path) -> None:
    base = base.resolve()
    if base.is_dir() and _looks_like_exam_folder(base):
        out = build_final_summary_md(base)
        print(f"[final-summary] {base}: wrote {out.name}")
        return
    if base.is_dir():
        folders = _discover_exam_folders(base)
        if not folders:
            print(f"[final-summary] No exam folders found under {base}")
            return
        for f in folders:
            out = build_final_summary_md(f)
            try: rel = f.relative_to(base)
            except Exception: rel = f
            print(f"[final-summary] {rel}: wrote {out.name}")
        print(f"[final-summary] processed {len(folders)} folder(s) under {base}")
        return
    print(f"[final-summary] Path is not a directory: {base}")
