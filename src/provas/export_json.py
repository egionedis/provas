# src/provas/export_json.py

from __future__ import annotations
import re, json, os
from pathlib import Path
from typing import List, Dict, Any, Tuple
from .schema import Exam, Question, Alternative, ImageDesc

# Azure OpenAI (text-only here)
from openai import AzureOpenAI

# =========================
# Patterns
# =========================
HDR = re.compile(r'^\s*##\s*Quest(?:ão|ao)\s+(\d+)\s*$', re.I)

# More permissive alternative header matcher
ALT_HEADER = re.compile(
    r'^\s*(?:\(\s*(?P<letter1>[A-Ea-e])\s*\)|(?P<letter2>[A-Ea-e])\s*(?:[\)\].:\-–—]))\s*(?P<text>.*\S)?\s*$'
)
SEP_LINE = re.compile(r'^\s*---\s*$')

IMG_TAG = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
IMG_DESC_INLINE = re.compile(r'IMG_DESC_START\s*:(.*?)IMG_DESC_END')

URL_RE   = re.compile(r'https?://\S+|\bwww\.\S+', re.I)
YEAR_RE  = re.compile(r'\b(1[5-9]\d{2}|20\d{2})\b')  # 1500–2099
CITY_PUBLISHER_RE = re.compile(r'\b[A-ZÁ-Ú][a-zá-ú]+(?:\s+[A-ZÁ-Ú][a-zá-ú]+)*:\s*[A-ZÁ-Ú]', re.U)
UPPER_SURNAME_RE  = re.compile(r'^[A-ZÁ-Ú]{2,}(?:[-\s][A-ZÁ-Ú]{2,})*,\s*[A-ZÁ-Ú]', re.U)
SIMPLE_CREDIT_RE  = re.compile(r'^[A-ZÁ-Ú][^.,\n]+(?:,\s*[^.,\n]+){0,3},\s*\d{4}\.?$', re.U)

# Headings like "Texto 1", "Texto 2" should be kept
TEXTO_HEADING = re.compile(r'^\s*#?\s*Texto\s+\d+\s*$', re.I)

# Expanded heuristic for detecting questions that should have alternatives
EXPECTS_ALTS = re.compile(
    r'(assinale|assimale|assinal|correto\s+afirmar|é\s+correto\s+afirmar|qual\s+(alternativa|situa[çc][aã]o)|'
    r'indique\s+a\s+alternativa|marque\s+a\s+alternativa)',
    re.I
)

# Strip leading label like "(A) ", "A) ", "A. ", "A - ", "A – ", etc.
_STRIP_LABEL_RE = re.compile(r'^\s*[\(\[]?\s*[A-Ea-e]\s*[\)\].:\-–—]\s*')

def _strip_leading_label(s: str) -> str:
    return _STRIP_LABEL_RE.sub('', s or '').strip()

# =========================
# LLM wrapper (STRICT extract-only; supports tables)
# =========================
class _LLM:
    """
    Strict extract-only helper using Azure OpenAI Chat Completions (no vision).
    For tabular options, returns each alternative as {'cells': [cell1, cell2, ...]}
    where EVERY cell is a literal substring of the raw block. We will join cells with ' — '.
    """

    def __init__(self):
        self.model = os.getenv("LLM_VISION_MODEL", "gpt-4o_dz-eu_2024-08-06")
        try:
            self.client = AzureOpenAI(
                api_key=os.getenv("GENAIHUB_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
                azure_endpoint=os.getenv("OPENAI_SDK_ENDPOINT"),
            )
            self.enabled = bool(self.client and self.model and os.getenv("GENAIHUB_API_KEY") and os.getenv("OPENAI_SDK_ENDPOINT"))
        except Exception:
            self.client = None
            self.enabled = False

    def fix_question(self, raw_block_text: str, parsed_full_text: str, parsed_alts: list[dict]) -> dict:
        """
        Return JSON:
          {
            "full_text": "<substring or empty>",
            "alternatives": [
              {"text": "<substring>"}           # non-table case
              OR
              {"cells": ["<substring>", "..."]} # table/multi-column case
            ]
          }
        All strings MUST be literal substrings of the raw block (verbatim).
        No rewriting, no invention, no translation.
        Only the FIRST contiguous set of labeled options (A–E). Max 5 items.
        """
        if not self.enabled:
            return {"full_text": "", "alternatives": []}

        system = (
            "Você é um assistente que **apenas EXTRAI** texto literal do bloco fornecido, sem inventar nada.\n"
            "Saída: **apenas JSON**. Não escreva nada além do JSON.\n"
            "Regras:\n"
            "1) 'full_text' deve ser um **substring exato** do bloco bruto que corresponda ao enunciado (sem imagens, créditos, URLs). "
            "   Se não for possível determinar, devolva string vazia.\n"
            "2) 'alternatives' deve conter **somente o primeiro conjunto contíguo** de alternativas rotuladas (A–E), **no máximo 5 itens**.\n"
            "3) Se as alternativas estiverem em **tabela ou layout de múltiplas colunas**, devolva cada uma como: {'cells': [cell1, cell2, ...]}, "
            "   onde cada cell é um **substring exato** do bloco bruto (ex.: relação ecológica, impacto imediato). "
            "   **Não inclua as letras (A), (B)... dentro de 'cells'**.\n"
            "4) Se estiverem em formato linear, devolva cada uma como: {'text': '<substring>'} — **sem o rótulo (A), (B)... no início**.\n"
            "5) NÃO reescreva, NÃO corrija, NÃO traduza, NÃO sintetize. Apenas copie substrings literais do bloco.\n"
        )

        user = {
            "raw_block": raw_block_text,
            "parsed_full_text": parsed_full_text,
            "parsed_alternatives": parsed_alts,
            "respond_with_schema": {
                "full_text": "substring or empty string",
                "alternatives": [
                    {"text": "substring"},
                    {"cells": ["substring", "substring (optional)"]}
                ]
            }
        }

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
                ],
                max_tokens=800,
            )
            out = resp.choices[0].message.content
            out = out.strip().strip("`")
            if out.lower().startswith("json"):
                out = out[4:].strip()
            data = json.loads(out)
            if not isinstance(data, dict):
                return {"full_text": "", "alternatives": []}
            return data
        except Exception:
            return {"full_text": "", "alternatives": []}

# =========================
# Split MD into question blocks
# =========================
def _split_blocks(md_text: str) -> List[Tuple[int, List[str]]]:
    lines = md_text.splitlines()
    blocks, cur_qn, buf = [], None, []
    for line in lines:
        m = HDR.match(line)
        if m:
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

# =========================
# Helpers
# =========================
def _is_citation_line(ln: str) -> bool:
    s = ln.strip()
    if not s:
        return False
    if TEXTO_HEADING.match(s):
        return False

    low = s.lower()

    if URL_RE.search(s):
        return True
    if any(k in low for k in ('disponível em', 'disponivel em', 'acesso em', 'acessado em',
                              '(adaptado)', 'adaptado', 'fonte', 'crédito', 'créditos',
                              'credito', 'creditos')):
        return True

    if YEAR_RE.search(s) and CITY_PUBLISHER_RE.search(s):
        return True

    if YEAR_RE.search(s) and UPPER_SURNAME_RE.search(s):
        return True

    if SIMPLE_CREDIT_RE.match(s):
        return True

    return False

def _strip_media_and_captions(lines: List[str]) -> List[str]:
    cleaned = []
    for ln in lines:
        if SEP_LINE.match(ln):
            continue
        if IMG_TAG.search(ln):
            continue
        if IMG_DESC_INLINE.search(ln):
            continue
        if _is_citation_line(ln):
            continue
        cleaned.append(ln)
    return cleaned

# =========================
# Parse a question block
# =========================
def _parse_block(qn: int, block_lines: List[str]) -> Dict[str, Any]:
    # Find where alternatives start
    alt_start = None
    for i, line in enumerate(block_lines):
        if ALT_HEADER.match(line):
            alt_start = i
            break

    # Raw statement region (includes images/captions before we clean)
    stmt_lines_raw = block_lines if alt_start is None else block_lines[:alt_start]
    stmt_lines_raw = [ln for ln in stmt_lines_raw if not SEP_LINE.match(ln)]

    # Extract images + descriptions from RAW lines
    images = []
    for idx, line in enumerate(stmt_lines_raw):
        tag = IMG_TAG.search(line)
        if tag:
            src = tag.group(1).strip()
            desc = ""
            d = IMG_DESC_INLINE.search(line)
            if d:
                desc = d.group(1).strip()
            else:
                for neigh in (idx + 1, idx - 1):
                    if 0 <= neigh < len(stmt_lines_raw):
                        d2 = IMG_DESC_INLINE.search(stmt_lines_raw[neigh])
                        if d2:
                            desc = d2.group(1).strip()
                            break
            images.append(ImageDesc(src=src, img_desc_raw=desc))

    # Clean statement text for full_text
    stmt_lines_clean = _strip_media_and_captions(stmt_lines_raw)

    # Parse alternatives (simple linear case). Tables will be handled by LLM if needed.
    alts = []
    if alt_start is not None:
        i = alt_start
        cur = None
        while i < len(block_lines):
            line = block_lines[i]
            if SEP_LINE.match(line):
                break
            m = ALT_HEADER.match(line)
            if m:
                if cur:
                    alts.append(cur)
                letter = (m.group('letter1') or m.group('letter2')).upper()
                text = (m.group('text') or '').strip()
                cur = Alternative(letter=letter, text=text)
            else:
                if cur:
                    s = line.strip()
                    if s:
                        cur.text = (cur.text + ' ' + s).strip()
                else:
                    break
            i += 1
        if cur:
            alts.append(cur)

    return {
        "number": qn,
        "full_text": "\n".join(stmt_lines_clean).strip(),
        "alternatives": [a.model_dump() for a in alts],
        "images": [i.model_dump() for i in images]
    }

# =========================
# Validation
# =========================
def _validate_question(q: Dict[str, Any]) -> List[str]:
    warns: List[str] = []
    ft = (q.get("full_text") or "").strip()

    alts = q.get("alternatives") or []
    letters = [a["letter"] for a in alts]
    texts = [a.get("text", "").strip() for a in alts]

    if not ft:
        warns.append("full_text is empty")
    if any(not t for t in texts):
        warns.append("some alternatives have empty text")
    if len(set(letters)) != len(letters):
        warns.append("duplicate alternative letters")
    if letters and letters[0] != "A":
        warns.append(f"alternatives start at {letters[0]} (expected A)")

    imgs = q.get("images") or []
    for im in imgs:
        if not im.get("img_desc_raw"):
            warns.append(f"image {im.get('src', '?')} has no IMG_DESC")

    if EXPECTS_ALTS.search(ft) and len(alts) < 4:
        warns.append(f"only {len(alts)} alternatives (often 4–5 expected)")

    return warns

def _should_llm_fix(warns: List[str]) -> bool:
    if not warns:
        return False
    for w in warns:
        lw = w.lower()
        if ("full_text is empty" in lw or
            "duplicate alternative letters" in lw or
            "alternatives start at" in lw or
            "only 0 alternatives" in lw or
            "only 1 alternatives" in lw or
            "only 2 alternatives" in lw or
            "only 3 alternatives" in lw):
            return True
    return False

def _apply_llm_corrections(questions: List[Question], raw_block_map: Dict[int, List[str]]) -> None:
    llm = _LLM()
    if not llm.enabled:
        return

    for q in questions:
        q_dict = q.model_dump()
        warns = _validate_question(q_dict)
        if not _should_llm_fix(warns):
            continue

        raw_lines = raw_block_map.get(q.number, [])
        raw_block_text = "\n".join(raw_lines)

        print(f"🔧 LLM extract-only fix → Questão {q.number}")

        fix_json = llm.fix_question(
            raw_block_text=raw_block_text,
            parsed_full_text=q.full_text,
            parsed_alts=[a.model_dump() for a in q.alternatives],
        )

        # FULL TEXT
        new_ft = (fix_json.get("full_text") or "").strip()
        if new_ft and new_ft in raw_block_text:
            q.full_text = new_ft

        # ALTERNATIVES
        raw_alts = fix_json.get("alternatives") or []
        pieces_based = []
        text_based = []

        for a in raw_alts:
            if isinstance(a, dict):
                if "cells" in a and isinstance(a["cells"], list) and a["cells"]:
                    # verify cells are literal substrings; then sanitize leading labels in each cell
                    cells = []
                    ok = True
                    for c in a["cells"]:
                        t = (c or "").strip()
                        if not t or t not in raw_block_text:
                            ok = False
                            break
                        cells.append(_strip_leading_label(t))  # <-- strip (A), A), etc in cells
                    if ok:
                        joined = " — ".join([t for t in cells if t])
                        joined = _strip_leading_label(joined)  # safety
                        if joined:
                            pieces_based.append(joined)
                elif "text" in a:
                    t = (a.get("text") or "").strip()
                    if t and (t in raw_block_text):
                        t = _strip_leading_label(t)  # <-- strip (A), A), etc
                        if t:
                            text_based.append(t)

        literal_texts: List[str] = pieces_based or text_based
        if not literal_texts:
            # fallback to current parsed alternatives; sanitize labels just in case
            literal_texts = [_strip_leading_label(a.text) for a in q.alternatives if a.text.strip()]

        # dedup, preserve order, cap at 5
        seen = set()
        norm_texts: List[str] = []
        for t in literal_texts:
            if t and t not in seen:
                seen.add(t)
                norm_texts.append(t)
                if len(norm_texts) == 5:
                    break

        # relabel to A..E
        if norm_texts:
            q.alternatives = [
                Alternative(letter=chr(ord('A') + i), text=t)
                for i, t in enumerate(norm_texts)
            ]

# =========================
# Exporters
# =========================
def export_single(md_path: Path):
    if not md_path.exists():
        print(f"❌ Not found: {md_path}")
        return
    exam_name = md_path.parent.name
    md = md_path.read_text(encoding="utf-8", errors="replace")

    blocks = _split_blocks(md)
    raw_block_map: Dict[int, List[str]] = {qn: blines for (qn, blines) in blocks}

    raw_qs = [_parse_block(qn, blines) for (qn, blines) in blocks]
    questions = [Question(**q) for q in raw_qs]

    # LLM corrections (strict extract-only with table support)
    _apply_llm_corrections(questions, raw_block_map)

    exam = Exam(exam=exam_name, questions=questions)

    out_json = md_path.with_name("exam.json")
    out_json.write_text(
        json.dumps(exam.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"✅ Wrote {out_json}")

    problems = {}
    for q in questions:
        w = _validate_question(q.model_dump())
        if w:
            problems[q.number] = w

    report = [
        f"Exam: {exam_name}",
        f"Total questions: {len(questions)}",
        f"Questions with warnings: {len(problems)}",
        ""
    ]
    for num in sorted(problems):
        report.append(f"## Questão {num}")
        for w in problems[num]:
            report.append(f" - {w}")
        report.append("")
    (md_path.with_name("validation_report.txt")).write_text(
        "\n".join(report).rstrip() + "\n", encoding="utf-8"
    )
    print(f"📝 Wrote {md_path.with_name('validation_report.txt')}")

def export_batch(base: Path):
    for folder in base.iterdir():
        if not folder.is_dir():
            continue
        md_path = folder / "full_regex.md"
        if md_path.exists():
            export_single(md_path)
        else:
            print(f"⚠️ Skipping {folder.name}: full_regex.md not found")
