from __future__ import annotations
from pathlib import Path
import re

# ---------------- Header & preamble detection ----------------
WORD_PAT = re.compile(r'(?:QUEST[ÃA]O|QUEST(?:ION(?:ES)?)?)', re.I)

def _parse_q_header(line: str):
    s = line.lstrip()
    with_hash = s.startswith('#')
    if with_hash:
        s = s.lstrip('#').strip()
    m = re.match(rf'{WORD_PAT.pattern}\s*(\d{{1,4}})(.*)', s, re.I)
    if m:
        return int(m.group(1)), m.group(2)
    if with_hash:
        m = re.match(r'(\d{1,4})(.*)', s)
        if m:
            return int(m.group(1)), m.group(2)
    m = re.match(r'(\d{1,4})\s*[-–]\s*(.*)', s)
    if m:
        return int(m.group(1)), m.group(2)
    return None

PRE_START = re.compile(
    r'^\s*#?\s*(?:'
    r'Texto\s+para\s+as\s+quest|'
    r'Texto\s+comum|'
    r'Para\s+responder|'
    r'El\s+texto\s+que\s+sigue|'
    r'O\s+texto\s+a\s+seguir|'
    r'O\s+texto\s+que\s+segue|'
    r'Itens?'
    r')',
    re.I,
)
QUEST_WORD = re.compile(r'(quest(?:[õo]es|iones?)|preguntas?|itens?|items?)', re.I)
DIGITS     = re.compile(r'\d{1,4}')
RANGE_SEP  = re.compile(r'[-–—]|(?:até|to|hasta|a|e|y)', re.I)

def _is_shared_preamble_marker(line: str) -> bool:
    return bool(PRE_START.search(line) and QUEST_WORD.search(line) and DIGITS.search(line))

def _targets_from_marker(line: str):
    nums = list(map(int, DIGITS.findall(line)))
    if not nums:
        return []
    if len(nums) >= 2 and RANGE_SEP.search(line):
        a, b = sorted((nums[0], nums[-1]))
        return list(range(a, b + 1))
    return nums

# ---------------- Blocks splitter (replace header with banner) ----------------
def blocks_one(md_in: Path, md_out: Path):
    lines = md_in.read_text(encoding="utf-8").splitlines()

    # 1) collect preambles (store only BODY; exclude marker line)
    pre_map: dict[int, str] = {}
    pre_idxs: list[int] = []
    i = 0
    while i < len(lines):
        if _is_shared_preamble_marker(lines[i]):
            pre_start = i
            targets = _targets_from_marker(lines[i])
            j = i + 1
            while j < len(lines) and not (_is_shared_preamble_marker(lines[j]) or _parse_q_header(lines[j])):
                j += 1
            body_only = "\n".join(lines[pre_start + 1:j]).rstrip()
            for q in targets:
                pre_map[q] = body_only  # last wins if overlapping
            pre_idxs.append(pre_start)  # still a boundary
            i = j
        else:
            i += 1
    pre_idxs.sort()

    # 2) collect all question headers (keep duplicates)
    heads: list[tuple[int, int]] = []
    for idx, ln in enumerate(lines):
        h = _parse_q_header(ln)
        if h:
            qn, _ = h
            heads.append((idx, qn))

    sep = "----"
    chunks: list[str] = []

    if heads:
        all_boundaries = sorted([idx for idx, _ in heads] + pre_idxs)

        def next_boundary_after(pos: int) -> int:
            for b in all_boundaries:
                if b > pos:
                    return b
            return len(lines)

        for h_idx, qn in heads:
            end = next_boundary_after(h_idx)

            # original slice for this question
            body_lines = lines[h_idx:end]
            if not body_lines:
                continue

            # REPLACE original header with normalized banner
            norm_banner = f"## Questão {qn}"
            tail_lines  = body_lines[1:]  # drop the original header line

            pre = (pre_map.get(qn) or "").rstrip()

            # assemble: banner, optional preamble body, then the rest
            block_parts = [norm_banner]
            if pre:
                block_parts += ["", pre]  # blank line, then preamble body
            # avoid accidental extra leading blank lines in tail
            while tail_lines and not tail_lines[0].strip():
                tail_lines = tail_lines[1:]
            if tail_lines:
                block_parts += [""] + tail_lines  # blank line, then tail
            block = "\n".join(block_parts).rstrip()

            chunks.append(block)
    else:
        # no headers → emit entire file (rare)
        chunks.append("\n".join(lines).rstrip())

    out_text = (sep + "\n") + ("\n".join(f"{c}\n{sep}" for c in chunks)) + "\n"
    md_out.write_text(out_text, encoding="utf-8")
    print(f"[ok] wrote {md_out}  (blocks: {len(chunks)})")

def blocks_batch(base_dir: Path):
    if not base_dir.exists():
        print("❌ Base dir not found:", base_dir); return
    count = 0
    for test_folder in base_dir.iterdir():
        if not test_folder.is_dir():
            continue
        md_in  = test_folder / "full.md"
        md_out = test_folder / "full_blocks.md"
        if md_in.exists():
            blocks_one(md_in, md_out)
            count += 1
        else:
            print(f"⚠️ Skipping {test_folder.name}: full.md not found")
    if count:
        print(f"[done] processed {count} folder(s)")
