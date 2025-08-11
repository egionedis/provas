from __future__ import annotations
import re, json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from .schema import Exam, Question, Alternative, ImageDesc

HDR = re.compile(r'^\s*##\s*Quest(?:ão|ao)\s+(\d+)\s*$', re.I)
ALT_LINE = re.compile(r'^\s*([A-Ea-e])\s*[\)\].:\-]\s+(.*\S)\s*$')
IMG_TAG = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
IMG_DESC_INLINE = re.compile(r'IMG_DESC_START\s*:(.*?)IMG_DESC_END')

def _split_blocks(md_text: str) -> List[Tuple[int, List[str]]]:
    lines = md_text.splitlines()
    blocks, cur_qn, buf = [], None, []
    for line in lines:
        m = HDR.match(line)
        if m:
            if cur_qn is not None: blocks.append((cur_qn, buf))
            cur_qn = int(m.group(1)); buf = []
        else:
            if cur_qn is not None: buf.append(line)
    if cur_qn is not None: blocks.append((cur_qn, buf))
    return blocks

def _parse_block(qn: int, block_lines: List[str]) -> Dict[str, Any]:
    alt_start = None
    for i, line in enumerate(block_lines):
        if ALT_LINE.match(line):
            alt_start = i; break

    stmt_lines = block_lines if alt_start is None else block_lines[:alt_start]
    alt_lines  = [] if alt_start is None else block_lines[alt_start:]

    alts = []
    for line in alt_lines:
        m = ALT_LINE.match(line)
        if not m: break
        alts.append(Alternative(letter=m.group(1).upper(), text=m.group(2).strip()))

    images = []
    for idx, line in enumerate(stmt_lines):
        tag = IMG_TAG.search(line)
        if tag:
            src = tag.group(1).strip()
            desc = ""
            d = IMG_DESC_INLINE.search(line)
            if d: desc = d.group(1).strip()
            else:
                # try next/prev lines for IMG_DESC
                for neigh in [idx+1, idx-1]:
                    if 0 <= neigh < len(stmt_lines):
                        d2 = IMG_DESC_INLINE.search(stmt_lines[neigh])
                        if d2:
                            desc = d2.group(1).strip()
                            break
            images.append(ImageDesc(src=src, img_desc_raw=desc))

    return {
        "number": qn,
        "full_text": "\n".join(stmt_lines).strip(),
        "alternatives": [a.model_dump() for a in alts],
        "images": [i.model_dump() for i in images]
    }

def _validate_question(q: Dict[str, Any]) -> List[str]:
    warns: List[str] = []
    ft = (q.get("full_text") or "").strip()
    if not ft: warns.append("full_text is empty")

    alts = q.get("alternatives") or []
    letters = [a["letter"] for a in alts]
    texts   = [a.get("text","").strip() for a in alts]

    if any(not t for t in texts):
        warns.append("some alternatives have empty text")
    if len(set(letters)) != len(letters):
        warns.append("duplicate alternative letters")
    if letters and letters[0] != "A":
        warns.append(f"alternatives start at {letters[0]} (expected A)")
    if re.search(r'(^|\s)A\)', ft) and re.search(r'(^|\s)B\)', ft):
        warns.append("possible inline alternatives left in full_text")
    imgs = q.get("images") or []
    for im in imgs:
        if not im.get("img_desc_raw"):
            warns.append(f"image {im.get('src','?')} has no IMG_DESC")
    # heuristic: many MCQs have 4–5 options
    if "assinale" in ft.lower() and len(alts) < 4:
        warns.append(f"only {len(alts)} alternatives (often 4–5 expected)")
    return warns

def export_single(md_path: Path):
    if not md_path.exists():
        print(f"❌ Not found: {md_path}"); return
    exam_name = md_path.parent.name
    md = md_path.read_text(encoding="utf-8", errors="replace")
    blocks = _split_blocks(md)
    raw_qs = [_parse_block(qn, blines) for (qn, blines) in blocks]

    # Validate via schema
    questions = []
    for q in raw_qs:
        # coerce to models (will raise if invalid types)
        questions.append(Question(**q))

    exam = Exam(exam=exam_name, questions=questions)
    out_json = md_path.with_name("exam.json")
    out_json.write_text(exam.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Wrote {out_json}")

    # Write validation report
    warnings = {q.number: _validate_question(q.model_dump()) for q in questions if _validate_question(q.model_dump())}
    report = [
        f"Exam: {exam_name}",
        f"Total questions: {len(questions)}",
        f"Questions with warnings: {len(warnings)}",
        ""
    ]
    for num in sorted(warnings):
        report.append(f"## Questão {num}")
        for w in warnings[num]:
            report.append(f" - {w}")
        report.append("")
    (md_path.with_name("validation_report.txt")).write_text("\n".join(report).rstrip()+"\n", encoding="utf-8")
    print(f"📝 Wrote {md_path.with_name('validation_report.txt')}")

def export_batch(base: Path):
    for folder in base.iterdir():
        if not folder.is_dir(): continue
        md_path = folder / "full_regex.md"
        if md_path.exists():
            export_single(md_path)
        else:
            print(f"⚠️ Skipping {folder.name}: full_regex.md not found")
