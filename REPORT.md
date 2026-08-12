# Project Report (Draft): Vera-Finance Local RAG Q&A Assistant

## Goal

Build a question-answering assistant for Vera-Finance (an AI-powered personal finance iOS app) that runs **entirely offline** on a MacBook (Apple Silicon), using retrieval-augmented generation so answers are grounded in curated product documentation rather than the model's training data.

## Why RAG (and why local)?

Small local models know nothing about a specific niche product like Vera-Finance, and even large cloud models would hallucinate details. RAG solves this by retrieving the relevant passages from a curated knowledge base and instructing the model to answer *only* from them. Running locally via Microsoft Foundry Local gives privacy (no data leaves the machine), zero API cost, and offline operation — a good match for a demo of on-device AI.

## Architecture

Four small Python modules over a single SQLite file:

1. **Ingestion** (`ingest.py`) — reads markdown passages from `docs/`, splits them into paragraph-level chunks (short paragraphs merged, headings glued to their following paragraph), embeds each chunk with `qwen3-embedding-0.6b`, and stores `(source, content, embedding)` rows in SQLite. The pipeline is idempotent: each run rebuilds the table.
2. **Retrieval** (`retrieval.py`) — embeds the query and ranks every stored chunk by cosine similarity (NumPy, brute force). Returns the top-3 chunks with source names and scores.
3. **Generation** (`answer.py`) — builds a system prompt containing the retrieved chunks and strict grounding rules ("use only the context; say 'I don't have that information' if it's not covered; cite the source"), then calls the local chat model (`qwen2.5-1.5b`) through the Foundry Local SDK.
4. **CLI** (`main.py`) — interactive loop with streamed output and per-answer timing.

## Design decisions

- **SQLite over a vector DB** — with ~15–30 chunks, brute-force cosine similarity is microseconds of work; a vector database would add operational complexity for zero benefit at this scale.
- **Embeddings stored as JSON** — human-inspectable and portable; binary blobs would save space but complicate debugging for negligible gain here.
- **Model choice** — `qwen2.5-1.5b` balances answer quality and latency on Apple Silicon GPU (Metal via ONNX Runtime). The 0.5b variant is faster but noticeably weaker at following the grounding instructions; larger models (4b+) improve quality but push response times past the 1–3 s target.
- **Paragraph-level chunking** — the source documents are short, hand-written passages, so paragraphs are natural semantic units; no overlapping-window chunking needed.
- **Foundry Local SDK over raw REST** — the SDK handles model download, loading, and lifecycle; the underlying endpoint remains OpenAI-compatible.

## Known limitations

- Quality is bounded by a 1.5B-parameter model: occasional stiff phrasing, and grounding discipline, while good, is not perfect.
- Retrieval is purely semantic; there is no keyword/BM25 fallback, so very short or ambiguous queries can retrieve suboptimal chunks.
- The knowledge base is manually curated; the assistant only knows what the docs say (this is also the point).
- Single-turn: no conversation memory between questions (each question is answered independently).
- The whole index is loaded from SQLite on every query — trivial at this scale, but would need caching for thousands of chunks.

## Possible next steps

- Streamlit web UI (v2 stretch goal from the requirements).
- Hybrid retrieval (cosine + keyword match) for robustness on short queries.
- Conversation history support with context-window management.
