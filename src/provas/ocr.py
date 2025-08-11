# src/provas/ocr.py
from __future__ import annotations
import os
import re
import base64
from pathlib import Path
from typing import List
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

# ──────────────────────────────── DEPENDENCIES ─────────────────────────────── #
from openai import AzureOpenAI

# ──────────────────────────────── CONFIG ──────────────────────────────── #
# Use the same deployment name you configured in Azure
MODEL_NAME: str = os.getenv("LLM_VISION_MODEL", "gpt-4o_dz-eu_2024-08-06")

IMG_TAG_REGEX = re.compile(r'!\[\]\((images/[^)]+)\)')

VISION_PROMPT = """
Você é um assistente de visão encarregado de extrair **todos** os detalhes
relevantes de qualquer imagem (foto, gráfico, diagrama, mapa, tabela ou texto).

Responda em **UMA ÚNICA LINHA**, sem markdown nem quebras de linha, começando
por `IMG_DESC_START ` e terminando com ` IMG_DESC_END`, seguindo exatamente o formato abaixo (sem colchetes).  
Use ponto como separador decimal.

IMG_DESC_START : tipo=<foto|gráfico|diagrama|mapa|tabela|texto|outro>;
     resumo=<1-2 frases>;
     elementos=[<item1>, <item2>, …];                # partes visuais
     dados_chave=[<d1>, <d2>, …];                    # eixos, unidades, legendas,
                                                     # escalas, cores, símbolos,
                                                     # valores numéricos isolados
     grandezas=[(símbolo, valor, unidade), …];       # p.ex. (m,2.0,kg),(Q,3e-6,C)
     estrutura=[<bloco1>, <bloco2>, …];              # • GRÁFICO: pontos=(x,y) ou
                                                     #   intervalos=(x0,x1,y0→y1)
                                                     #   em ordem crescente de x
                                                     # • TABELA: linhaN=[c1,c2,…]
                                                     # • DIAGRAMA/FOTO: (obj, pos)
                                                     #   ou relações (obj1↔obj2)
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
"""

# ──────────────────────────────── AZURE CLIENT ──────────────────────────────── #
client = AzureOpenAI(
    api_key=os.getenv("GENAIHUB_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    azure_endpoint=os.getenv("OPENAI_SDK_ENDPOINT"),
)

# ────────────────────────────── UTILITIES ────────────────────────────── #
def _to_data_url(img_path: Path) -> str:
    mime = "image/png" if img_path.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(img_path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def _describe_image(img_path: Path) -> str:
    """Send the image to the vision model and return the structured one-line description."""
    print(f"Gerando descrição para {img_path} …")
    data_url = _to_data_url(img_path)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": VISION_PROMPT},
                {"type": "image_url", "image_url": {"url": data_url, "detail": "auto"}},
            ],
        }],
        max_tokens=500,
        temperature=0.2,
    )
    return response.choices[0].message.content.strip().replace("\n", " ")

def _already_has_description(next_line: str) -> bool:
    # Your prompt emits "IMG_DESC_START"
    return next_line.strip().startswith("IMG_DESC_START")

# ───────────────────────────── MAIN LOGIC ───────────────────────────── #
def _process_markdown(lines: List[str], image_dir: Path) -> List[str]:
    out_lines: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out_lines.append(line)
        match = IMG_TAG_REGEX.search(line)
        if match:
            img_rel = match.group(1)
            img_path = image_dir / Path(img_rel).name
            if i + 1 < len(lines) and _already_has_description(lines[i + 1]):
                i += 1
                out_lines.append(lines[i])
            else:
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
