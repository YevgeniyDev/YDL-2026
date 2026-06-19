-- PostgreSQL + pgvector schema. Used ONLY when VECTOR_BACKEND=pgvector
-- (i.e. if the scraped corpus is large enough to outgrow the file-based store).
-- Apply with:  psql "$DATABASE_URL" -f schema.sql

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id          bigserial PRIMARY KEY,
    source_url  text NOT NULL,
    lang        text NOT NULL DEFAULT '',
    topic       text NOT NULL DEFAULT '',
    chunk_text  text NOT NULL,
    embedding   vector(1024) NOT NULL          -- text-1024 => 1024-dim
);

-- Cosine-distance index (matches the `<=>` operator used by PgVectorStore.search).
-- ivfflat needs ANALYZE after load; for small/medium corpora hnsw is also fine.
CREATE INDEX IF NOT EXISTS documents_embedding_cos
    ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
