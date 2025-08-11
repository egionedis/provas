from __future__ import annotations
import os
import re
import base64
from pathlib import Path
from typing import List
from dotenv import load_dotenv

load_dotenv()

try:
  from openai import AzureOpenAI
except Exception:
  AzureOpenAI = None  # optional import; skip if not available

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

def _to_data_url(img_path: Path) -> str:
    mime = "image/png" if img_path.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(img_path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def _already_has_description(next_line: str) -> bool:
    # FIX: your prompt emits "IMG_DESC_START", not "IMG:"
    return next_line.strip().startswith("IMG_DESC_START")

def _describe_image(client, model_name: str, img_path: Path) -> str:
    data_url = _to_data_url(img_path)
    resp = client.chat.completions.create(
        model=model_name,
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
    return resp.choices[0].message.content.strip().replace("\n", " ")

def _process_markdown(lines: List[str], image_dir: Path, client, model_name: str) -> List[str]:
    out_lines: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out_lines.append(line)
        m = IMG_TAG_REGEX.search(line)
        if m:
            img_rel = m.group(1)
            img_path = image_dir / Path(img_rel).name
            if i + 1 < len(lines) and _already_has_description(lines[i + 1]):
                i += 1
                out_lines.append(lines[i])
            else:
                desc = _describe_image(client, model_name, img_path)
                out_lines.append(f"{desc}\n")
        i += 1
    return out_lines

def run_ocr_folder(folder: Path,
                   model_name: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
                   api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
                   endpoint: str = os.getenv("OPENAI_SDK_ENDPOINT"),
                   api_key: str = os.getenv("GENAIHUB_API_KEY")):
    if AzureOpenAI is None:
        print("⚠️ AzureOpenAI not installed; skipping OCR.")
        return
    client = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)

    md_in = folder / "full.md"
    md_out = folder / "full_with_descriptions.md"
    image_dir = folder / "images"
    if not (md_in.exists() and image_dir.exists()):
        print(f"⚠️ Skipping {folder.name}: missing full.md or images/")
        return
    lines = md_in.read_text(encoding="utf-8").splitlines(keepends=True)
    annotated = _process_markdown(lines, image_dir, client, model_name)
    md_out.write_text("".join(annotated), encoding="utf-8")
    print(f"✅ OCR+descriptions: {md_out}")

def run_ocr_batch(base_dir: Path):
    if not base_dir.exists():
        print("❌ Base dir not found:", base_dir)
        return
    for test_folder in base_dir.iterdir():
        if test_folder.is_dir():
            run_ocr_folder(test_folder)
