# src/provas/finalize_from_audit.py
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
import os, re, json

# --- load environment early so llm_client sees it ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ---------- optional LLM client ----------
try:
    from .llm_client import chat as llm_chat
except Exception:
    llm_chat = None

# ---------- patterns ----------
BANNER = re.compile(r'^\s*##\s*Quest[ãa]o\s+(\d{1,4})\b', re.I)
SEP    = re.compile(r'^\s*-{2,}\s*$', re.M)

# STRICT line-start alternatives (accept letters/digits)
ALT_LINE = re.compile(r'(?mi)^\s*[\(\[]?\s*(?P<label>[A-Za-z0-9])\s*[\)\]\.\:\-–—]\s+(?P<t>.+)$')
# INLINE labels anywhere in the paragraph (letters/digits)
ALT_ANY  = re.compile(r'(?i)([A-Za-z0-9])\s*[\)\]\.\:\-–—]\s+')

# keep headings like "Texto 1"
TEXTO_HEADING = re.compile(r'^\s*#?\s*Texto\s+\d+\s*$', re.I)
IMG_TAG = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
IMG_DESC_INLINE = re.compile(r'IMG_DESC_START\s*:(.*?)IMG_DESC_END')
URL_RE = re.compile(r'https?://\S+|\bwww\.\S+', re.I)

# ---------- source & targets (reads the NEW audit JSON you just built) ----------
def _read_source_from_audit(folder: Path) -> tuple[Path, str, dict]:
    """
    Uses final_audit_summary.json (problem-focused JSON).
    Source file is the 'file' field in that JSON; by design it is full_blocks_fix_missing.md.
    """
    audit_path = folder / "final_audit_summary.json"
    if not audit_path.exists():
        raise FileNotFoundError("final_audit_summary.json not found")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))

    file_name = audit.get("file")
    if not file_name:
        raise FileNotFoundError("final_audit_summary.json missing 'file' field")

    src = folder / file_name
    if not src.exists():
        # fallback if the audit JSON was moved
        src = folder / "full_blocks_fix_missing.md"
        if not src.exists():
            raise FileNotFoundError("no source blocks file (full_blocks_fix_missing.md)")

    return src, src.read_text(encoding="utf-8", errors="ignore"), audit

def _target_questions(audit: dict) -> Tuple[Set[int], Optional[int]]:
    """
    Build the target set from the audit JSON buckets and
    return (targets, expected_mode) where expected_mode is the exam-wide alternatives mode.
    """
    targets: Set[int] = set()
    for item in (audit.get("few_alts") or []):
        try:
            targets.add(int(item.get("q")))
        except Exception:
            pass
    for q in (audit.get("inline_only") or []):
        try:
            targets.add(int(q))
        except Exception:
            pass
    for q in (audit.get("no_alts") or []):
        try:
            targets.add(int(q))
        except Exception:
            pass

    exp = audit.get("expected_alt_count") or {}
    mode = exp.get("mode")
    try:
        mode = int(mode) if mode is not None else None
    except Exception:
        mode = None
    return targets, mode

# ---------- blocks I/O ----------
def _split_blocks(md_text: str) -> List[Tuple[int, str]]:
    raw = [b.strip() for b in SEP.split(md_text)]
    out: List[Tuple[int, str]] = []
    for b in raw:
        if not b:
            continue
        m = BANNER.match(b)
        if m:
            out.append((int(m.group(1)), b))
    return out

def _alt_count_strict(block_text: str) -> int:
    labels = {m.group("label").upper() for m in ALT_LINE.finditer(block_text)}
    # Count UNIQUE labels found at line start, but only within the first contiguous cluster
    # (so re-scan cluster-wise)
    lines = block_text.splitlines()
    body = lines[1:] if (lines and BANNER.match(lines[0])) else lines[:]

    started = False
    cluster_labels: List[str] = []
    for ln in body:
        m = ALT_LINE.match(ln)
        if m:
            started = True
            cluster_labels.append(m.group("label").upper())
        else:
            if started:
                # allow completely blank lines within cluster
                if ln.strip() == "":
                    continue
                break
    # unique count within the cluster
    return len(cluster_labels)

def _parse_block_return_body(block_text: str) -> str:
    lines = block_text.splitlines()
    body_lines = lines[1:] if (lines and BANNER.match(lines[0])) else lines[:]
    return "\n".join(body_lines)

# ---------- keep quotes/citations; drop only obvious meta ----------
def _is_meta_credit_line(ln: str) -> bool:
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
    return False

def _clean_stem_text(raw: str) -> str:
    lines = raw.splitlines()
    out = []
    for ln in lines:
        if IMG_TAG.search(ln) or IMG_DESC_INLINE.search(ln):
            continue
        if _is_meta_credit_line(ln):
            continue
        out.append(ln)
    return "\n".join(out).strip()

# ---------- validation helpers ----------
def _extract_label_token(s: str) -> Optional[str]:
    m = re.match(r'\s*[\(\[]?\s*([A-Za-z0-9])\s*[\)\]\.\:\-–—]\s+', s)
    return m.group(1).upper() if m else None

def _labels_are_sequential(labeled: List[str], expected_n: int) -> bool:
    """
    Accept sequences like A.., or 1.., exactly 'expected_n' items.
    """
    if not labeled or expected_n is None:
        return False
    if len(labeled) != expected_n:
        return False

    heads = []
    for s in labeled:
        tok = _extract_label_token(s)
        if tok is None:
            return False
        heads.append(tok)

    # Letters?
    if heads[0] == "A":
        for i in range(expected_n):
            if heads[i] != chr(ord("A") + i):
                return False
        return True

    # Digits?
    if heads[0] == "1":
        for i in range(expected_n):
            if heads[i] != str(1 + i):
                return False
        return True

    return False

# ---------- inline splitter (letters or digits) ----------
def _split_inline_alternatives(raw_body: str, expected_n: int) -> tuple[str, List[str]] | None:
    """
    Try to extract EXACTLY expected_n alternatives starting at A.. or 1..
    Returns (pre_stem, [exact labeled substrings]) or None.
    """
    if expected_n is None or expected_n < 2:
        return None

    matches = list(ALT_ANY.finditer(raw_body))
    if not matches:
        return None

    def _scan_sequence(start_token: str) -> Optional[tuple[str, List[str]]]:
        # find first start_token
        start_idx = next((i for i, m in enumerate(matches) if m.group(1).upper() == start_token), None)
        if start_idx is None:
            return None
        seq = []
        cur = start_idx
        for step in range(expected_n):
            expect = chr(ord(start_token) + step) if start_token.isalpha() else str(1 + step)
            found = None
            for j in range(cur, len(matches)):
                tok = matches[j].group(1).upper()
                # normalize digit tokens
                if start_token.isdigit():
                    if tok.isdigit() and tok == str(1 + step):
                        found = j; break
                else:
                    if tok == expect:
                        found = j; break
            if found is None:
                return None
            seq.append(matches[found])
            cur = found + 1

        labeled: List[str] = []
        for k in range(len(seq)):
            s = seq[k].start()
            e = seq[k + 1].start() if k + 1 < len(seq) else len(raw_body)
            frag = raw_body[s:e].strip()
            if frag:
                labeled.append(frag)
        if not _labels_are_sequential(labeled, expected_n):
            return None
        pre = raw_body[:seq[0].start()]
        return pre, labeled

    # Try letters then digits
    out = _scan_sequence("A")
    if out:
        return out
    return _scan_sequence("1")

# ---------- LLM fallback (extract-only; exact substrings) ----------
class _LLM:
    def __init__(self):
        # Default to a 4o-mini deployment (stable with Chat Completions)
        self.endpoint = os.getenv("OPENAI_SDK_ENDPOINT", "")
        self.api_key  = os.getenv("GENAIHUB_API_KEY", "")
        self.model    = os.getenv("LLM_MODEL", "gpt-4o-mini_dz-eu_2024-07-08")
        self.enabled  = bool(llm_chat and self.endpoint and self.api_key)
        self.disabled_reason = None
        if not llm_chat:
            self.disabled_reason = "llm_client not importable"
        elif not self.endpoint or not self.api_key:
            self.disabled_reason = "missing OPENAI_SDK_ENDPOINT/GENAIHUB_API_KEY"

    def recover_labeled(self, raw_body: str, expected_n: int) -> List[str]:
        """
        Ask the model to return EXACTLY expected_n alternatives as exact substrings.
        Accept letters (A..), or digits (1..). Returns [] if not confident.
        """
        if not self.enabled or expected_n is None or expected_n < 2:
            return []

        system = (
            "You extract text by copying **exact substrings** from the provided block. "
            "Output **only JSON** (no prose).\n"
            "Task: From the block, return the **first contiguous labeled alternatives** sequence starting at A or 1, "
            "then strictly increasing (A,B,C,...) or (1,2,3,...) until you reach the requested count. "
            "Labels look like 'A)', '(B)', 'C -', 'D:', '1)' or '2.' etc. "
            "Return each **exact substring** (including the label), preserving the original spacing/punctuation.\n"
            'Schema: { "labeled_alternatives": ["A) …", "B) …"], "confidence": 0..1 }\n'
            "Rules:\n"
            f"- Return **exactly {expected_n} items**. If you cannot find {expected_n} labeled alternatives, return an empty list.\n"
            "- Every returned string MUST be an exact substring of the raw block.\n"
            "- Stop each item at the beginning of the next label.\n"
        )
        user = {"raw_block": raw_body, "expected_count": expected_n}

        try:
            resp = llm_chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
                ],
                max_tokens=800,
            )
            out = (resp.choices[0].message.content or "").strip()
            out = out.strip("`")
            if out.lower().startswith("json"):
                out = out[4:].strip()
            data = json.loads(out)
            seq = data.get("labeled_alternatives") or []
            if not isinstance(seq, list):
                return []
            # literal & sequential check
            clean = []
            for s in seq:
                t = (s or "").strip()
                if t and t in raw_body:
                    clean.append(t)
            return clean if _labels_are_sequential(clean, expected_n) else []
        except Exception:
            return []

# ---------- assemble new block ----------
def _build_block(qn: int, stem_text: str, alt_labeled_lines: List[str], img_lines_pre: List[str]) -> str:
    parts = [f"## Questão {qn}"]
    if img_lines_pre:
        parts += img_lines_pre
        parts.append("")
    if stem_text.strip():
        parts.append(stem_text.strip())
        parts.append("")
    for s in alt_labeled_lines:
        parts.append(s.lstrip())
    return "\n".join([p for p in parts if p is not None]).strip()

# ---------- finalize ----------
def finalize_one_from_audit(folder: Path) -> bool:
    try:
        src_path, text, audit = _read_source_from_audit(folder)
    except FileNotFoundError as e:
        print(f"⚠️  Skipping {folder}: {e}")
        return False

    targets, expected_mode = _target_questions(audit)
    # Clamp expected count (practical limits 2..7; leave None -> default 4)
    expected_n = expected_mode if (isinstance(expected_mode, int) and 2 <= expected_mode <= 7) else 4

    blocks = _split_blocks(text)
    if not blocks:
        print(f"⚠️  Skipping {folder}: no '## Questão N' blocks in {src_path.name}")
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

        # 1) Deterministic inline split (must return EXACTLY expected_n items)
        inline = _split_inline_alternatives(raw_body, expected_n=expected_n)
        if inline:
            pre, labeled = inline
            pre_lines = pre.splitlines()
            img_lines_pre = [ln for ln in pre_lines if IMG_TAG.search(ln)]
            stem_text = _clean_stem_text(pre)
            new_block = _build_block(qn, stem_text, labeled, img_lines_pre)
            after = _alt_count_strict(new_block)
            if after == expected_n:
                out_blocks.append(new_block.strip())
                before = before_counts.get(qn, 0)
                fixed_info.append(f"- Q{qn}: STRICT {before} → {after} (inline split)")
                continue
            # else, fall through to LLM

        # 2) LLM fallback (extract-only; MUST return EXACTLY expected_n)
        labeled_llm = llm.recover_labeled(raw_body, expected_n=expected_n)
        if labeled_llm and len(labeled_llm) == expected_n:
            first = labeled_llm[0]
            start_pos = raw_body.find(first)
            pre = raw_body[:start_pos] if start_pos >= 0 else ""
            pre_lines = pre.splitlines()
            img_lines_pre = [ln for ln in pre_lines if IMG_TAG.search(ln)]
            stem_text = _clean_stem_text(pre)
            new_block = _build_block(qn, stem_text, labeled_llm, img_lines_pre)
            after = _alt_count_strict(new_block)
            if after == expected_n:
                out_blocks.append(new_block.strip())
                before = before_counts.get(qn, 0)
                fixed_info.append(f"- Q{qn}: STRICT {before} → {after} (LLM extract-only)")
                continue
            else:
                unresolved.append(f"- Q{qn}: LLM returned {after} but expected {expected_n}; kept original")
        else:
            if labeled_llm:
                unresolved.append(f"- Q{qn}: LLM returned {len(labeled_llm)} but expected {expected_n}; kept original")

        # 3) keep as-is with explicit reason
        out_blocks.append(raw_block.strip())
        if not llm.enabled:
            unresolved.append(f"- Q{qn}: no inline A/1 sequence; LLM disabled ({llm.disabled_reason})")
        else:
            unresolved.append(f"- Q{qn}: could not extract {expected_n} alternatives; kept original")

    # write outputs
    out_md  = folder / "full_blocks_final.md"
    out_sum = folder / "full_blocks_final_summary.md"

    md_text = "----\n" + "\n----\n".join(out_blocks) + "\n----\n"
    out_md.write_text(md_text, encoding="utf-8")

    lines = [
        "# Finalize (inline + LLM fallback with exam pattern)",
        f"- input: {src_path.name}",
        f"- output: {out_md.name}",
        f"- total blocks: {len(blocks)}",
        f"- targeted questions: {len(targets)}",
        f"- expected alternatives per question (mode): {expected_n}",
        "",
    ]
    if fixed_info:
        lines.append("## Fixed")
        lines += fixed_info
        lines.append("")
    if unresolved:
        lines.append("## Unresolved (kept as-is)")
        lines += unresolved
        lines.append("")

    out_sum.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[finalize] {folder.name}: targets={len(targets)} | expected_n={expected_n} | wrote {out_md.name} | summary: {out_sum.name}")
    return True

def finalize_batch_from_audit(base: Path):
    if not base.exists():
        print("❌ Base dir not found:", base); return
    # single-folder mode
    try:
        _ = _read_source_from_audit(base)
        finalize_one_from_audit(base)
        return
    except FileNotFoundError:
        pass

    # multi-folder
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
