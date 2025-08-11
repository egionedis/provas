#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export per-test JSON from full_regex.md and write a validation report.

Usage:
  # single file
  python 04_export_json.py provas/<TEST>/full_regex.md

  # batch (all test folders under ./provas)
  python 04_export_json.py --batch

Output (for each test folder):
  - exam.json
  - validation_report.txt
"""

import sys
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

# ---------- Parsing utilities ----------

HDR = re.compile(r'^\s*##\s*Quest(?:ão|ao)\s+(\d+)\s*$', re.I)
ALT_LINE = re.compile(r'^\s*([A-Ea-e])\s*[\)\].:\-]\s+(.*\S)\s*$', re.U)
IMG_TAG = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')  # e.g., ![](images/foo.jpg)
IMG_DESC_INLINE = re.compile(r'IMG_DESC_START\s*:(.*?)IMG_DESC_END', re.U)

def split_blocks(md_text: str) -> List[Tuple[int, List[str]]]:
    """Split the full_regex.md into blocks keyed by question number."""
    lines = md_text.splitlines()
    blocks: List[Tuple[int, List[str]]] = []
    cur_qn = None
    buf: List[str] = []
    for line in lines:
        m = HDR.match(line)
        if m:
            # flush
            if cur_qn is not None:
                blocks.append((cur_qn, buf))
            cur_qn = int(m.group(1))
            buf = []
        else:
            if cur_qn is not None:
                buf.append(line)
    if cur_qn is not None:
        blocks.append((cur_qn, buf))
    return blocks

def parse_block_to_question(qn: int, block_lines: List[str]) -> Dict[str, Any]:
    """
    From a block (already after '## Questão N'), split statement vs alternatives,
    collect images, and return a question dict.
    """
    # Find where alternatives start (first line that matches ALT_LINE)
    alt_start = None
    for i, line in enumerate(block_lines):
        if ALT_LINE.match(line):
            alt_start = i
            break

    # Split statement vs alternatives
    stmt_lines = block_lines if alt_start is None else block_lines[:alt_start]
    alt_lines = [] if alt_start is None else block_lines[alt_start:]

    # Parse alternatives (contiguous A–E lines; ignore non-matching lines after first gap)
    alternatives = []
    for line in alt_lines:
        m = ALT_LINE.match(line)
        if not m:
            # stop at the first non-alt line after alternatives started
            # (avoids accidentally pulling footer/separators)
            break
        letter = m.group(1).upper()
        text = m.group(2).strip()
        alternatives.append({"letter": letter, "text": text})

    # Parse images in the statement lines (before alternatives)
    stmt_text = "\n".join(stmt_lines).strip()

    images = []
    # Find all image tags, attempt to capture a nearby IMG_DESC on the same line (common),
    # otherwise leave description empty (we’ll validate)
    for line in stmt_lines:
        tag_match = IMG_TAG.search(line)
        if tag_match:
            src = tag_match.group(1).strip()
            desc = ""
            # Try inline IMG_DESC on the same line
            d = IMG_DESC_INLINE.search(line)
            if d:
                desc = d.group(1).strip()
            images.append({"src": src, "img_desc_raw": desc})

        else:
            # Sometimes IMG_DESC is on its own line following the image line
            d = IMG_DESC_INLINE.search(line)
            if d:
                # attach to the last image if present and missing desc
                if images and not images[-1].get("img_desc_raw"):
                    images[-1]["img_desc_raw"] = d.group(1).strip()

    # Build full_text (statement only; alternatives kept separate)
    full_text = stmt_text

    return {
        "number": qn,
        "full_text": full_text,
        "alternatives": alternatives,
        "images": images
    }

# ---------- Validation ----------

def validate_question(q: Dict[str, Any]) -> List[str]:
    """
    Return a list of human-readable warnings for the question dict.
    """
    warns: List[str] = []
    num = q.get("number")

    # 1) full_text non-empty
    ft = (q.get("full_text") or "").strip()
    if not ft:
        warns.append("full_text is empty")

    # 2) alternatives sanity
    alts = q.get("alternatives") or []
    letters = [a.get("letter") for a in alts if a.get("letter")]
    texts = [a.get("text","").strip() for a in alts]

    # empty texts?
    for i, t in enumerate(texts, start=1):
        if not t:
            warns.append(f"alternative {letters[i-1] if i-1 < len(letters) else i} has empty text")

    # duplicate letters?
    if len(set(letters)) != len(letters):
        warns.append("duplicate alternative letters detected")

    # non A…E order / gaps
    if letters:
        expected = ["A","B","C","D","E"]
        # if it starts not from A, warn
        if letters[0] != "A":
            warns.append(f"alternatives start at {letters[0]} (expected A)")
        # if gaps exist (e.g., A,C,E)
        last_idx = -1
        for L in letters:
            if L in expected:
                idx = expected.index(L)
                if last_idx != -1 and idx != last_idx + 1:
                    warns.append("alternatives have gaps or out-of-order sequence")
                    break
                last_idx = idx

    # too few options? (heuristic)
    if "assinale" in ft.lower() and len(alts) < 4:
        warns.append(f"only {len(alts)} alternatives found (often 4–5 are expected)")

    # 3) inline options possibly inside statement (heuristic)
    # warn if we find A) and B) inside the statement text
    if re.search(r'(^|\s)A\)', ft) and re.search(r'(^|\s)B\)', ft):
        warns.append("possible inline alternatives left in full_text")

    # 4) image descriptions
    imgs = q.get("images") or []
    for img in imgs:
        if not img.get("img_desc_raw"):
            warns.append(f"image {img.get('src','?')} has no IMG_DESC")

    return warns

def validate_exam(exam: Dict[str, Any]) -> Dict[str, Any]:
    q_warnings = {}
    for q in exam.get("questions", []):
        warns = validate_question(q)
        if warns:
            q_warnings[q["number"]] = warns
    return {
        "total_questions": len(exam.get("questions", [])),
        "questions_with_warnings": len(q_warnings),
        "warnings": q_warnings
    }

# ---------- IO helpers ----------

def load_exam_md(md_path: Path) -> Dict[str, Any]:
    md = md_path.read_text(encoding="utf-8", errors="replace")
    blocks = split_blocks(md)
    questions = [parse_block_to_question(qn, lines) for (qn, lines) in blocks]
    exam_name = md_path.parent.name
    return {"exam": exam_name, "questions": questions}

def write_exam_json(exam: Dict[str, Any], out_path: Path):
    out_path.write_text(json.dumps(exam, ensure_ascii=False, indent=2), encoding="utf-8")

def write_report(report: Dict[str, Any], report_path: Path):
    lines = []
    lines.append(f"Exam: {report_path.parent.name}")
    lines.append(f"Total questions: {report['total_questions']}")
    lines.append(f"Questions with warnings: {report['questions_with_warnings']}")
    lines.append("")
    for qn in sorted(report["warnings"]):
        lines.append(f"## Questão {qn}")
        for w in report["warnings"][qn]:
            lines.append(f" - {w}")
        lines.append("")
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

# ---------- Main ----------

def process_single(md_path: Path):
    exam = load_exam_md(md_path)
    report = validate_exam(exam)
    out_json = md_path.with_name("exam.json")
    out_report = md_path.with_name("validation_report.txt")
    write_exam_json(exam, out_json)
    write_report(report, out_report)
    print(f"✅ Wrote {out_json}")
    print(f"📝 Wrote {out_report}")

def process_batch(base: Path):
    base = base if base else Path("provas")
    for test_folder in base.iterdir():
        if not test_folder.is_dir():
            continue
        md_path = test_folder / "full_regex.md"
        if md_path.exists():
            print(f"Processing {test_folder.name} …")
            process_single(md_path)
        else:
            print(f"⚠️  Skipping {test_folder.name}: full_regex.md not found")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)
    if args[0] == "--batch":
        process_batch(Path("provas"))
    else:
        md_path = Path(args[0])
        if not md_path.exists():
            print(f"❌ Not found: {md_path}")
            sys.exit(2)
        process_single(md_path)
