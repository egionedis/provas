# src/provas/llm_client.py
"""
Standard LLM helpers for the whole project.

- chat(model, messages, **kwargs)           -> Azure OpenAI response
- chat_vision(model, text_prompt, images, detail=None, **kwargs) -> response
  (images can be local paths or http(s)/data URLs; local paths are base64->data URLs)
"""
from __future__ import annotations
import base64
from pathlib import Path
from typing import Iterable, Union

from .azure_client import get_client_for_model


StrPath = Union[str, Path]


def _guess_mime(p: Path) -> str:
    ext = p.suffix.lower()
    if ext == ".png": return "image/png"
    if ext in (".jpg", ".jpeg"): return "image/jpeg"
    if ext == ".webp": return "image/webp"
    if ext == ".gif": return "image/gif"
    return "application/octet-stream"


def _to_data_url(p: Path) -> str:
    mime = _guess_mime(p)
    b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def _to_image_content(item: StrPath, detail: str | None):
    s = str(item)
    if s.startswith(("http://", "https://", "data:")):
        url = s
    else:
        url = _to_data_url(Path(s))
    blob = {"type": "image_url", "image_url": {"url": url}}
    if detail:
        blob["image_url"]["detail"] = detail
    return blob


def chat(model: str, messages: list[dict], **kwargs):
    client = get_client_for_model(model)
    return client.chat.completions.create(model=model, messages=messages, **kwargs)


def chat_vision(model: str,
                text_prompt: str,
                images: Iterable[StrPath],
                detail: str | None = None,
                **kwargs):
    content = [{"type": "text", "text": text_prompt}]
    for it in images:
        content.append(_to_image_content(it, detail=detail))
    msgs = [{"role": "user", "content": content}]
    return chat(model=model, messages=msgs, **kwargs)
