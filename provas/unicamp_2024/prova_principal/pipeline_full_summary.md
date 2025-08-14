# Pipeline Full Summary

- Source: **full_blocks_fix_missing.md**
- Final output: **full_blocks_final.md**
- Expected alternatives per question: **4**

## Step: full_blocks_fix_dedup_summary.md
# Fix Summary

- input: full_blocks.md
- output: full_blocks_fixed.md
- output blocks: 69
- deduped: 1
- instruction-like detected: 5
- source blocks: 70

## Questão 11

**Kept** (best score; len=2172, alts=4, prompt=0, img=0, instr_like=1)

> Em 1921, Mário de Andrade, escrevendo a série de artigos "Mestres do passado", publicados no Jornal do Comércio (edi- ção de São Paulo), obs…

## Questão 17

**Kept** (best score; len=1550, alts=4, prompt=0, img=1, instr_like=1)

> ![](images/9861d3a0bfe6142da8e1c1f2d2f69ed4706e181333ea757b46c4e6be842a58be.jpg) Legenda: Imagens de "mulheres de conforto" **, em 1944, na …

## Questão 18

**Kept** (best score; len=1669, alts=3, prompt=0, img=0, instr_like=1)

> Priões e torturas igualmente triplicaram, principalmente as de jornalistas. Dentre elas, a mais emblemática foi a de Vladimir Herzog, direct…

## Questão 28

**Kept** (best score; len=2679, alts=4, prompt=1, img=1, instr_like=1)

> O litoral brasileiro tem uma historia fisiografica e ecologica rica e complexa, influenciaada por uma variedade de fatores e processos inter…

## Questão 47

**Kept** (best score; len=1812, alts=4, prompt=1, img=1, instr_like=1)

> A partir da organização tecidual, é possível reconhecer o está- gio de desenvolvimento dos plantas e mesmo diferenciar mono cotiledôneas e e…

## Questão 53

**Kept** (best score; len=1258, alts=4, prompt=1, img=0, instr_like=0)

> "Apesar de sua presumida evidencia, a articulacao entre liberidade e igualidade e mais complicada do que parece. Sua reuniao em um mesmo ind…

**Dropped**
- lower score; len=13, alts=0, prompt=0, img=0, instr_like=0
  >

## Step: full_blocks_fix_missing_summary.md
# Fix Missing Review
- input: full_blocks_fix_dedup.md
- output: full_blocks_fix_missing.md

- Filled Q29 by splitting Q28 after options:
    last option: d) Os deltas sao formatados por sedimentos fluviais e cobertos por especies arboreas de grande porte.
    tail start:  Moradores em situação de rua em São Paulo/SP
- Q48: tail after options in Q47 didn’t look like a new question.
- Q65: tail after options in Q64 didn’t look like a new question.
- Filled Q48 by splitting Q47 after options:
    last option: d) Figura B, xilema e pericíclo.
    tail start:  Quando desempenho minha tarefa de imao, de marido ou de cidadao, quando executo os compromissos que assumi, eu cumpro de
- Q65: tail after options in Q64 didn’t look like a new question.
- Unresolved missing: 65

## Step: final_audit_summary.json (compact)
- file: `full_blocks_fix_missing.md`
- expected_alt_count: `{'mode': 4, 'mode_support': 60, 'histogram': {'3': 7, '4': 60}}`
- buckets: few_alts=7, inline_only=4, no_alts=0

## Step: full_blocks_final_summary.md
# Finalize (letters-only; LaTeX-masked; safe pre-trim; relaxed inline; skip-if-none; LLM exact)
- input: full_blocks_fix_missing.md
- output: full_blocks_final.md
- total blocks: 71
- targeted questions: 11
- expected alternatives per question (mode): 4

## Fixed
- Q9: STRICT 3 → 4 (inline split)
- Q18: STRICT 3 → 4 (inline split)
- Q19: STRICT 3 → 4 (inline split)
- Q45: STRICT 3 → 4 (inline split)
- Q46: STRICT 3 → 4 (inline split)
- Q54: STRICT 3 → 4 (inline split, relaxed)
- Q55: STRICT 3 → 4 (inline split)
- Q69: STRICT 0 → 4 (inline split)

## Unresolved (kept as-is)
- Q26: no textual A.. options found (likely image-only); kept original
- Q40: no textual A.. options found (likely image-only); kept original
- Q67: no textual A.. options found (likely image-only); kept original

## Final per-question status

- OK: **67** &nbsp;&nbsp; NOT: **4** &nbsp;&nbsp; TOTAL: **71**

| Questão | Status |
|:------:|:------:|
| 01 | ok |
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
| 16 | ok |
| 17 | ok |
| 18 | ok |
| 19 | ok |
| 20 | not |
| 21 | ok |
| 22 | ok |
| 23 | ok |
| 24 | ok |
| 25 | ok |
| 26 | not |
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
| 40 | not |
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
| 66 | ok |
| 67 | not |
| 68 | ok |
| 69 | ok |
| 70 | ok |
| 71 | ok |
| 72 | ok |
