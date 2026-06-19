"""Thin wrappers around the client's OpenAI-compatible chat + embedding endpoints.

The rest of the engine only ever calls `embed()` and `chat()` — it never sees raw HTTP,
base URLs, or model names. That keeps the providers swappable.
"""
from __future__ import annotations

from openai import OpenAI

from . import config

# Two clients: chat and embeddings may use different keys / base URLs.
_chat_client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.CHAT_API_KEY or "none")
_embed_client = OpenAI(base_url=config.EMBED_BASE_URL, api_key=config.EMBED_API_KEY or "none")


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts → list of vectors (each length config.EMBED_DIM)."""
    if not texts:
        return []
    resp = _embed_client.embeddings.create(model=config.EMBED_MODEL, input=texts)
    # OpenAI returns items possibly out of order; sort by index to be safe.
    items = sorted(resp.data, key=lambda d: d.index)
    return [item.embedding for item in items]


def embed_one(text: str) -> list[float]:
    return embed([text])[0]


def chat(
    messages: list[dict],
    *,
    temperature: float = 0.2,
    max_tokens: int = 800,
) -> str:
    """Single chat completion → assistant text.

    Low default temperature keeps answers grounded and predictable for a support bot.
    """
    resp = _chat_client.chat.completions.create(
        model=config.CHAT_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()
