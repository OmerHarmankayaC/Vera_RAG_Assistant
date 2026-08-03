# Vera-Finance Local RAG Q&A Assistant

A fully offline, retrieval-augmented generation (RAG) Q&A assistant that answers questions about **Vera-Finance** (an AI-powered personal finance iOS app). All inference runs on-device on macOS (Apple Silicon) via **Microsoft Foundry Local** — no internet connection needed at query time.

## Architecture

```
User question (CLI)
      │
      ▼
answer_query(question)            # answer.py
      │
      ├─► get_top_chunks(q, k=3)  # retrieval.py
      │      ├─ embed the query        (qwen3-embedding-0.6b via Foundry Local)
      │      └─ cosine similarity vs all chunk embeddings in SQLite → top-k
      │
      └─► chat model (qwen2.5-1.5b via Foundry Local)
             system prompt: answer only from context, cite source,
             say "I don't have that information" if not covered
      │
      ▼
   Grounded answer (+ source)
```

- **Ingestion** ([ingest.py](ingest.py)): reads `docs/*.md`, splits into paragraph-level chunks, embeds each chunk, stores text + JSON embedding in SQLite (`vera_rag.db`). Re-runnable — rebuilds the index each run.
- **Retrieval** ([retrieval.py](retrieval.py)): brute-force cosine similarity over all stored embeddings (fine at this scale; no vector DB needed).
- **Generation** ([answer.py](answer.py)): builds a grounded prompt from the retrieved chunks and calls the Foundry Local chat model.
- **CLI** ([main.py](main.py)): interactive question loop with streaming output and response timing.

## Setup

### 1. Install Foundry Local (macOS, Apple Silicon)

```bash
brew tap microsoft/foundrylocal
brew install foundrylocal
foundry service start
```

### 2. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Models

The models are downloaded automatically on first use (via the Foundry Local SDK), or you can pre-download the chat model with:

```bash
foundry model download qwen2.5-1.5b
```

Models used (configurable in [config.py](config.py)):

| Role      | Model                 | Size (GPU) |
|-----------|-----------------------|------------|
| Embedding | `qwen3-embedding-0.6b`| ~0.6 GB    |
| Chat      | `qwen2.5-1.5b`        | ~1.5 GB    |

Both run with Apple Metal GPU acceleration through ONNX Runtime — no CUDA needed.

## Usage

```bash
# 1. Build (or rebuild) the index — run after adding/editing files in docs/
python ingest.py

# 2. Ask questions interactively
python main.py
```

One-shot from the command line:

```bash
python answer.py "How does the AI in Vera-Finance work?"
python retrieval.py "data privacy"        # inspect retrieval only
```

## Content

The knowledge base lives in [docs/](docs/) as short markdown passages (overview, features, AI engine, onboarding, privacy, FAQ). **These are draft placeholders** — replace their content with the real Vera-Finance details, then re-run `python ingest.py`.

## Behavior / acceptance

- Questions covered by the docs → grounded answer, with source file cited where possible.
- Questions not covered → "I don't have that information." — no fabrication.
- Blank input → prompt again, no crash.
- Typical response time: ~1–3 s on Apple Silicon GPU. If too slow, reduce `TOP_K` or switch `CHAT_MODEL_ALIAS` to `qwen2.5-0.5b`; for better answer quality (at some latency cost), try `qwen3-4b`.

## Out of scope (v1)

External vector databases, multi-user web service, fine-tuning. A Streamlit UI is a possible v2.
