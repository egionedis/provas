# Provas

Pipeline to turn vestibular PDFs into structured JSON.

## Pipeline

```bash
# 1) OCR images and inject IMG_DESC lines
provas ocr provas

# 2) Normalize markdown (merge preambles; strip inline options in headers)
provas clean provas

# 3) Export JSON + validation report
provas export_all provas
