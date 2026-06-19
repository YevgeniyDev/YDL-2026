"""Vector store abstraction with two interchangeable backends.

`NumpyStore` (default) keeps all vectors in a single in-memory matrix persisted to disk —
perfect for a small site KB (a few hundred / thousand chunks): brute-force cosine is
sub-millisecond and needs zero external infrastructure.

`PgVectorStore` is the fallback for a genuinely large corpus; same interface, so switching
is a one-line config change (VECTOR_BACKEND=pgvector).

Distances are COSINE distance: 0.0 = identical, 1.0 = orthogonal, 2.0 = opposite.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from . import config


@dataclass
class Hit:
    chunk_text: str
    source_url: str
    lang: str
    topic: str
    distance: float


class VectorStore(Protocol):
    def add(self, vectors: list[list[float]], metas: list[dict]) -> None: ...
    def search(self, query_vector: list[float], k: int) -> list[Hit]: ...
    def count(self) -> int: ...
    def save(self) -> None: ...


def _normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


class NumpyStore:
    """File-based store: vectors.npy (float32 matrix) + meta.json (parallel metadata list)."""

    def __init__(self, index_dir: Path | None = None) -> None:
        self.dir = index_dir or config.INDEX_DIR
        self.vectors_path = self.dir / "vectors.npy"
        self.meta_path = self.dir / "meta.json"
        self._vectors: np.ndarray | None = None  # normalized, shape (N, dim)
        self._metas: list[dict] = []
        if self.vectors_path.exists() and self.meta_path.exists():
            self._load()

    # --- persistence ---
    def _load(self) -> None:
        self._vectors = np.load(self.vectors_path).astype(np.float32)
        self._metas = json.loads(self.meta_path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        if self._vectors is None:
            self._vectors = np.zeros((0, config.EMBED_DIM), dtype=np.float32)
        np.save(self.vectors_path, self._vectors)
        self.meta_path.write_text(
            json.dumps(self._metas, ensure_ascii=False), encoding="utf-8"
        )

    # --- writes ---
    def reset(self) -> None:
        self._vectors = None
        self._metas = []

    def add(self, vectors: list[list[float]], metas: list[dict]) -> None:
        if not vectors:
            return
        new = _normalize(np.asarray(vectors, dtype=np.float32))
        if self._vectors is None or len(self._metas) == 0:
            self._vectors = new
        else:
            self._vectors = np.vstack([self._vectors, new])
        self._metas.extend(metas)

    # --- reads ---
    def count(self) -> int:
        return len(self._metas)

    def search(self, query_vector: list[float], k: int) -> list[Hit]:
        if self._vectors is None or len(self._metas) == 0:
            return []
        q = _normalize(np.asarray([query_vector], dtype=np.float32))[0]
        # Cosine similarity via dot product on normalized vectors; distance = 1 - sim.
        sims = self._vectors @ q
        k = min(k, len(self._metas))
        top_idx = np.argpartition(-sims, k - 1)[:k]
        top_idx = top_idx[np.argsort(-sims[top_idx])]
        hits: list[Hit] = []
        for i in top_idx:
            m = self._metas[int(i)]
            hits.append(
                Hit(
                    chunk_text=m["chunk_text"],
                    source_url=m.get("source_url", ""),
                    lang=m.get("lang", ""),
                    topic=m.get("topic", ""),
                    distance=float(1.0 - sims[int(i)]),
                )
            )
        return hits


class PgVectorStore:
    """Postgres + pgvector backend. Used only when VECTOR_BACKEND=pgvector.

    Requires the `vector` extension and the `documents` table from schema.sql.
    """

    def __init__(self, dsn: str | None = None) -> None:
        import psycopg  # imported lazily so numpy-only deployments don't need it

        self._psycopg = psycopg
        self.dsn = dsn or config.DATABASE_URL
        self._conn = psycopg.connect(self.dsn, autocommit=True)

    def reset(self) -> None:
        with self._conn.cursor() as cur:
            cur.execute("TRUNCATE documents;")

    def add(self, vectors: list[list[float]], metas: list[dict]) -> None:
        if not vectors:
            return
        with self._conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO documents (source_url, lang, topic, chunk_text, embedding)"
                " VALUES (%s, %s, %s, %s, %s)",
                [
                    (
                        m.get("source_url", ""),
                        m.get("lang", ""),
                        m.get("topic", ""),
                        m["chunk_text"],
                        "[" + ",".join(str(x) for x in vec) + "]",
                    )
                    for vec, m in zip(vectors, metas)
                ],
            )

    def count(self) -> int:
        with self._conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM documents;")
            return int(cur.fetchone()[0])

    def search(self, query_vector: list[float], k: int) -> list[Hit]:
        vec_literal = "[" + ",".join(str(x) for x in query_vector) + "]"
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT chunk_text, source_url, lang, topic, embedding <=> %s AS distance"
                " FROM documents ORDER BY distance LIMIT %s",
                (vec_literal, k),
            )
            return [
                Hit(chunk_text=r[0], source_url=r[1], lang=r[2], topic=r[3], distance=float(r[4]))
                for r in cur.fetchall()
            ]

    def save(self) -> None:
        # Postgres persists on write; nothing to flush.
        pass


def get_store() -> VectorStore:
    """Factory: returns the configured backend."""
    if config.VECTOR_BACKEND == "pgvector":
        return PgVectorStore()
    return NumpyStore()
