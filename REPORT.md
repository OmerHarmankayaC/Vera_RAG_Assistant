# Project Report: Vera-Finance Local RAG Q&A Assistant

## Goal

Build a question-answering assistant for Vera-Finance (an AI-powered personal finance iOS app) that runs **entirely offline** on a MacBook (Apple Silicon), using retrieval-augmented generation so answers are grounded in curated product documentation rather than the model's training data.

## Why RAG (and why local)?

Small local models know nothing about a specific niche product like Vera-Finance, and even large cloud models would hallucinate details. RAG solves this by retrieving the relevant passages from a curated knowledge base and instructing the model to answer *only* from them. Running locally via Microsoft Foundry Local gives privacy (no data leaves the machine), zero API cost, and offline operation — a good match for a demo of on-device AI.

## Architecture

Four small Python modules over a single SQLite file:

1. **Ingestion** (`ingest.py`) — reads markdown passages from `docs_vera/`, splits them into paragraph-level chunks (short paragraphs merged, headings glued to their following paragraph), embeds each chunk with `qwen3-embedding-0.6b`, and stores `(source, content, embedding)` rows in SQLite. The pipeline is idempotent: each run rebuilds the table. The current corpus is 12 documents → 35 chunks of 1024-dimensional vectors.
2. **Retrieval** (`retrieval.py`) — embeds the query and ranks every stored chunk by cosine similarity (NumPy, brute force). Returns the top-*k* chunks with source names and scores.
3. **Generation** (`answer.py`) — builds a system prompt containing the retrieved chunks and strict grounding rules ("use only the context; say 'I don't have that information' if it's not covered; cite the source"), then calls the local chat model (`qwen2.5-1.5b`) through the Foundry Local SDK.
4. **CLI** (`main.py`) — interactive loop with streamed output and per-answer timing.

## Design decisions

- **SQLite over a vector DB** — with 35 chunks, brute-force cosine similarity is microseconds of work; a vector database would add operational complexity for zero benefit at this scale.
- **Embeddings stored as JSON** — human-inspectable and portable; binary blobs would save space but complicate debugging for negligible gain here.
- **Model choice** — `qwen2.5-1.5b` balances answer quality and latency on Apple Silicon GPU (Metal via ONNX Runtime). The 0.5b variant is faster but noticeably weaker at following the grounding instructions; larger models (4b+) improve quality but push response times past the 1–3 s target.
- **Paragraph-level chunking** — the source documents are short, hand-written passages, so paragraphs are natural semantic units; no overlapping-window chunking needed.
- **Foundry Local SDK over raw REST** — the SDK handles model download, loading, and lifecycle; the underlying endpoint remains OpenAI-compatible.
- **Grounding as prompt policy** — the refusal wording is fixed (`"I don't have that information."`) so it is both a rule the model follows and a string the code can detect, which is how the appended source line is suppressed on refusals.

## Cross-language behaviour

The knowledge base is English; questions arrive in Turkish as often as English. Rather than translating the corpus or the query, the system prompt instructs the model to judge passage relevance *by topic, not by language*, and to answer in the language the question was asked in. Embedding retrieval carries this on its own — `qwen3-embedding-0.6b` places a Turkish question near its English answer in vector space — so no translation step was needed.

## From offline CLI to a public demo

The requirements listed a web interface as a v2 stretch goal. It was built, with one substitution: Foundry Local targets macOS/Windows, and the demo runs on a small Linux VPS, so **Ollama** provides the equivalent OpenAI-compatible local endpoint there (`ollama_client.py` in place of `foundry_client.py`). Chunking, retrieval, prompting and grounding are unchanged; `TOP_K` drops from 5 to 3 because on CPU the prompt-evaluation pass dominates time-to-first-token.

The frontend is a React SPA served by the same FastAPI process, streaming tokens as they are generated so a 30-second answer doesn't look like a hang.

**Operating a public demo introduced a problem the offline version doesn't have:** one answer occupies the entire CPU for tens of seconds, so a single impatient visitor can make the site unusable for everyone. The service therefore enforces sliding-window limits in two scopes simultaneously — per visitor (1/second, 3/minute, 10/day) and across all visitors (3/second, 5/minute, 100/day) — where every rule must pass and a rejected request consumes no quota. Rejections name the specific limit that was hit and how long to wait, and the UI states plainly, before the first question, that the demo is slow and that a 1.5B model can be wrong.

## Handling small-model failure modes

Two failure modes showed up in testing that no amount of retrieval quality addresses.

**Degeneration loops.** Asked something awkward — often a Turkish question against the English corpus — the model sometimes repeats a fragment until it exhausts `MAX_TOKENS` (`"...tamamen tamamen tamamen..."` ×125, or 300 characters of `#`). A parameter sweep across temperature and frequency/presence penalties found no safe setting: every configuration that fixed one question introduced a loop on another, and removing the penalties entirely made things worse. The fix is therefore deterministic rather than statistical — `text_guard.py` detects a short fragment repeating back-to-back, stops generation immediately, keeps the usable prefix and states plainly that generation was cut short. On the CPU-only demo server this also saves the compute that would have gone into generating the rest of the noise.

**Over-answering on adjacent topics.** Refusal is reliable when a topic is absent outright (pricing, named individuals), but a question *near* the corpus — platform availability, which the documents never state — can still draw an assertion instead of a refusal. This is a capability limit of a 1.5B model following a multi-step instruction, not a retrieval problem; a larger chat model resolves it at the cost of the latency target.

## Known limitations

- Quality is bounded by a 1.5B-parameter model: occasional stiff phrasing, and grounding discipline, while good, is not perfect (see the over-answering case above).
- Retrieval is purely semantic; there is no keyword/BM25 fallback, so very short or ambiguous queries can retrieve suboptimal chunks.
- The knowledge base is manually curated; the assistant only knows what the docs say (this is also the point).
- Single-turn: no conversation memory between questions (each question is answered independently).
- The whole index is loaded from SQLite on every query — trivial at this scale, but would need caching for thousands of chunks.
- Embeddings are model-specific: an index built with one embedding model cannot be served by another, which is why the macOS and Linux deployments each build their own database.
- Rate-limit counters live in process memory, so restarting the service resets every visitor's quota. Fine for one process; a multi-worker deployment would need shared state.

## Possible next steps

- Hybrid retrieval (cosine + keyword match) for robustness on short queries.
- Conversation history support with context-window management.
- Re-ranking the top-*k* with a cross-encoder before generation.
- Caching the index in memory across queries.
