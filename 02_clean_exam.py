# clean_exam.py

from dotenv import load_dotenv
import os
import re
import pathlib

load_dotenv()

# ──────────────────────────── 1. QUESTION HEADERS ─────────────────────────────
WORD_PAT = re.compile(r'(?:QUEST[ÃA]O|QUEST(?:ION(?:ES)?)?)', re.I)

def parse_q_header(line: str):
    s = line.lstrip()
    with_hash = s.startswith('#')
    if with_hash:
        s = s.lstrip('#').strip()

    # Word form  “QUESTÃO 5 …”  (dash optional)
    m = re.match(rf'{WORD_PAT.pattern}\s*(\d{{1,4}})(.*)', s, re.I)
    if m:
        num = int(m.group(1))
        trail = m.group(2).lstrip(' -–:').strip()
        return num, trail

    # Hash-numeric form  “# 47 …”  (dash optional)
    if with_hash:
        m = re.match(r'(\d{1,4})(.*)', s)
        if m:
            num = int(m.group(1))
            trail = m.group(2).lstrip(' -–:').strip()
            return num, trail

    # Bare numeric must have dash to be a header  “47 – Texto …”
    m = re.match(r'(\d{1,4})\s*[-–]\s*(.*)', s)
    if m:
        return int(m.group(1)), m.group(2).strip()

    return None


# ───────────────────────── 2. SHARED PREÂMBULOS ───────────────────────────────
PRE_PAT = re.compile(
    r'^\s*#?\s*'
    r'(?:O texto a seguir|O texto que segue|Texto comum\b|El texto que sigue|'
    r'Texto para as quest(?:[õo]es)?)',
    re.I,
)
DIGITS    = re.compile(r'\d+')
RANGE_SEP = re.compile(r'[-–—]|(?:até|to|hasta|a|e)', re.I)

def is_shared_preamble(line: str) -> bool:
    return bool(PRE_PAT.search(line) and DIGITS.search(line))


# ───────────────────────────── 3. EXTRACTOR ───────────────────────────────────
def extract_questions(path: str) -> str:
    with open(path, encoding='utf-8') as fh:
        lines = fh.read().splitlines()

    # 3-A  shared preambles
    pre_map, i = {}, 0
    while i < len(lines):
        if is_shared_preamble(lines[i]):
            nums = list(map(int, DIGITS.findall(lines[i])))
            if len(nums) >= 2 and RANGE_SEP.search(lines[i]):
                start, end = sorted((nums[0], nums[-1]))
            else:
                start = end = nums[0]
            j, buf = i + 1, []
            while j < len(lines) and not (is_shared_preamble(lines[j]) or parse_q_header(lines[j])):
                buf.append(lines[j]); j += 1
            txt = '\n'.join(buf).strip()
            for q in range(start, end + 1):
                pre_map[q] = txt
            i = j
        else:
            i += 1

    # 3-B  question bodies
    items, i = {}, 0
    while i < len(lines):
        head = parse_q_header(lines[i])
        if head:
            qn, trail = head
            buf = [trail] if trail else []
            j = i + 1
            while j < len(lines) and not (parse_q_header(lines[j]) or is_shared_preamble(lines[j])):
                buf.append(lines[j]); j += 1
            items[qn] = '\n'.join(buf).rstrip()
            i = j
        else:
            i += 1

    # 3-C  assemble markdown
    blocks = []
    for qn in sorted(items):
        seg = [f'## Questão {qn}']
        if pre_map.get(qn):
            seg.append(pre_map[qn])
        seg.append(items[qn])
        blocks.append('\n\n'.join(seg))

    return '\n\n---\n\n'.join(blocks)


# ─────────────────────────────── 4. BATCH DRIVER ──────────────────────────────
def main():
    base_dir = pathlib.Path("provas")
    if not base_dir.exists():
        raise FileNotFoundError("❌ Pasta 'provas' não encontrada.")

    for test_folder in base_dir.iterdir():
        if not test_folder.is_dir():
            continue

        inp = test_folder / "full_with_descriptions.md"
        out = test_folder / "full_regex.md"

        if inp.exists():
            print(f"🛠  Processing {test_folder.name} …")
            result = extract_questions(str(inp))
            out.write_text(result, encoding="utf-8")
            print(f"✅  Wrote {out}")
        else:
            print(f"⚠️  Skipping {test_folder.name}: {inp.name} not found")


if __name__ == "__main__":
    main()
