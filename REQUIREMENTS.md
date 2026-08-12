# Vera-Finance Local RAG Q&A Assistant — Requirements Document

## Purpose

A fully offline, RAG (Retrieval-Augmented Generation) based Q&A assistant that answers questions
about Vera-Finance (an AI-powered personal finance iOS app published on the App Store). Model
inference runs entirely on-device (macOS, Apple Silicon) using Microsoft Foundry Local — no
internet connection required.

Reference: Microsoft Tech Community — "Building Your First Local RAG Application with Foundry Local"
(https://techcommunity.microsoft.com/blog/azuredevcommunityblog/building-your-first-local-rag-application-with-foundry-local/4501968)
and the official tutorial: https://learn.microsoft.com/en-us/azure/foundry-local/tutorials/tutorial-build-rag-app

## Environment / Platform

- **OS:** macOS (Apple Silicon)
- **Runtime:** Foundry Local, installed via Homebrew (`brew tap microsoft/foundrylocal && brew install foundrylocal`)
- **Acceleration:** Apple Metal (GPU) — no CUDA needed, via the `--device GPU` flag
- **Language:** Python 3.x
- **Database:** SQLite (single file, serverless)

## Prerequisites (to be done by the user, before any code is written)

1. Install the Foundry Local CLI via Homebrew (~5 minutes)
2. Download and test one embedding model and one chat model:
   - `foundry model run <embedding-model> --device GPU`
   - `foundry model run <chat-model> --device GPU`
   - Use `foundry service list` to get the full model IDs (needed for API calls)
3. **Content preparation:** write 5–10 short passages/documents about Vera-Finance (markdown or
   plain text, ~1–3 paragraphs each), for example:
   - App's overall purpose and target user
   - Core features (budget tracking, spending categories, etc. — based on the actual feature set)
   - How the AI/recommendation engine works (high-level, technical detail not required)
   - Onboarding / first-use flow
   - Data privacy approach
   - Frequently asked questions (from real user feedback, if available)

## Architecture

```
User question
      │
      ▼
[CLI interface] → answer_query(question)
      │
      ├─► get_top_chunks(question, k=3)   # retrieval
      │        │
      │        ├─ embed the query (embedding model)
      │        └─ compute cosine similarity against all
      │           chunk embeddings in SQLite, return top-k
      │
      └─► send to Foundry Local chat model:
               system prompt: "Use only the given context,
               say you don't know if unsure, cite the source"
               + retrieved chunks + user question
      │
      ▼
   Answer (+ optional source passage name)
```

## Components

### 1. Ingestion pipeline (`ingest.py`)
- Reads text files from the `docs/` folder
- Splits each document into paragraph/passage-level chunks
- Generates an embedding for each chunk (Foundry Local embedding model)
- Writes chunk text + embedding vector to SQLite (`documents` table: id, source, content, embedding)
- Should be re-runnable (so ingestion can be repeated when documents are added/changed)

### 2. Retrieval (`retrieval.py`)
- `get_top_chunks(query: str, k: int = 3) -> list[str]`
- Embeds the query, computes cosine similarity against all embeddings in SQLite
  (brute-force is sufficient given the small dataset size — no external vector DB needed)
- Returns the k most relevant chunks (with source info)

### 3. Generation (`answer.py`)
- `answer_query(question: str) -> str`
- Uses the output of `get_top_chunks` as context
- System prompt: use only the given context, say "I don't have that information" if the context
  is insufficient, never fabricate, cite the source passage where possible
- Calls Foundry Local's OpenAI-compatible local REST API

### 4. Interface (`main.py`)
- v1: CLI — take a question via `input()`, call `answer_query()`, print the answer, loop until
  the user exits
- v2 (stretch goal, if time allows): a simple Streamlit web interface

## Acceptance Criteria

- A question with an answer covered in the documents → correct, document-grounded answer
- A question not covered in the documents → "I don't have that information" style response, no
  fabrication
- Response time: ~1–3 seconds for a typical question (on Apple Silicon GPU); if noticeably
  slower, discuss optimizing chunk count / model size
- Empty or malformed input (e.g. blank question) handled without crashing

## Out of Scope (v1)

- External vector database (Pinecone, Chroma, etc.) — SQLite is sufficient at this data scale
- Multi-user / persistent web service — single machine, single user
- Fine-tuning — using pre-trained models with retrieval only

## Deliverables

- Working Python project (`main.py`, `ingest.py`, `retrieval.py`, `answer.py`, `requirements.txt`)
- `docs/` folder (Vera-Finance content passages)
- `README.md`: setup steps (including Foundry Local installation), run instructions, architecture overview
- Short project report draft (RAG architecture, design decisions, known limitations) — base text
  for the demo/presentation day

## Notes

- This document is written to be handed off directly to Claude Code. All code will be written by
  Claude Code; Foundry Local installation and model downloads must be done by the user (on their
  own Apple Silicon Mac), since these can't run in a cloud/sandbox environment.
- The content passages (Vera-Finance documents) must be ready before coding begins — they're
  needed to test the ingestion pipeline.
