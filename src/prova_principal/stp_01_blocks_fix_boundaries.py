#src/prova_principal/stp_01_blocks_fix_boundaries.py

from __future__ import annotations
from pathlib import Path
import re

# ====================== Question header detection (agnostic, PT-first) ======================

WORD_PAT = re.compile(r'(?:QUEST[ÃA]O|QUESTO(?:E|Õ)S?)', re.I)

def _parse_q_header(line: str):
    """
    Return (question_number:int, tail_text:str) if the line looks like a question header.
    'tail_text' is any content on the same line after the number (kept inside the block).
    """
    s = line.lstrip()
    with_hash = s.startswith('#')
    if with_hash:
        s = s.lstrip('#').strip()

    # "Questão 8 ..." / "QUESTÃO 12"
    m = re.match(rf'{WORD_PAT.pattern}\s*(\d{{1,4}})\b(.*)', s, re.I)
    if m:
        return int(m.group(1)), (m.group(2) or "").strip()

    # "# 01 ..." (heading that is just a number)
    if with_hash:
        m = re.match(r'(\d{1,4})\b(.*)', s)
        if m:
            return int(m.group(1)), (m.group(2) or "").strip()

    # "01 - ..." or "1– ..." (number + dash/em-dash). We DO NOT match "1." (dot) to avoid list items from instructions.
    m = re.match(r'(\d{1,4})\s*[-–—]\s*(.*)', s)
    if m:
        return int(m.group(1)), (m.group(2) or "").strip()

    return None


# ====================== Shared preamble detection (more phrasings, lists & ranges) ======================

RANGE_SEP = re.compile(r'[-–—]|\b(?:até|a|e|to|hasta|y)\b', re.I)
DIGITS    = re.compile(r'\d{1,4}')

# Resource nouns often used in markers
RESOURCE = r'(?:texto(?:s)?|poema(?:s)?|gr[áa]fico(?:s)?|tabela(?:s)?|mapa(?:s)?|figura(?:s)?|imagem(?:ens)?|ilustra[cç][aã]o(?:es)?|an[úu]ncio(?:s)?|cartum(?:s)?|charge(?:s)?|trecho(?:s)?)'

# Be generous with "questões" spellings: questões / questoes / questiones / questions / questione / questao(es)
QUEST_WORD = r'(?:quest(?:[õo]es|oes|iones|ions|ione?s?|ao(?:es)?)|questions?)'

# Start-anchored patterns that typically precede shared preambles
PRE_MARKER_PATTERNS = [
    # "Texto comum às questões 20 e 21:"
    re.compile(rf'^\s*#?\s*texto\s+comum\s+(?:a|às?)\s+{QUEST_WORD}', re.I),

    # "{Recurso} para as questões 10 e 11"
    re.compile(rf'^\s*#?\s*{RESOURCE}s?\s+para\s+(?:a|as)\s+{QUEST_WORD}', re.I),

    # "O {recurso} a seguir é referência/referencia para as questões ..."
    re.compile(rf'^\s*#?\s*o\s+{RESOURCE}\s+a\s+seguir\s+é\s+refer[êe]nci[ao]\s+para\s+as\s+{QUEST_WORD}', re.I),

    # Explicit fallback just for common typos/mixes:
    re.compile(r'^\s*#?\s*o\s+texto\s+a\s+seguir\s+é\s+refer[êe]nci[ao]\s+para\s+as\s+questiones?', re.I),

    # "O {recurso} a seguir/abaixo será usado/utilizado para responder às questões ..."
    re.compile(rf'^\s*#?\s*o\s+{RESOURCE}\s+(?:a\s+seguir|abaixo)\s+ser[áa]?\s+(?:usad[oa]s?|utilizad[oa]s?)\s+.*{QUEST_WORD}', re.I),

    # "Leia o(s) {recurso}(s) a seguir/abaixo para responder às questões ..."
    re.compile(rf'^\s*#?\s*leia\s+o?s?\s+{RESOURCE}s?\s+(?:a\s+seguir|abaixo)\s+.*{QUEST_WORD}', re.I),

    # "Com base no(s) {recurso}(s) a seguir/abaixo, responda às questões ..."
    re.compile(rf'^\s*#?\s*com\s+base\s+no?s?\s+{RESOURCE}s?\s+(?:a\s+seguir|abaixo)\s+.*{QUEST_WORD}', re.I),

    # "Considere o(s) {recurso}(s) a seguir/abaixo ..."
    re.compile(rf'^\s*#?\s*consider(?:e|em)\s+o?s?\s+{RESOURCE}s?\s+(?:a\s+seguir|abaixo)\s+.*{QUEST_WORD}', re.I),

    # "Para responder às questões X a Y, considere o texto a seguir"
    re.compile(rf'^\s*#?\s*para\s+responder\s+(?:a|às?)\s+{QUEST_WORD}', re.I),

    # "As questões X a Y referem-se ao {recurso}"
    re.compile(rf'^\s*#?\s*as\s+{QUEST_WORD}\s+.*referem-se\s+ao?\s+{RESOURCE}', re.I),

    # "Os itens X a Y referem-se ao texto ..."
    re.compile(r'^\s*#?\s*os\s+itens?\s+.*referem-se', re.I),
]


def _is_shared_preamble_marker(line: str) -> bool:
    if not any(p.search(line) for p in PRE_MARKER_PATTERNS):
        return False
    # Must include explicit question numbers somewhere on the marker line
    return bool(DIGITS.search(line))

def _targets_from_marker(line: str):
    nums = list(map(int, DIGITS.findall(line)))
    if not nums:
        return []
    # Range cue anywhere + at least 2 numbers → expand [first..last]
    if len(nums) >= 2 and RANGE_SEP.search(line):
        a, b = sorted((nums[0], nums[-1]))
        return list(range(a, b + 1))
    # Otherwise treat as explicit list (handles "34, 35, 36 e 37")
    return nums


# ====================== Section titles to drop (discipline headers etc.) ======================
SECTION_TITLE_PAT = re.compile(
    r'^\s*#\s*(?:'
    r'MATEM[ÁA]TICA|F[ÍI]SICA|QU[ÍI]MICA|BIOLOGIA|GEOGRAFIA|HIST[ÓO]RIA|'
    r'PORTUGU[ÊE]S|L[ÍI]NGUA\s+PORTUGUESA|INGL[ÊE]S|ESPANHOL|'
    r'CONHECIMENTOS\s+GERAIS|RASCUNHO|INSTRU[CÇ][ÕO]ES?|'
    r'FOLHA\s+DE\s+RESPOSTAS|RESPOSTAS|GABARITO|DECLARA[CÇ][ÃA]O|ASSINATURA'
    r')\b',
    re.I,
)

def _drop_line(line: str) -> bool:
    # Drop known section/discipline headers (only when formatted as headings)
    return bool(SECTION_TITLE_PAT.match(line))


# ====================== Heuristic to discard instruction-like blocks ======================
INSTR_HINTS = re.compile(
    r'(?:prova|caderno|cart[aã]o-?resposta|aplicador(?:es)?|sala de prova|'
    r'autoriza[cç][aã]o|tempo de prova|folha de respostas|'
    r'detetor|detector\s+de\s+metais|processo\s+seletivo|assin(e|atura)|port[aã]o\s+de\s+sa[ií]da|'
    r'instru[cç][oõ]es?|regras?|desclassificad[oa])',
    re.I,
)
QUESTION_HINTS = re.compile(
    r'(?:assinale|considere|calcule|determine|qual(?:\s+é)?|quais|sabendo|no\s+plano|'
    r'gr[áa]fico|figura|tabela|mapa|texto|observe|analise|responda)',
    re.I,
)

def _looks_like_instruction(block_body: str) -> bool:
    """
    If the block body has multiple instruction hints and few/no question hints, treat as instructions.
    Also if it contains a RESPOSTAS board/table, treat as instructions.
    """
    body = block_body.lower()
    if 'respostas' in body and '</table>' in body:
        return True
    instr = len(INSTR_HINTS.findall(body))
    ques  = len(QUESTION_HINTS.findall(body))
    # Heuristic: plenty of instruction terms and almost no question terms → instruction
    return instr >= 3 and ques == 0


# ====================== Blocks splitter (normalize header, attach preambles, drop junk) ======================
def blocks_one(md_in: Path, md_out: Path):
    lines = md_in.read_text(encoding="utf-8", errors="ignore").splitlines()

    # 1) collect shared preambles (store only BODY; exclude the marker line)
    pre_map: dict[int, str] = {}
    pre_marker_idxs: list[int] = []
    i = 0
    while i < len(lines):
        if _is_shared_preamble_marker(lines[i]):
            start = i
            targets = _targets_from_marker(lines[i])
            j = i + 1
            while j < len(lines) and not (_is_shared_preamble_marker(lines[j]) or _parse_q_header(lines[j])):
                j += 1
            body_only = "\n".join(lines[start + 1:j]).rstrip()
            for q in targets:
                pre_map[q] = body_only  # last one wins if overlapping
            pre_marker_idxs.append(start)
            i = j
        else:
            i += 1
    pre_marker_idxs.sort()

    # 2) collect all question headers (keep duplicates & mixed styles)
    heads: list[tuple[int, int, str]] = []
    for idx, ln in enumerate(lines):
        h = _parse_q_header(ln)
        if h:
            qn, tail = h
            heads.append((idx, qn, tail))

    if not heads:
        print("⚠️ No question headers found; nothing written.")
        return

    # 3) Boundaries are each question header + each preamble marker
    boundaries = sorted([idx for idx, *_ in heads] + pre_marker_idxs)

    def next_boundary_after(pos: int) -> int:
        for b in boundaries:
            if b > pos:
                return b
        return len(lines)

    sep = "----"
    chunks: list[str] = []

    for h_idx, qn, tail in heads:
        end = next_boundary_after(h_idx)
        block_lines = lines[h_idx:end]
        if not block_lines:
            continue

        # Normalize header banner
        banner = f"## Questão {qn}"

        # Drop the original header line from the body
        tail_lines = block_lines[1:]

        # Drop discipline/section headers inside the slice
        tail_lines = [ln for ln in tail_lines if not _drop_line(ln)]

        # Assemble current raw body (without preamble yet)
        raw_body = "\n".join(tail_lines).strip()

        # Skip if this "question" is actually an instruction block
        if _looks_like_instruction(raw_body):
            continue

        # Attach shared preamble (repeat in every mapped question).
        pre = (pre_map.get(qn) or "").rstrip()

        # If the preamble content already exists inside the question slice, remove it there
        if pre and pre in raw_body:
            raw_body = raw_body.replace(pre, "").strip()

        # Rebuild tail_lines from (possibly deduped) raw_body
        tail_lines = raw_body.splitlines() if raw_body else []

        # Trim leading empties in remaining body
        while tail_lines and not tail_lines[0].strip():
            tail_lines.pop(0)

        parts = [banner]

        #Place preamble ABOVE any question text
        if pre:
            parts += ["", pre]

        # If there was extra text on the same header line (e.g., "01 - enunciado..."), keep it AFTER preamble
        header_tail = (tail or "").strip()
        if header_tail:
            parts += ["", header_tail]

        # Then the rest of the question body
        if tail_lines:
            parts += [""] + tail_lines

        chunk = "\n".join(parts).rstrip()
        chunks.append(chunk)

    out_text = (sep + "\n") + ("\n".join(f"{c}\n{sep}" for c in chunks)) + "\n"
    md_out.write_text(out_text, encoding="utf-8")
    print(f"[ok] wrote {md_out}  (blocks: {len(chunks)})")


def blocks_batch(base_dir: Path):
    if not base_dir.exists():
        print("❌ Base dir not found:", base_dir); return
    count = 0
    for test_folder in sorted(base_dir.iterdir()):
        if not test_folder.is_dir():
            continue
        md_in  = test_folder / "full.md"
        md_out = test_folder / "prova_principal" / "full_blocks.md"
        if md_in.exists():
            try:
                md_out.parent.mkdir(parents=True, exist_ok=True)
                blocks_one(md_in, md_out)
                count += 1
            except Exception as e:
                print(f"❌ Error on {test_folder.name}: {e}")
        else:
            print(f"⚠️ Skipping {test_folder.name}: full.md not found")
    if count:
        print(f"[done] processed {count} folder(s)")

# -------------------------- quick single-file helper --------------------------
if __name__ == "__main__":
    md_in  = Path("/mnt/data/full.md")  
    md_out = Path("full_blocks.md")
    if md_in.exists():
        blocks_one(md_in, md_out)
    else:
        print("❌ Input not found:", md_in)
