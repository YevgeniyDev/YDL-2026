"""Build the vector index from data/raw/*.md.

Pipeline: read each scraped markdown file -> split into small overlapping chunks ->
batch-embed via the client's embedding API -> write into the active vector store.

Idempotent: the store is reset at the start, so re-running fully rebuilds the index.

Run:  python -m engine.ingest
"""
from __future__ import annotations

import hashlib
import re
import sys

from . import config, providers
from .store import NumpyStore, get_store


def _norm_hash(text: str) -> str:
    """Hash of whitespace/case-normalized text — for detecting duplicate pages/chunks."""
    norm = " ".join(text.lower().split())
    return hashlib.md5(norm.encode("utf-8")).hexdigest()

# Rough word-based chunking. The client's context window is small, so we keep chunks
# short. ~60 words ≈ ~80-90 tokens for latin text (more for Cyrillic) — deliberately
# conservative so several chunks + memory + question still fit MAX_INPUT_TOKENS.
CHUNK_WORDS = 180
OVERLAP_WORDS = 30
EMBED_BATCH = 32


def parse_file(path) -> tuple[dict, str]:
    """Split a raw/*.md file into (front-matter dict, body)."""
    text = path.read_text(encoding="utf-8")
    meta: dict = {}
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm = text[3:end].strip()
            body = text[end + 4 :].lstrip("\n")
            for line in fm.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
    return meta, body


def topic_for(url: str) -> str:
    """Coarse topic tag inferred from the URL path — used for light filtering/labelling."""
    u = url.lower()
    if "scholarship" in u:
        return "scholarship"
    if "grant" in u:
        return "grant"
    if "data-lab" in u or "datalab" in u or "ydl" in u:
        return "school"
    if "program" in u:
        return "program"
    if "faq" in u:
        return "faq"
    if "contact" in u:
        return "contact"
    return "general"


def chunk_text(body: str) -> list[str]:
    words = re.split(r"\s+", body.strip())
    if not words:
        return []
    chunks: list[str] = []
    step = max(1, CHUNK_WORDS - OVERLAP_WORDS)
    for start in range(0, len(words), step):
        piece = " ".join(words[start : start + CHUNK_WORDS]).strip()
        if len(piece) >= 40:  # drop tiny tail fragments
            chunks.append(piece)
        if start + CHUNK_WORDS >= len(words):
            break
    return chunks


def build() -> int:
    raw_dir = config.RAW_DIR
    files = sorted(raw_dir.glob("*.md"))
    if not files:
        print(f"No markdown files in {raw_dir}. Run the scraper first.")
        return 0

    store = get_store()
    if hasattr(store, "reset"):
        store.reset()

    pending_texts: list[str] = []
    pending_metas: list[dict] = []
    total_chunks = 0

    def flush() -> None:
        nonlocal total_chunks
        if not pending_texts:
            return
        vectors = providers.embed(pending_texts)
        # Verify embedding dimensionality on the very first batch.
        if total_chunks == 0 and vectors and len(vectors[0]) != config.EMBED_DIM:
            raise SystemExit(
                f"Embedding dim mismatch: got {len(vectors[0])}, expected {config.EMBED_DIM}. "
                f"Update EMBED_DIM in .env."
            )
        store.add(vectors, pending_metas)
        total_chunks += len(pending_texts)
        print(f"  embedded {total_chunks} chunks...", end="\r")
        pending_texts.clear()
        pending_metas.clear()

    seen_pages: set[str] = set()    # body hashes — drop duplicate pages (e.g. /x and /en/x)
    seen_chunks: set[str] = set()   # chunk hashes — drop repeated boilerplate (nav/mission)
    dup_pages = dup_chunks = 0

    for path in files:
        meta, body = parse_file(path)
        url = meta.get("source_url", path.name)
        lang = meta.get("lang", "unknown")
        topic = topic_for(url)

        # Skip whole pages whose normalized body we've already ingested under another URL.
        page_key = _norm_hash(body)
        if page_key in seen_pages:
            dup_pages += 1
            continue
        seen_pages.add(page_key)

        for chunk in chunk_text(body):
            ckey = _norm_hash(chunk)
            if ckey in seen_chunks:  # boilerplate shared across pages
                dup_chunks += 1
                continue
            seen_chunks.add(ckey)
            pending_texts.append(chunk)
            pending_metas.append(
                {"chunk_text": chunk, "source_url": url, "lang": lang, "topic": topic}
            )
            if len(pending_texts) >= EMBED_BATCH:
                flush()
    flush()

    store.save()
    print(
        f"\nIngest complete: {total_chunks} chunks from {len(files)} pages "
        f"(skipped {dup_pages} duplicate pages, {dup_chunks} duplicate chunks)."
    )
    print(f"Vector backend: {config.VECTOR_BACKEND}  |  store count: {store.count()}")

    # Surface the store decision rule from the plan.
    if isinstance(store, NumpyStore) and total_chunks > 50_000:
        print(
            "NOTE: >50k chunks — consider switching VECTOR_BACKEND=pgvector for scale."
        )
    return total_chunks


if __name__ == "__main__":
    sys.exit(0 if build() else 1)
