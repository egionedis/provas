# Pipeline Full Summary

- Source: **full_blocks_fix_missing.md**
- Final output: **full_blocks_final.md**
- Expected alternatives per question: **5**

## Step: full_blocks_fix_dedup_summary.md
# Fix Summary

- input: full_blocks.md
- output: full_blocks_fixed.md
- output blocks: 82
- deduped: 1
- instruction-like detected: 2
- source blocks: 83

## Questão 37

**Kept** (best score; len=1415, alts=5, prompt=0, img=0, instr_like=1)

> "O capitalismo é um sistema económico que, desde sua origem, foi se expandindo económico e territorialmente: primeiro foi o colonialismo, de…

## Questão 50

**Kept** (best score; len=751, alts=5, prompt=0, img=0, instr_like=1)

> Em 18 de setembro de 1850, o imperador D. Pedro Il assinou a Lei 601, também conhecida como Lei de Terras. Esse é um marco legislativo impor…

## Questão 65

**Kept** (best score; len=2322, alts=0, prompt=1, img=0, instr_like=0)

> Todas as grandes línguas de cultura que conhecemos hoje, ao longo de sua historia, passaram por um processo de estandardização. Por estandar…

**Dropped**
- lower score, near-duplicate (sim=0.83); len=1651, alts=0, prompt=1, img=0, instr_like=0
  > Todas as grandes línguas de cultura que conhecemos hoje, ao longo de sua historia, passaram por um processo de estandardização. Por estandar…

## Step: full_blocks_fix_missing_summary.md
# Fix Missing Review
- input: full_blocks_fix_dedup.md
- output: full_blocks_fix_missing.md

- No gaps found.

## Step: final_audit_summary.json (compact)
- file: `full_blocks_fix_missing.md`
- expected_alt_count: `{'mode': 5, 'mode_support': 65, 'histogram': {'1': 2, '2': 2, '3': 1, '4': 9, '5': 65}}`
- buckets: few_alts=14, inline_only=3, no_alts=0

## Step: full_blocks_final_summary.md
# Finalize (letters-only; LaTeX-masked; safe pre-trim; relaxed inline; skip-if-none; LLM exact)
- input: full_blocks_fix_missing.md
- output: full_blocks_final.md
- total blocks: 82
- targeted questions: 17
- expected alternatives per question (mode): 5

## Fixed
- Q3: STRICT 4 → 5 (LLM organize)
- Q25: STRICT 5 → 5 (inline split, relaxed)
- Q26: STRICT 5 → 5 (inline split, relaxed)
- Q59: STRICT 4 → 5 (inline split)
- Q63: STRICT 1 → 5 (inline split)
- Q64: STRICT 4 → 5 (inline split)
- Q65: STRICT 0 → 5 (inline split)
- Q66: STRICT 0 → 5 (inline split)
- Q67: STRICT 0 → 5 (inline split)
- Q68: STRICT 4 → 5 (inline split)
- Q69: STRICT 4 → 5 (inline split)
- Q70: STRICT 1 → 5 (inline split)
- Q77: STRICT 1 → 5 (inline split)
- Q78: STRICT 5 → 5 (inline split, relaxed)

## Unresolved (kept as-is)
- Q1: could not extract 5 alternatives; kept original
- Q16: could not extract 5 alternatives; kept original
- Q23: could not extract 5 alternatives; kept original

## Final per-question status

- OK: **79** &nbsp;&nbsp; NOT: **3** &nbsp;&nbsp; TOTAL: **82**

| Questão | Status |
|:------:|:------:|
| 01 | not |
| 02 | ok |
| 03 | ok |
| 04 | ok |
| 05 | ok |
| 06 | ok |
| 07 | ok |
| 08 | ok |
| 09 | ok |
| 10 | ok |
| 11 | ok |
| 12 | ok |
| 13 | ok |
| 14 | ok |
| 15 | ok |
| 16 | not |
| 17 | ok |
| 18 | ok |
| 19 | ok |
| 20 | ok |
| 21 | ok |
| 22 | ok |
| 23 | not |
| 24 | ok |
| 25 | ok |
| 26 | ok |
| 27 | ok |
| 28 | ok |
| 29 | ok |
| 30 | ok |
| 31 | ok |
| 32 | ok |
| 33 | ok |
| 34 | ok |
| 35 | ok |
| 36 | ok |
| 37 | ok |
| 38 | ok |
| 39 | ok |
| 40 | ok |
| 41 | ok |
| 42 | ok |
| 43 | ok |
| 44 | ok |
| 45 | ok |
| 46 | ok |
| 47 | ok |
| 48 | ok |
| 49 | ok |
| 50 | ok |
| 51 | ok |
| 52 | ok |
| 53 | ok |
| 54 | ok |
| 55 | ok |
| 56 | ok |
| 57 | ok |
| 58 | ok |
| 59 | ok |
| 60 | ok |
| 61 | ok |
| 62 | ok |
| 63 | ok |
| 64 | ok |
| 65 | ok |
| 66 | ok |
| 67 | ok |
| 68 | ok |
| 69 | ok |
| 70 | ok |
| 71 | ok |
| 72 | ok |
| 73 | ok |
| 74 | ok |
| 75 | ok |
| 76 | ok |
| 77 | ok |
| 78 | ok |
| 79 | ok |
| 80 | ok |
| 81 | ok |
| 82 | ok |
