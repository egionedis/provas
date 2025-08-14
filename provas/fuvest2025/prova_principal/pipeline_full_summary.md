# Pipeline Full Summary

- Source: **full_blocks_fix_missing.md**
- Final output: **full_blocks_final.md**
- Expected alternatives per question: **5**

## Step: full_blocks_fix_dedup_summary.md
# Fix Summary

- input: full_blocks.md
- output: full_blocks_fixed.md
- output blocks: 89
- deduped: 0
- instruction-like detected: 2
- source blocks: 89

## Questão 22

**Kept** (best score; len=1498, alts=0, prompt=0, img=1, instr_like=1)

> ![](images/51fed61c162cbb40be353c551d70e742bbfe4069ee58ac1c1da3470a7e28af7c.jpg) Uma das possíveis tecnologias para a produção de telas sens…

## Questão 36

**Kept** (best score; len=2042, alts=0, prompt=0, img=0, instr_like=1)

> "Madala pensou que devia dizer qualquer coisa ao Djimo, mas não se lembrou de repetir a pergunta para si mesmo e por isso não soube o que di…

## Step: full_blocks_fix_missing_summary.md
# Fix Missing Review
- input: full_blocks_fix_dedup.md
- output: full_blocks_fix_missing.md

- Filled Q26 by splitting Q25 after options:
    last option: (E) 1:20.000.000.
    tail start:  Atualmente  $80\%$  do comércio mundial transita pelos mares, principalmente em rotas que passam pelos Canais do Panamá

## Step: final_audit_summary.json (compact)
- file: `full_blocks_fix_missing.md`
- expected_alt_count: `{'mode': 5, 'mode_support': 81, 'histogram': {'1': 1, '4': 1, '5': 81}}`
- buckets: few_alts=2, inline_only=4, no_alts=3

## Step: full_blocks_final_summary.md
# Finalize (letters-only; LaTeX-masked; safe pre-trim; relaxed inline; skip-if-none; LLM exact)
- input: full_blocks_fix_missing.md
- output: full_blocks_final.md
- total blocks: 90
- targeted questions: 9
- expected alternatives per question (mode): 5

## Fixed
- Q21: STRICT 1 → 5 (inline split)
- Q31: STRICT 0 → 5 (inline split, relaxed)
- Q43: STRICT 0 → 5 (inline split)
- Q45: STRICT 0 → 5 (inline split, relaxed)
- Q48: STRICT 0 → 5 (inline split)
- Q60: STRICT 0 → 5 (inline split, relaxed)
- Q78: STRICT 0 → 5 (inline split)

## Unresolved (kept as-is)
- Q5: could not extract 5 alternatives; kept original
- Q69: no textual A.. options found (likely image-only); kept original

## Final per-question status

- OK: **88** &nbsp;&nbsp; NOT: **2** &nbsp;&nbsp; TOTAL: **90**

| Questão | Status |
|:------:|:------:|
| 01 | ok |
| 02 | ok |
| 03 | ok |
| 04 | ok |
| 05 | not |
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
| 16 | ok |
| 17 | ok |
| 18 | ok |
| 19 | ok |
| 20 | ok |
| 21 | ok |
| 22 | ok |
| 23 | ok |
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
| 69 | not |
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
| 83 | ok |
| 84 | ok |
| 85 | ok |
| 86 | ok |
| 87 | ok |
| 88 | ok |
| 89 | ok |
| 90 | ok |
