from __future__ import annotations
import re
from pathlib import Path

WORD_PAT = re.compile(r'(?:QUEST[ÃA]O|QUEST(?:ION(?:ES)?)?)', re.I)

def _parse_q_header(line: str):
    s = line.lstrip()
    with_hash = s.startswith('#')
    if with_hash: s = s.lstrip('#').strip()

    m = re.match(rf'{WORD_PAT.pattern}\s*(\d{{1,4}})(.*)', s, re.I)
    if m:
        num = int(m.group(1)); trail = m.group(2).lstrip(' -–:').strip()
        return num, trail

    if with_hash:
        m = re.match(r'(\d{1,4})(.*)', s)
        if m:
            num = int(m.group(1)); trail = m.group(2).lstrip(' -–:').strip()
            return num, trail

    m = re.match(r'(\d{1,4})\s*[-–]\s*(.*)', s)
    if m: return int(m.group(1)), m.group(2).strip()

    return None

PRE_PAT = re.compile(
    r'^\s*#?\s*'
    r'(?:O texto a seguir|O texto que segue|Texto comum\b|El texto que sigue|'
    r'Texto para as quest(?:[õo]es)?)',
    re.I,
)
DIGITS    = re.compile(r'\d+')
RANGE_SEP = re.compile(r'[-–—]|(?:até|to|hasta|a|e)', re.I)

def _is_shared_preamble(line: str) -> bool:
    return bool(PRE_PAT.search(line) and DIGITS.search(line))

ALT_LABELS = ["A)", "B)", "C)", "D)", "E)"]

def _strip_inline_alts(trail: str) -> str:
    if not trail: return trail
    up = trail.upper()
    if ("A)" not in up) or ("B)" not in up):
        return trail
    first_pos = min([up.find(l) for l in ALT_LABELS if up.find(l) != -1] or [None])  # earliest
    if first_pos is None: return trail
    return trail[:first_pos].rstrip()

def clean_one(md_in: Path, md_out: Path):
    lines = md_in.read_text(encoding='utf-8').splitlines()

    # preambles
    pre_map, i = {}, 0
    while i < len(lines):
        if _is_shared_preamble(lines[i]):
            nums = list(map(int, DIGITS.findall(lines[i])))
            if len(nums) >= 2 and RANGE_SEP.search(lines[i]):
                start, end = sorted((nums[0], nums[-1]))
            else:
                start = end = nums[0]
            j, buf = i + 1, []
            while j < len(lines) and not (_is_shared_preamble(lines[j]) or _parse_q_header(lines[j])):
                buf.append(lines[j]); j += 1
            txt = '\n'.join(buf).strip()
            for q in range(start, end + 1): pre_map[q] = txt
            i = j
        else:
            i += 1

    # bodies
    items, i = {}, 0
    while i < len(lines):
        head = _parse_q_header(lines[i])
        if head:
            qn, trail = head
            if trail: trail = _strip_inline_alts(trail)
            buf = [trail] if trail else []
            j = i + 1
            while j < len(lines) and not (_parse_q_header(lines[j]) or _is_shared_preamble(lines[j])):
                buf.append(lines[j]); j += 1
            items[qn] = '\n'.join(buf).rstrip()
            i = j
        else:
            i += 1

    # assemble
    blocks = []
    for qn in sorted(items):
        seg = [f'## Questão {qn}']
        if pre_map.get(qn): seg.append(pre_map[qn])
        seg.append(items[qn])
        blocks.append('\n\n'.join(seg))

    md_out.write_text('\n\n---\n\n'.join(blocks), encoding="utf-8")
    print(f"✅ Cleaned: {md_out}")

def clean_batch(base_dir: Path):
    if not base_dir.exists():
        print("❌ Base dir not found:", base_dir); return
    for test_folder in base_dir.iterdir():
        if not test_folder.is_dir(): continue
        md_in  = test_folder / "full_with_descriptions.md"
        md_out = test_folder / "full_regex.md"
        if md_in.exists():
            clean_one(md_in, md_out)
        else:
            print(f"⚠️ Skipping {test_folder.name}: full_with_descriptions.md not found")
