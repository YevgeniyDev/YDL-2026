# Yessenov Foundation — RAG Chatbot

An official-but-friendly assistant that answers questions about the Shakhmardan Yessenov
Foundation's **grants, scholarships, and programs (incl. Yessenov Data Lab)** — grounded
**only** in content scraped from [yessenovfoundation.org](https://yessenovfoundation.org).

Key properties:
- **No hallucination.** If the answer isn't in the retrieved site content, the bot says so
  and points the user to contact a real person.
- **Answers in the user's language** (Russian / English / Kazakh).
- **Small-context-safe.** Uses RAG for knowledge + a rolling summary for chat memory, so it
  never overflows the client's small LLM context window.
- **Optional admin email.** A button sends a short LLM-written conversation summary to the
  admin (yourself only) via MailerSend — never automatically, never in a loop.

## Architecture

```
scraper/scrape.py   crawl the site  -> data/raw/*.md   (reproducible knowledge base)
engine/ingest.py    chunk + embed    -> data/index/     (vector store)
engine/rag.py       retrieve -> grounded prompt -> grounded answer OR "contact a human"
app.py              Streamlit chat UI (thin shell over the UI-agnostic engine/)
```

The `engine/` package is UI-agnostic on purpose: a Telegram adapter can reuse it without a
rewrite. The vector store sits behind one interface with two backends — `numpy` (default,
file-based, zero infra) and `pgvector` (fallback for a large corpus); flip with
`VECTOR_BACKEND` in `.env`.

## Setup

```bash
cd "Task 5/yessenov-bot"
python -m venv .venv
.venv\Scripts\activate            # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt

cp .env.example .env              # then fill in the real values (see below)
```

Fill `.env` with the **client-provided** credentials (confirm exact values first):
- `LLM_BASE_URL`, `CHAT_MODEL`, `CHAT_API_KEY`
- `EMBED_BASE_URL`, `EMBED_MODEL`, `EMBED_API_KEY`, `EMBED_DIM` (1024)
- `MAILERSEND_API_KEY`, `ADMIN_EMAIL` (your own inbox only)

## Build the knowledge base

```bash
python scraper/scrape.py          # -> data/raw/*.md   (re-runnable)
python -m engine.ingest           # -> data/index/     (prints the chunk count)
```

`ingest` prints the total chunk count. With a small corpus (the expected case) keep
`VECTOR_BACKEND=numpy`. Only if it reports a very large count (~50k+) switch to
`VECTOR_BACKEND=pgvector`, then `psql "$DATABASE_URL" -f schema.sql` and re-run ingest.

## Run

```bash
streamlit run app.py
```

## Tuning anti-hallucination

`RELEVANCE_MAX_DISTANCE` (cosine distance, 0=identical) is the gate: if the best retrieved
chunk is farther than this, the bot returns the fixed "I don't know — contact the
foundation" reply instead of guessing. Lower = stricter. Calibrate by asking a few real and
a few off-topic questions and watching the distances in the **Sources** panel.

## Security notes

- `.env` is git-ignored; only `.env.example` (placeholders) is committed.
- The email function sends **only** to `ADMIN_EMAIL`, **only** on a button press, and the UI
  disables the button after one send — protecting the sending domain's reputation.
