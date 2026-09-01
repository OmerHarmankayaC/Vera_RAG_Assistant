"""Retrieval: embed the query and rank stored chunks by cosine similarity."""

import json
import sqlite3
import sys

import numpy as np

import config
import foundry_client


def _load_chunks() -> list[tuple[str, str, np.ndarray]]:
    """Return (source, content, embedding) for every stored chunk."""
    if not config.DB_PATH.exists():
        sys.exit(f"Database not found ({config.DB_PATH.name}). Run `python ingest.py` first.")
    conn = sqlite3.connect(config.DB_PATH)
    try:
        rows = conn.execute("SELECT source, content, embedding FROM documents").fetchall()
    finally:
        conn.close()
    if not rows:
        sys.exit("Database is empty. Run `python ingest.py` first.")
    return [
        (source, content, np.array(json.loads(embedding), dtype=np.float32))
        for source, content, embedding in rows
    ]


def get_top_chunks(query: str, k: int = config.TOP_K) -> list[dict]:
    """Return the k most relevant chunks for the query.

    Each result is {"source": str, "content": str, "score": float}.
    Brute-force cosine similarity — fine at this dataset size.
    """
    chunks = _load_chunks()
    query_vec = np.array(foundry_client.embed_text(query), dtype=np.float32)
    query_norm = np.linalg.norm(query_vec)

    scored = []
    for source, content, vec in chunks:
        denom = query_norm * np.linalg.norm(vec)
        score = float(np.dot(query_vec, vec) / denom) if denom else 0.0
        scored.append({"source": source, "content": content, "score": score})

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:k]


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "What is Vera-Finance?"
    for result in get_top_chunks(question):
        print(f"[{result['score']:.3f}] {result['source']}")
        print(result["content"][:200], "...\n")
