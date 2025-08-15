from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
import os, re, json
from html import unescape as _html_unescape

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    from llm_client.llm_client import chat as llm_chat
except Exception:
    llm_chat = None

BANNER = re.compile(r'^\s*##\s*Quest[ãa]o\s+(\d{1,4})\b', re.I)
SEP    = re.compile(r'^\s*-{2,}\s*$', re.M)

ALT_LINE = re.compile(r'(?mi)^\s*[\(\[]?\s*(?P<label>[A-Za-z])\s*[\)\]\.\:\-–—]\s*(?P<t>.+)$')
ALT_ANY  = re.compile(r'(?i)([A-Za-z])\s*[\)\]\.\:\-–—]\s*')
LETTER_ANCHOR = re.compile(r'(?i)(?<![A-Za-z0-9])\(?A\s*[\)\]\.\:\-–—]\s*')

TEXTO_HEADING = re.compile(r'^\s*#?\s*Texto\s+\d+\s*$', re.I)
IMG_TAG = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
IMG_DESC_INLINE = re.compile(r'IMG_DESC_START\s*:(.*?)IMG_DESC_END')
URL_RE = re.compile(r'https?://\S+|\bwww\.\S+', re.I)
TABLE_BLOCK = re.compile(r'(?is)<table\b.*?</table>')

# LaTeX masks (preserve length)
MATH_DOLLAR_INLINE  = re.compile(r'\$(?:\\.|[^$])+\$')
MATH_DOLLAR_BLOCK   = re.compile(r'\$\$(?:\\.|[^$])+\$\$', re.S)
MATH_PARENS         = re.compile(r'\\\((?:\\.|[^\\])*?\\\)')
MATH_BRACKETS       = re.compile(r'\\\[(?:\\.|[^\\])*?\\\]', re.S)

def _mask_span(s: str, a: int, b: int) -> str:
    return s[:a] + (' ' * (b - a)) + s[b:]

def _mask_math(s: str) -> str:
    for pat in (MATH_DOLLAR_BLOCK, MATH_BRACKETS, MATH_DOLLAR_INLINE, MATH_PARENS):
        for m in reversed(list(pat.finditer(s))):
            s = _mask_span(s, m.start(), m.end())
    return s

def _read_source_from_audit(folder: Path) -> tuple[Path, str, dict]:
    # --- CHANGE IS HERE ---
    search_dir = folder / "prova_principal"
    audit_path = search_dir / "final_audit_summary.json"
    if not audit_path.exists():
        raise FileNotFoundError("final_audit_summary.json not found")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))

    file_name = audit.get("file")
    if not file_name:
        raise FileNotFoundError("final_audit_summary.json missing 'file' field")

    src = search_dir / file_name
    if not src.exists():
        # Fallback to the default name if the one in the audit is wrong
        src = search_dir / "full_blocks_missing.md"
        if not src.exists():
            raise FileNotFoundError("no source blocks file (full_blocks_missing.md)")
    # --- END OF CHANGE ---
    return src, src.read_text(encoding="utf-8", errors="ignore"), audit

def _target_questions(audit: dict) -> Tuple[Set[int], Optional[int]]:
    targets: Set[int] = set()
    for item in (audit.get("few_alts") or []):
        try: targets.add(int(item.get("q")))
        except Exception: pass
    for q in (audit.get("inline_only") or []):
        try: targets.add(int(q))
        except Exception: pass
    for q in (audit.get("no_alts") or []):
        try: targets.add(int(q))
        except Exception: pass

    exp = audit.get("expected_alt_count") or {}
    mode = exp.get("mode")
    try:
        mode = int(mode) if mode is not None else None
    except Exception:
        mode = None
    return targets, mode

def _split_blocks(md_text: str) -> List[Tuple[int, str]]:
    raw = [b.strip() for b in SEP.split(md_text)]
    out: List[Tuple[int, str]] = []
    for b in raw:
        if not b: continue
        m = BANNER.match(b)
        if m:
            out.append((int(m.group(1)), b))
    return out

def _alt_count_strict(block_text: str) -> int:
    lines = block_text.splitlines()
    body = lines[1:] if (lines and BANNER.match(lines[0])) else lines[:]
    started = False
    labels = []
    for ln in body:
        m = ALT_LINE.match(ln)
        if m:
            started = True
            labels.append(m.group("label").upper())
        else:
            if started:
                if ln.strip() == "":  # allow blank
                    continue
                break
    return len(labels)

def _parse_block_return_body(block_text: str) -> str:
    lines = block_text.splitlines()
    body_lines = lines[1:] if (lines and BANNER.match(lines[0])) else lines[:]
    return "\n".join(body_lines)

def _is_meta_credit_line(ln: str) -> bool:
    s = ln.strip()
    if not s: return False
    if TEXTO_HEADING.match(s): return False
    low = s.lower()
    if URL_RE.search(s): return True
    if any(k in low for k in ('disponível em','disponivel em','acesso em','acessado em',
                              '(adaptado)','adaptado','fonte','crédito','créditos',
                              'credito','creditos')):
        return True
    return False

def _strip_tables(s: str) -> str:
    return TABLE_BLOCK.sub('', s)

def _clean_stem_text(raw: str) -> str:
    raw = _strip_tables(raw)
    lines = raw.splitlines()
    out = []
    for ln in lines:
        if IMG_TAG.search(ln) or IMG_DESC_INLINE.search(ln):
            continue
        if _is_meta_credit_line(ln):
            continue
        out.append(ln)
    return "\n".join(out).strip()

def _extract_label_token(s: str) -> Optional[str]:
    m = re.match(r'\s*[\(\[]?\s*([A-Za-z])\s*[\)\]\.\:\-–—]\s+', s)
    return m.group(1).upper() if m else None

def _labels_are_sequential(labeled: List[str], expected_n: int) -> bool:
    if not labeled or expected_n is None: return False
    if len(labeled) != expected_n: return False
    heads = []
    for s in labeled:
        tok = _extract_label_token(s)
        if tok is None: return False
        heads.append(tok)
    if heads[0] != "A":
        return False
    return all(heads[i] == chr(ord("A")+i) for i in range(expected_n))

def _render_html_to_text(s: str) -> str:
    s = re.sub(r'(?i)</\s*(tr|p|li)\s*>', '\n', s)
    s = re.sub(r'(?i)<\s*br\s*/?\s*>', '\n', s)
    s = re.sub(r'<[^>]+>', ' ', s)
    try: s = _html_unescape(s)
    except Exception: pass
    s = re.sub(r'[ \t\r\f\v]+', ' ', s)
    s = re.sub(r'\n\s*\n+', '\n\n', s)
    return s.strip()

def _first_alt_label_index(raw: str) -> int:
    masked = _mask_math(raw)
    m = LETTER_ANCHOR.search(masked)
    return m.start() if m else -1

def _has_textual_options(raw_body: str) -> Tuple[bool, Optional[str]]:
    if LETTER_ANCHOR.search(_mask_math(raw_body)):
        return True, None
    if '<table' in raw_body.lower():
        rendered = _render_html_to_text(raw_body)
        if LETTER_ANCHOR.search(_mask_math(rendered)):
            return True, rendered
        return False, rendered
    return False, None

def _compute_pre_until_label(raw_body: str, label_start: int) -> str:
    """Trim pre-stem ending right before label; drop a dangling '(' or '[' before the label."""
    if label_start <= 0:
        return ""
    end = label_start
    # remove just one opening bracket if it directly precedes the label
    if raw_body[end-1] in "([":  # keep ':' if any; only strip the bracket
        end -= 1
        # optional whitespace before that bracket
        while end > 0 and raw_body[end-1] in " \t":
            end -= 1
    return raw_body[:end]

def _split_inline_alternatives_strict(raw_body: str, expected_n: int) -> tuple[str, List[str]] | None:
    if expected_n is None or expected_n < 2: return None
    masked = _mask_math(raw_body)
    matches = list(ALT_ANY.finditer(masked))
    if not matches: return None
    start_idx = None
    for i, m in enumerate(matches):
        if m.group(1).upper() == "A":
            if m.start() > 0 and masked[m.start()-1].isalnum():  # boundary-safe
                continue
            start_idx = i; break
    if start_idx is None:
        return None

    seq = []
    cur = start_idx
    for step in range(expected_n):
        expect = chr(ord("A") + step)
        found = None
        for j in range(cur, len(matches)):
            tok = matches[j].group(1).upper()
            if tok == expect:
                if matches[j].start() > 0 and masked[matches[j].start()-1].isalnum():
                    continue
                found = j; break
        if found is None:
            return None
        seq.append(matches[found])
        cur = found + 1

    labeled: List[str] = []
    for k in range(len(seq)):
        s = seq[k].start()
        e = seq[k+1].start() if k+1 < len(seq) else len(masked)
        frag = raw_body[s:e].strip()
        if frag:
            labeled.append(frag)
    if not _labels_are_sequential(labeled, expected_n):
        return None
    pre = _compute_pre_until_label(raw_body, seq[0].start())
    return pre, labeled

def _split_inline_alternatives_relaxed(raw_body: str, expected_n: int) -> tuple[str, List[str]] | None:
    if expected_n is None or expected_n < 2: return None
    masked = _mask_math(raw_body)
    matches = list(ALT_ANY.finditer(masked))
    if not matches: return None

    a_idx = None
    for i, m in enumerate(matches):
        if m.group(1).upper() == "A":
            if m.start() > 0 and masked[m.start()-1].isalnum():
                continue
            a_idx = i; break
    if a_idx is None:
        return None

    found_idxs: Dict[str, int] = {}
    cur = a_idx
    while cur < len(matches) and len(found_idxs) < expected_n:
        m = matches[cur]
        if m.start() == 0 or not masked[m.start()-1].isalnum():
            tok = m.group(1).upper()
            if 'A' <= tok <= 'Z' and tok not in found_idxs:
                found_idxs[tok] = cur
        cur += 1
    if len(found_idxs) != expected_n:
        return None

    used = sorted(found_idxs.items(), key=lambda kv: matches[kv[1]].start())
    slices: Dict[str, str] = {}
    for idx_in_used, (tok, j) in enumerate(used):
        s = matches[j].start()
        e = matches[used[idx_in_used+1][1]].start() if idx_in_used+1 < len(used) else len(masked)
        frag = raw_body[s:e].strip()
        slices[tok] = frag

    ordered: List[str] = []
    for step in range(expected_n):
        label = chr(ord('A') + step)
        if label not in slices:
            return None
        payload = re.sub(r'^\s*[\(\[]?\s*[A-Za-z]\s*[\)\]\.\:\-–—]\s*', '', slices[label].strip())
        ordered.append(f"{label}) {payload}".strip())

    pre = _compute_pre_until_label(raw_body, matches[a_idx].start())
    return pre, ordered

class _LLM:
    def __init__(self):
        self.endpoint = os.getenv("OPENAI_SDK_ENDPOINT", "")
        self.api_key  = os.getenv("GENAIHUB_API_KEY", "")
        self.model    = os.getenv("LLM_MODEL", "gpt-4o-mini_dz-eu_2024-07-08")
        self.enabled  = bool(llm_chat and self.endpoint and self.api_key)
        self.disabled_reason = None
        if not llm_chat:
            self.disabled_reason = "llm_client not importable"
        elif not self.endpoint or not self.api_key:
            self.disabled_reason = "missing OPENAI_SDK_ENDPOINT/GENAIHUB_API_KEY"

    def recover_labeled(self, raw_body: str, rendered: Optional[str], expected_n: int) -> List[str]:
        if not self.enabled or expected_n is None or expected_n < 2:
            return []

        system = (
            "Extract multiple-choice alternatives from an exam block.\n"
            "Answers are letters only (A,B,C,...). Output ONLY JSON:\n"
            '{ "labeled_alternatives": ["A) ...", "B) ..."], "confidence": 0..1 }\n'
            f"- Return exactly {expected_n} items, starting at 'A)'.\n"
            "- Do NOT modify, paraphrase, shorten, or invent text.\n"
            "- Include full LaTeX if present ($...$ or \\( ... \\)).\n"
            "- Each line must be an EXACT contiguous substring of RAW or RENDERED.\n"
        )
        user = { "RAW": raw_body, "RENDERED": rendered or "", "expected_count": expected_n }

        try:
            resp = llm_chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
                ],
                max_tokens=900,
            )
            out = (resp.choices[0].message.content or "").strip().strip("`")
            if out.lower().startswith("json"): out = out[4:].strip()
            data = json.loads(out)
            seq = data.get("labeled_alternatives") or []
            if not isinstance(seq, list): return []

            clean: List[str] = []
            for t in seq:
                s = (t or "").strip()
                if not s: return []
                if not re.match(r'^\s*[\(\[]?\s*[A-Za-z]\s*[\)\]\.\:\-–—]\s+.+', s):
                    return []
                if (s in raw_body) or (rendered and s in rendered):
                    clean.append(s)
                else:
                    return []  # reject inventions

            return clean if _labels_are_sequential(clean, expected_n) and len(clean) == expected_n else []
        except Exception:
            return []

def _tidy_option_line(s: str) -> str:
    return re.sub(r'\s*\(\s*$', '', s.strip())

def _build_block(qn: int, stem_text: str, alt_labeled_lines: List[str], img_lines_pre: List[str]) -> str:
    parts = [f"## Questão {qn}"]
    if img_lines_pre:
        parts += img_lines_pre
        parts.append("")
    if stem_text.strip():
        parts.append(stem_text.strip())
        parts.append("")
    for s in alt_labeled_lines:
        parts.append(_tidy_option_line(s.lstrip()))
    return "\n".join([p for p in parts if p is not None]).strip()

def finalize_one_from_audit(folder: Path) -> bool:
    try:
        src_path, text, audit = _read_source_from_audit(folder)
    except FileNotFoundError as e:
        print(f"⚠️  Skipping {folder.name}: {e}")
        return False

    targets, expected_mode = _target_questions(audit)
    expected_n = expected_mode if (isinstance(expected_mode, int) and 2 <= expected_mode <= 7) else 5

    blocks = _split_blocks(text)
    if not blocks:
        print(f"⚠️  Skipping {folder.name}: no '## Questão N' blocks in {src_path.name}")
        return False

    out_blocks: List[str] = []
    fixed_info: List[str] = []
    unresolved: List[str] = []

    before_counts: Dict[int, int] = {qn: _alt_count_strict(raw) for qn, raw in blocks}
    llm = _LLM()

    for qn, raw_block in blocks:
        if qn not in targets:
            out_blocks.append(raw_block.strip())
            continue

        raw_body = _parse_block_return_body(raw_block)

        has_opts, rendered = _has_textual_options(raw_body)

        # 1) Strict inline
        inline = _split_inline_alternatives_strict(raw_body, expected_n=expected_n) if has_opts else None
        if inline:
            pre, labeled = inline
            img_lines_pre = [ln for ln in pre.splitlines() if IMG_TAG.search(ln)]
            stem_text = _clean_stem_text(pre)
            new_block = _build_block(qn, stem_text, labeled, img_lines_pre)
            after = _alt_count_strict(new_block)
            if after == expected_n:
                out_blocks.append(new_block.strip())
                fixed_info.append(f"- Q{qn}: STRICT {before_counts.get(qn,0)} → {after} (inline split)")
                continue

        # 1b) Relaxed inline
        inline_relaxed = _split_inline_alternatives_relaxed(raw_body, expected_n=expected_n) if has_opts else None
        if inline_relaxed:
            pre, labeled = inline_relaxed
            img_lines_pre = [ln for ln in pre.splitlines() if IMG_TAG.search(ln)]
            stem_text = _clean_stem_text(pre)
            new_block = _build_block(qn, stem_text, labeled, img_lines_pre)
            after = _alt_count_strict(new_block)
            if after == expected_n:
                out_blocks.append(new_block.strip())
                fixed_info.append(f"- Q{qn}: STRICT {before_counts.get(qn,0)} → {after} (inline split, relaxed)")
                continue

        # 1c) Rendered (tables)
        inline_norm = None
        if has_opts and rendered:
            inline_norm = _split_inline_alternatives_strict(rendered, expected_n=expected_n) \
                          or _split_inline_alternatives_relaxed(rendered, expected_n=expected_n)
        if inline_norm:
            _pre_norm, labeled_norm = inline_norm
            idx = _first_alt_label_index(raw_body)
            pre_raw = _compute_pre_until_label(raw_body, idx) if idx >= 0 else raw_body
            img_lines_pre = [ln for ln in pre_raw.splitlines() if IMG_TAG.search(ln)]
            stem_text = _clean_stem_text(pre_raw)
            new_block = _build_block(qn, stem_text, labeled_norm, img_lines_pre)
            after = _alt_count_strict(new_block)
            if after == expected_n:
                out_blocks.append(new_block.strip())
                fixed_info.append(f"- Q{qn}: STRICT {before_counts.get(qn,0)} → {after} (rendered-table split)")
                continue

        # 2) LLM organize (only if textual options exist)
        labeled_llm = llm.recover_labeled(raw_body, rendered, expected_n=expected_n) if has_opts else []
        if labeled_llm and len(labeled_llm) == expected_n:
            idx = _first_alt_label_index(raw_body)
            pre_raw = _compute_pre_until_label(raw_body, idx) if idx >= 0 else raw_body
            img_lines_pre = [ln for ln in pre_raw.splitlines() if IMG_TAG.search(ln)]
            stem_text = _clean_stem_text(pre_raw)
            new_block = _build_block(qn, stem_text, labeled_llm, img_lines_pre)
            after = _alt_count_strict(new_block)
            if after == expected_n:
                out_blocks.append(new_block.strip())
                fixed_info.append(f"- Q{qn}: STRICT {before_counts.get(qn,0)} → {after} (LLM organize)")
                continue
            else:
                unresolved.append(f"- Q{qn}: LLM returned {after} but expected {expected_n}; kept original")
        else:
            if has_opts and labeled_llm:
                unresolved.append(f"- Q{qn}: LLM returned {len(labeled_llm)} but expected {expected_n}; kept original")

        # 3) keep as-is
        out_blocks.append(raw_block.strip())
        if not has_opts:
            unresolved.append(f"- Q{qn}: no textual A.. options found (likely image-only); kept original")
        elif not llm.enabled:
            unresolved.append(f"- Q{qn}: inline/HTML split failed; LLM disabled ({llm.disabled_reason})")
        else:
            unresolved.append(f"- Q{qn}: could not extract {expected_n} alternatives; kept original")

    output_dir = folder / "prova_principal"
    out_md  = output_dir / "full_blocks_final.md"
    out_sum = output_dir / "full_blocks_final_summary.md"

    md_text = "----\n" + "\n----\n".join(out_blocks) + "\n----\n"
    out_md.write_text(md_text, encoding="utf-8")

    lines = [
        "# Finalize (letters-only; LaTeX-masked; safe pre-trim; relaxed inline; skip-if-none; LLM exact)",
        f"- input: {src_path.name}",
        f"- output: {out_md.name}",
        f"- total blocks: {len(blocks)}",
        f"- targeted questions: {len(targets)}",
        f"- expected alternatives per question (mode): {expected_n}",
        "",
    ]
    if fixed_info:
        lines.append("## Fixed"); lines += fixed_info; lines.append("")
    if unresolved:
        lines.append("## Unresolved (kept as-is)"); lines += unresolved; lines.append("")

    out_sum.write_text("\n".join(lines) + "\n", encoding="utf-8")
    
    # --- THIS IS THE NEW PRINT LOGIC ---
    print(f"[finalize] {folder.name}: targets={len(targets)} | fixed={len(fixed_info)} | unresolved={len(unresolved)} | wrote {out_md.name}")
    # --- END OF NEW PRINT LOGIC ---
    
    return True

def finalize_batch_from_audit(base: Path):
    if not base.exists():
        print("❌ Base dir not found:", base); return
    try:
        _ = _read_source_from_audit(base)
        finalize_one_from_audit(base)
        return
    except FileNotFoundError:
        pass
    count = 0
    for folder in sorted(p for p in base.iterdir() if p.is_dir()):
        try:
            _ = _read_source_from_audit(folder)
        except FileNotFoundError:
            continue
        if finalize_one_from_audit(folder):
            count += 1
    if count:
        print(f"[done] finalize-from-audit processed {count} folder(s)")
    else:
        print("⚠️ No folders with final_audit_summary.json were found under", base)
