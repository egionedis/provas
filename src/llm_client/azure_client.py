# src/provas/azure_client.py
"""
Azure OpenAI client selector with per-model API version.
"""

from __future__ import annotations
import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

_API_DEFAULT = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
_API_GPT5 = os.getenv("AZURE_OPENAI_API_VERSION_GPT5", "2024-06-01")
_ENDPOINT = os.getenv("OPENAI_SDK_ENDPOINT")
_API_KEY = os.getenv("GENAIHUB_API_KEY")

_clients: dict[tuple[str, str], AzureOpenAI] = {}


def _api_version_for(model_name: str) -> str:
    return _API_GPT5 if model_name.startswith("gpt-5") else _API_DEFAULT


def get_client_for_model(model_name: str) -> AzureOpenAI:
    if not _ENDPOINT or not _API_KEY:
        raise RuntimeError("OPENAI_SDK_ENDPOINT or GENAIHUB_API_KEY is not set")

    api_version = _api_version_for(model_name)
    key = (api_version, _ENDPOINT)

    cli = _clients.get(key)
    if cli is None:
        cli = AzureOpenAI(
            api_key=_API_KEY,
            api_version=api_version,
            azure_endpoint=_ENDPOINT,
        )
        _clients[key] = cli
    return cli
