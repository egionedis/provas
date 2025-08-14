#blocks_fix_dedup.py
from __future__ import annotations
from pathlib import Path
import re
import difflib

BANNER = re.compile(r'^\s*##\s*Quest[ãa]o\s+(\d{1,4})\b', re.I)
SEP    = re.compile(r'^\s*-{2,}\s*$', re.M)

# Alternatives like:
# A) foo / a) foo / A - foo / A. foo
ALT_LINE = re.compile(r'(?mi)^\s*([A-Ea-e])\s*[\)\.\-–]\s+')
# Quick cue that looks like a prompt
PROMPT_CUE = re.compile(r'(assinale|escolha|marque|analise|considere|indique|complete|correspond[ea])', re.I)

# Instructional noise indicators (match >=2 strongly suggests "instructions")
INSTR_KEYWORDS = [
    "cartão-resposta", "cartao-resposta", "aplicador", "aplicação da prova", "aplicacao da prova",
    "sala de prova", "duração da prova", "duracao da prova", "detector de metais",
    "caderno de prova", "versão definitiva", "versao definitiva",
    "controle de respostas", "declaração de presença", "declaracao de presenca",
    "processo seletivo", "portão de saída", "portao de saida",
    "assin",  # assinar/assinatura/assine
    "prova",  # generic (works in combination with others)
    "gabarito", "turma", "inscrição", "inscricao", "candidato", "apresentar documento",
]

def _pick_blocks_file(folder: Path) -> Path | None:
    for name in ("full_blocks.md", "full_block.md"):
        p = folder / name
        if p.exists():
            return p
    return None

def _split_blocks(text: str) -> list[str]:
    raw = [b.strip() for b in SEP.split(text)]
    return [b for b in raw if b and BANNER.search(b)]

def _qnum_from_block(block: str) -> int | None:
    m = BANNER.search(block)
    return int(m.group(1)) if m else None

def _alt_count(block: str) -> int:
    letters = [m.group(1).upper() for m in ALT_LINE.finditer(block)]
    return len(sorted(set([c for c in letters if c in {"A","B","C","D","E"}])))

def _has_images(block: str) -> bool:
    return "![" in block or "![ " in block

def _has_prompt_cue(block: str) -> bool:
    lines = block.splitlines()
    body = "\n".join(lines[1:]) if len(lines) > 1 else ""
    return bool(PROMPT_CUE.search(body))

def _instruction_score(block: str) -> int:
    text = block.lower()
    hits = sum(1 for k in INSTR_KEYWORDS if k in text)
    many_lettered = len(re.findall(r'(?mi)^\s*[a-p]\s*[\)\.\-–]\s+', text)) >= 6
    return hits + (2 if many_lettered else 0)

def _looks_instruction(block: str) -> bool:
    score = _instruction_score(block)
    if score >= 2:
        return True
    if score >= 1 and not _has_prompt_cue(block):
        return True
    return False

def _normalize_for_sim(s: str) -> str:
    s = re.sub(r'^\s*##[^\n]*\n?', '', s, flags=re.M)  # drop banner
    s = re.sub(r'\s+', ' ', s)
    return s.strip().lower()

def _similar(a: str, b: str) -> float:
    return difflib.SequenceMatcher(a=_normalize_for_sim(a), b=_normalize_for_sim(b)).ratio()

def _score_block(block: str) -> tuple:
    # Higher is better
    return (
        _alt_count(block),            # prioritize having A..E options
        1 if _has_prompt_cue(block) else 0,
        1 if _has_images(block) else 0,
        len(block),                   # tie-break by length
    )

def _cleanup_block(block: str) -> str:
    """
    Remove echoed numeric header just below the banner, e.g. "65 - Assinale ..."
    """
    lines = block.splitlines()
    if not lines:
        return block
    banner = lines[0]
    rest = lines[1:]

    ECHO_PATS = [
        re.compile(r'^\s*\d{1,4}\s*[-–]\s+', re.I),
        re.compile(r'^\s*quest(?:[ãa]o)?\s*\d{1,4}\b', re.I),
    ]
    drop_n = 0
    for k in range(min(2, len(rest))):
        line = rest[k]
        if any(pat.search(line) for pat in ECHO_PATS):
            drop_n = k + 1
        else:
            break

    if drop_n:
        rest = rest[drop_n:]
    cleaned = "\n".join([banner] + rest).strip()
    return cleaned

def _summarize(s: str, n: int = 140) -> str:
    s = re.sub(r'^\s*##[^\n]*\n?', '', s, flags=re.M)
    s = re.sub(r'\s+', ' ', s).strip()
    return (s[:n] + "…") if len(s) > n else s

def fix_one(folder: Path) -> bool:
    md_in = _pick_blocks_file(folder)
    if not md_in:
        print(f"⚠️  Skipping {folder}: full_blocks.md not found")
        return False

    text = md_in.read_text(encoding="utf-8", errors="ignore")
    blocks = _split_blocks(text)
    if not blocks:
        print(f"⚠️  Skipping {folder}: no '## Questão N' blocks found in {md_in.name}")
        return False

    # Group and precompute metadata
    groups: dict[int, list[dict]] = {}
    for b in blocks:
        n = _qnum_from_block(b)
        if n is None:
            continue
        cleaned = _cleanup_block(b)
        meta = {
            "raw": b,
            "clean": cleaned,
            "len": len(cleaned),
            "alts": _alt_count(cleaned),
            "prompt": _has_prompt_cue(cleaned),
            "img": _has_images(cleaned),
            "instr_score": _instruction_score(cleaned),
            "looks_instr": _looks_instruction(cleaned),
            "score": _score_block(cleaned),
            "snippet": _summarize(cleaned),
        }
        groups.setdefault(n, []).append(meta)

    out_blocks = []
    deduped = 0
    instr_detected = 0

    # For simple Markdown summary
    summary_lines = [
        "# Fix Summary",
        "",
        f"- input: {md_in.name}",
        f"- output: full_blocks_fixed.md",
        f"- source blocks: {len(blocks)}",
        "",
    ]
    any_changes = False

    for qn in sorted(groups.keys()):
        items = groups[qn]
        before = len(items)

        # Choose kept
        non_instr = [m for m in items if not m["looks_instr"]]
        used_pool = non_instr if non_instr else items[:]  # keep something

        # pick by highest score
        kept = max(used_pool, key=lambda m: m["score"])
        kept_reason = "best score"
        if non_instr and any(m["looks_instr"] for m in items):
            kept_reason = "only non-instruction" if len(non_instr) == 1 else "best score among non-instruction blocks"

        # Build dropped list
        dropped = [m for m in items if m is not kept]
        deduped += max(0, before - 1)
        instr_detected += sum(1 for m in items if m["looks_instr"])
        out_blocks.append(kept["clean"].strip())

        # Only log when there was duplication or instruction-like stuff detected
        if before > 1 or any(m["looks_instr"] for m in items):
            any_changes = True
            summary_lines.append(f"## Questão {qn}")
            summary_lines.append("")
            summary_lines.append(f"**Kept** ({kept_reason}; len={kept['len']}, alts={kept['alts']}, "
                                 f"prompt={int(kept['prompt'])}, img={int(kept['img'])}, "
                                 f"instr_like={int(kept['looks_instr'])})")
            summary_lines.append("")
            summary_lines.append(f"> {kept['snippet']}")
            if dropped:
                summary_lines.append("")
                summary_lines.append("**Dropped**")
                for m in dropped:
                    reasons = []
                    if m["looks_instr"]:
                        reasons.append(f"instruction-like (score={m['instr_score']})")
                    if m["score"] < kept["score"]:
                        reasons.append("lower score")
                    sim = _similar(kept["clean"], m["clean"])
                    if sim >= 0.75:
                        reasons.append(f"near-duplicate (sim={sim:.2f})")
                    reason_txt = ", ".join(reasons) if reasons else "other"
                    summary_lines.append(f"- {reason_txt}; len={m['len']}, alts={m['alts']}, "
                                         f"prompt={int(m['prompt'])}, img={int(m['img'])}, "
                                         f"instr_like={int(m['looks_instr'])}")
                    summary_lines.append(f"  > {m['snippet']}")
            summary_lines.append("")

    md_out = folder / "full_blocks_fix_dedup.md"
    joined = "----\n" + "\n----\n".join(out_blocks) + "\n----\n"
    md_out.write_text(joined, encoding="utf-8")

    # Write simple summary markdown
    if not any_changes:
        summary_lines.append("_No deduplications or instruction-like drops detected._")
    summary_lines.insert(4, f"- output blocks: {len(out_blocks)}")
    summary_lines.insert(5, f"- deduped: {deduped}")
    summary_lines.insert(6, f"- instruction-like detected: {instr_detected}")

    summary_path = folder / "full_blocks_fix_dedup_summary.md"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print(f"[fix] {folder.name}: in={len(blocks)} blocks → out={len(out_blocks)} | "
          f"deduped={deduped} | instr_detected={instr_detected} | wrote {md_out.name} | summary: {summary_path.name}")
    return True

def fix_batch(base: Path):
    if not base.exists():
        print("❌ Base dir not found:", base)
        return

    # If base itself has full_blocks.md, fix just this folder
    single = _pick_blocks_file(base)
    if single:
        fix_one(base)
        return

    # Else iterate subfolders
    count = 0
    for test_folder in base.iterdir():
        if not test_folder.is_dir():
            continue
        if _pick_blocks_file(test_folder):
            if fix_one(test_folder):
                count += 1
    if count:
        print(f"[done] fixed {count} folder(s)")
    else:
        print("⚠️ No folders with full_blocks.md were found under", base)
