"""Ingestion pipeline: read docs/, chunk, embed, store in SQLite.

Re-runnable: each run rebuilds the documents table from scratch so
added/edited docs are picked up cleanly.

Usage: python ingest.py
"""

import json
import sqlite3
import sys

import config
import foundry_client


def read_documents() -> list[tuple[str, str]]:
    """Return (source_name, text) pairs from the docs/ folder."""
    if not config.DOCS_DIR.exists():
        sys.exit(f"Docs folder not found: {config.DOCS_DIR}")
    docs = []
    for path in sorted(config.DOCS_DIR.glob("*")):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8").strip()
        if text:
            docs.append((path.name, text))
    if not docs:
        sys.exit(f"No .md/.txt files found in {config.DOCS_DIR}")
    return docs


def chunk_text(text: str, min_chars: int = 200) -> list[str]:
    """Split a document into paragraph-level chunks.

    Consecutive short paragraphs are merged so each chunk carries enough
    context to be retrievable on its own. A markdown heading is glued to
    the paragraph that follows it.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buffer = ""
    for para in paragraphs:
        buffer = f"{buffer}\n\n{para}".strip() if buffer else para
        # keep accumulating while the buffer is short or ends in a heading
        if len(buffer) >= min_chars and not buffer.splitlines()[-1].startswith("#"):
            chunks.append(buffer)
            buffer = ""
    if buffer:
        if chunks and len(buffer) < min_chars:
            chunks[-1] = f"{chunks[-1]}\n\n{buffer}"
        else:
            chunks.append(buffer)
    return chunks


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS documents")
    conn.execute(
        """
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding TEXT NOT NULL  -- JSON array of floats
        )
        """
    )


def main() -> None:
    docs = read_documents()
    print(f"Found {len(docs)} document(s) in {config.DOCS_DIR.name}/")

    all_chunks: list[tuple[str, str]] = []  # (source, chunk_text)
    for source, text in docs:
        for chunk in chunk_text(text):
            all_chunks.append((source, chunk))
    print(f"Split into {len(all_chunks)} chunk(s). Generating embeddings...")

    embeddings = foundry_client.embed_texts([c for _, c in all_chunks])

    conn = sqlite3.connect(config.DB_PATH)
    try:
        init_db(conn)
        conn.executemany(
            "INSERT INTO documents (source, content, embedding) VALUES (?, ?, ?)",
            [
                (source, content, json.dumps(vector))
                for (source, content), vector in zip(all_chunks, embeddings)
            ],
        )
        conn.commit()
    finally:
        conn.close()

    print(f"Ingestion complete: {len(all_chunks)} chunks stored in {config.DB_PATH.name}")


if __name__ == "__main__":
    main()
