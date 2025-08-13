# src/provas/ocr.py
from __future__ import annotations
import os, re
from pathlib import Path
from typing import List
from dotenv import load_dotenv

from llm_client import chat_vision

load_dotenv()

# ───────────────────────────── CONFIG ───────────────────────────── #
# Default to GPT-5 Sweden Data Zone; override via .env if needed
MODEL_NAME: str = os.getenv("LLM_VISION_MODEL", "gpt-5_dz-swc_2025-08-07")
IMG_TAG_REGEX = re.compile(r'!\[\]\((images/[^)]+)\)')

VISION_PROMPT = """
Você é um assistente de visão encarregado de extrair **todos** os detalhes
relevantes de qualquer imagem (foto, gráfico, diagrama, mapa, tabela ou texto).

Responda em **UMA ÚNICA LINHA**, sem markdown nem quebras de linha, começando
por `IMG_DESC_START ` e terminando com ` IMG_DESC_END`, seguindo exatamente o formato abaixo (sem colchetes).  
Use ponto como separador decimal.

IMG_DESC_START : tipo=<foto|gráfico|diagrama|mapa|tabela|texto|outro>;
     resumo=<1-2 frases>;
     elementos=[<item1>, <item2>, …];
     dados_chave=[<d1>, <d2>, …];
     grandezas=[(símbolo, valor, unidade), …];
     estrutura=[<bloco1>, <bloco2>, …];
     texto_detectado=[<str1>, <str2>, …]
IMG_DESC_END

Regras
- Preencha **estrutura** conforme o tipo detectado; se não se aplicar,
  use estrutura=[]. Exemplos para degraus:
  estrutura=[(0,0);(10,4);(30,4);(40,2);(60,2);(70,0)]
  ou estrutura=[(0,10,0→4);(10,30,4);(30,40,4→2);(40,60,2);…]
- Coloque em **grandezas** toda grandeza explícita (massa, força, densidade,
  escala gráfica, etc.). Se não houver, use grandezas=[].
- Não inclua markdown, “```json” ou explicações extras.
- Use português.
""".strip()


def _already_has_description(next_line: str) -> bool:
    # Your prompt emits "IMG_DESC_START"
    return next_line.strip().startswith("IMG_DESC_START")


def _describe_image(img_path: Path) -> str:
    """Send the image to the vision model and return the structured one-line description."""
    resp = chat_vision(
        model=MODEL_NAME,
        text_prompt=VISION_PROMPT,
        images=[img_path],
        detail=None,
        max_tokens=500,
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip().replace("\n", " ")


# ──────────────────────────── MAIN LOGIC ──────────────────────────── #
def _process_markdown(lines: List[str], image_dir: Path) -> List[str]:
    out_lines: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out_lines.append(line)
        match = IMG_TAG_REGEX.search(line)
        if match:
            img_rel = match.group(1)                       # e.g., "images/foo.jpg"
            img_path = image_dir / Path(img_rel).name      # provas/<exam>/images/foo.jpg
            if i + 1 < len(lines) and _already_has_description(lines[i + 1]):
                i += 1
                out_lines.append(lines[i])
            else:
                # 👇 Print which test (folder) and which image we’re describing
                exam_name = image_dir.parent.name          # folder name is the "test"
                print(f"🖼️ Descrevendo imagem → teste: {exam_name} | arquivo: {img_rel}")
                desc_line = _describe_image(img_path)
                out_lines.append(f"{desc_line}\n")
        i += 1
    return out_lines


def run_ocr_folder(folder: Path):
    """Process a single exam folder: provas/<exam>/"""
    md_in = folder / "full.md"
    md_out = folder / "full_with_descriptions.md"
    image_dir = folder / "images"

    if not md_in.exists() or not image_dir.exists():
        print(f"⚠️ Ignorado: {folder.name} (full.md ou images/ ausentes)")
        return

    # ✅ Skip if already processed
    if md_out.exists():
        print(f"⏩ Já existe {md_out}, pulando para economizar tokens.")
        return

    lines = md_in.read_text(encoding="utf-8").splitlines(keepends=True)
    annotated = _process_markdown(lines, image_dir)
    md_out.write_text("".join(annotated), encoding="utf-8")
    print(f"✅ Arquivo gerado: {md_out}")


def run_ocr_batch(base_dir: Path):
    """Process all exam folders under base_dir."""
    base_dir = Path(base_dir)
    if not base_dir.exists():
        raise FileNotFoundError("❌ Pasta base não encontrada: " + str(base_dir))

    for test_folder in base_dir.iterdir():
        if test_folder.is_dir():
            print(f"\n📂 Processando: {test_folder.name}")
            run_ocr_folder(test_folder)
