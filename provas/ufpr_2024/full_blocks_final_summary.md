# Finalize (inline + LLM fallback with exam pattern)
- input: full_blocks_fix_missing.md
- output: full_blocks_final.md
- total blocks: 82
- targeted questions: 17
- expected alternatives per question (mode): 5

## Fixed
- Q1: STRICT 2 → 5 (LLM extract-only)
- Q3: STRICT 4 → 5 (LLM extract-only)
- Q59: STRICT 4 → 5 (inline split)
- Q64: STRICT 4 → 5 (LLM extract-only)
- Q65: STRICT 0 → 5 (LLM extract-only)
- Q66: STRICT 0 → 5 (LLM extract-only)
- Q67: STRICT 0 → 5 (LLM extract-only)
- Q68: STRICT 4 → 5 (inline split)
- Q69: STRICT 4 → 5 (inline split)
- Q70: STRICT 1 → 5 (LLM extract-only)
- Q77: STRICT 1 → 5 (inline split)

## Unresolved (kept as-is)
- Q16: could not extract 5 alternatives; kept original
- Q23: could not extract 5 alternatives; kept original
- Q25: could not extract 5 alternatives; kept original
- Q26: could not extract 5 alternatives; kept original
- Q63: could not extract 5 alternatives; kept original
- Q78: could not extract 5 alternatives; kept original

