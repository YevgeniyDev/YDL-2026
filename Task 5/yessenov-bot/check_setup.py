"""Pre-flight check — run this BEFORE ingest to validate config + API connectivity.

It does NOT need the vector index; it only verifies that:
  1. .env is loaded and the endpoints/models resolve,
  2. the knowledge base was scraped,
  3. the embedding API responds with the expected dimensionality,
  4. the chat API responds.

Run:  python check_setup.py
"""
from __future__ import annotations

import sys

from engine import config, providers


def mask(key: str) -> str:
    if not key or key.startswith("replace-me"):
        return "(not set / placeholder)"
    return key[:6] + "…" + key[-4:]


def main() -> int:
    print("=== Configuration ===")
    print(f"  LLM_BASE_URL : {config.LLM_BASE_URL}")
    print(f"  CHAT_MODEL   : {config.CHAT_MODEL}")
    print(f"  CHAT_API_KEY : {mask(config.CHAT_API_KEY)}")
    print(f"  EMBED_BASE_URL: {config.EMBED_BASE_URL}")
    print(f"  EMBED_MODEL  : {config.EMBED_MODEL}")
    print(f"  EMBED_API_KEY: {mask(config.EMBED_API_KEY)}")
    print(f"  EMBED_DIM    : {config.EMBED_DIM}")
    print(f"  VECTOR_BACKEND: {config.VECTOR_BACKEND}")
    print()

    ok = True

    # 1) Knowledge base present?
    n_pages = len(list(config.RAW_DIR.glob("*.md")))
    print(f"=== Knowledge base ===\n  {n_pages} pages in {config.RAW_DIR}")
    if n_pages == 0:
        print("  ! No pages. Run: python scraper/scrape.py")
        ok = False
    print()

    # 2) Embedding API
    print("=== Embedding API ===")
    try:
        vec = providers.embed_one("Test embedding request.")
        print(f"  OK — returned vector of dim {len(vec)}")
        if len(vec) != config.EMBED_DIM:
            print(f"  ! Dim mismatch: expected {config.EMBED_DIM}. Update EMBED_DIM in .env.")
            ok = False
    except Exception as e:  # noqa: BLE001
        print(f"  FAILED: {type(e).__name__}: {e}")
        print("  Hint: the OpenAI SDK posts to <EMBED_BASE_URL>/embeddings.")
        print("        If you get a 404, set EMBED_BASE_URL to the base (…/v1), not …/v1/embeddings.")
        ok = False
    print()

    # 3) Chat API
    print("=== Chat API ===")
    try:
        reply = providers.chat(
            [{"role": "user", "content": "Reply with the single word: OK"}],
            max_tokens=10,
        )
        print(f"  OK — model replied: {reply!r}")
    except Exception as e:  # noqa: BLE001
        print(f"  FAILED: {type(e).__name__}: {e}")
        ok = False
    print()

    print("=== Result ===")
    print("  All checks passed — you can run ingest." if ok else "  Some checks failed — fix the above first.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
