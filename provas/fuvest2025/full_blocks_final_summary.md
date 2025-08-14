# Finalize (inline + LLM fallback with exam pattern)
- input: full_blocks_fix_missing.md
- output: full_blocks_final.md
- total blocks: 90
- targeted questions: 9
- expected alternatives per question (mode): 5

## Fixed
- Q5: STRICT 4 → 5 (LLM extract-only)
- Q21: STRICT 1 → 5 (LLM extract-only)
- Q43: STRICT 0 → 5 (inline split)
- Q48: STRICT 0 → 5 (inline split)
- Q78: STRICT 0 → 5 (inline split)

## Unresolved (kept as-is)
- Q31: could not extract 5 alternatives; kept original
- Q45: could not extract 5 alternatives; kept original
- Q60: could not extract 5 alternatives; kept original
- Q69: could not extract 5 alternatives; kept original

