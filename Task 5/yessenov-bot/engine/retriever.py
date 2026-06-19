"""Query-time retrieval over the active vector store."""
from __future__ import annotations

from . import config, providers
from .store import Hit, get_store

# The store is loaded once and reused across queries (cheap for NumpyStore).
_store = None


def _get_store():
    global _store
    if _store is None:
        _store = get_store()
    return _store


def retrieve(query: str, k: int | None = None) -> list[Hit]:
    """Embed the query and return the top-k nearest chunks (sorted by ascending distance)."""
    k = k or config.TOP_K
    qvec = providers.embed_one(query)
    return _get_store().search(qvec, k)


def best_distance(hits: list[Hit]) -> float:
    """Smallest (best) distance among hits; +inf if no hits."""
    return hits[0].distance if hits else float("inf")
