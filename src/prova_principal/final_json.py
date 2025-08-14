# src/provas/final_json.py
from __future__ import annotations
import re, json
from pathlib import Path
from typing import List, Tuple, Dict, Optional

# --- parse finalized blocks ---
BANNER   = re.compile(r'^\s*##\s*Quest[ãa]o\s+(\d{1,4})\b', re.I)
SEP      = re.compile(r'^\s*-{2,}\s*$', re.M)
ALT_LINE = re.compile(r'(?mi)^\s*[\(\[]?\s*([A-Za-z])\s*[\)\]\.\:\-–—]\s+(.+)$')
IMG_TAG  = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')

def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def _split_blocks(md_text: str) -> List[Tuple[int, str]]:
    out: List[Tuple[int, str]] = []
    for b in (x.strip() for x in SEP.split(md_text)):
        if not b: continue
        m = BANNER.match(b)
        if m:
            try: out.append((int(m.group(1)), b))
            except Exception: pass
    return out

def _first_image_url(block_text: str) -> str:
    m = IMG_TAG.search(block_text)
    return m.group(1) if m else ""

def _extract_stem_and_answers(block_text: str) -> Tuple[str, Dict[str, str]]:
    lines = block_text.splitlines()
    if lines and BANNER.match(lines[0]):
        lines = lines[1:]
    stem_lines: List[str] = []
    answers: Dict[str, str] = {}
    started = False
    for ln in lines:
        m = ALT_LINE.match(ln)
        if m:
            started = True
            answers[m.group(1).upper()] = m.group(2).strip()
        else:
            if not started:
                stem_lines.append(ln)
            else:
                if ln.strip():  # stop after contiguous alternatives
                    break
    return ("\n".join(stem_lines).strip(), answers)

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
    return 5

def _load_status_map(folder: Path, qwidth: int) -> Dict[str, str]:
    """{'01':'ok',...}, prefer full_blocks_final_status.json; else compute."""
    status_path = folder / "full_blocks_final_status.json"
    if status_path.exists():
        try:
            data = json.loads(_read_text(status_path) or "{}")
            qs = data.get("questions") or {}
            return {str(k).zfill(qwidth): v for k, v in qs.items()}
        except Exception:
            pass
    # fallback compute
    expected_n = _read_expected_n(folder)
    final_md = folder / "full_blocks_final.md"
    qs: Dict[str, str] = {}
    if final_md.exists():
        for qn, block in _split_blocks(_read_text(final_md)):
            # count contiguous alternatives
            alts = 0
            body = block.split("\n", 1)[1] if "\n" in block else ""
            for ln in body.splitlines():
                if ALT_LINE.match(ln):
                    alts += 1
                elif alts > 0 and ln.strip():
                    break
            qs[str(qn).zfill(qwidth)] = "ok" if alts == expected_n else "not"
    return qs

def build_final_json(folder: Path) -> Path:
    """Write final_blocks.json with the requested schema (subject fields inside each question)."""
    final_md = folder / "full_blocks_final.md"
    blocks = _split_blocks(_read_text(final_md))

    # parse test/year from folder name like "unicamp_2024"
    test = folder.name
    year: Optional[int] = None
    m = re.match(r'^(.*?)[\-_](\d{4})$', folder.name)
    if m:
        test = m.group(1)
        try: year = int(m.group(2))
        except Exception: year = None

    width = max(2, len(str(max((qn for qn, _ in blocks), default=0))))
    status_map = _load_status_map(folder, qwidth=width)

    qitems = []
    for qn, block in blocks:
        stem, answers = _extract_stem_and_answers(block)
        qitems.append({
            "question_number": qn,
            "subject": "",
            "subject_description": "",
            "structure": status_map.get(str(qn).zfill(width), "not"),
            "question": stem,
            "answers": answers,           # {"A": "...", "B": "...", ...}
            "correct_answer": "",
            "image": _first_image_url(block),
            "img_description": ""
        })

    payload = {
        "test": test,
        "year": year,
        "questions": qitems
    }
    out = folder / "final_blocks.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out

def _looks_like_exam_folder(p: Path) -> bool:
    return (p / "full_blocks_final.md").exists()

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
        out = build_final_json(base)
        print(f"[final-json] {base}: wrote {out.name}")
        return
    if base.is_dir():
        folders = _discover_exam_folders(base)
        if not folders:
            print(f"[final-json] No folders with full_blocks_final.md under {base}")
            return
        for f in folders:
            out = build_final_json(f)
            try: rel = f.relative_to(base)
            except Exception: rel = f
            print(f"[final-json] {rel}: wrote {out.name}")
        print(f"[final-json] processed {len(folders)} folder(s) under {base}")
        return
    print(f"[final-json] Path is not a directory: {base}")
