# Final Audit
- input: full_blocks_fix_missing.md

## Pipeline summaries
### Blocks

_No full_blocks_summary.md found._

### Fix: Deduplicate

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

### Fix: Missing

# Fix Missing Review
- input: full_blocks_fix_dedup.md
- output: full_blocks_fix_missing.md

- No gaps found.

## Final quality
- blocks: 82
- unique questions: 82
- range: 1..82
- duplicates: 0 
- out-of-order pairs: 0
- missing between min..max: none
- expected total: not inferred
- items with few alternatives (<4): 6

### Questions with few alternatives
- Q63: alt_count=1
- Q65: alt_count=0
- Q66: alt_count=0
- Q67: alt_count=0
- Q70: alt_count=1
- Q77: alt_count=1
