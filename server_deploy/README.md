# Hosted demo — deployment guide

This directory is the **secondary** half of the project: the same RAG pipeline as the root
CLI, wrapped in a FastAPI service so the assistant can be demonstrated from a browser at
[rag.omerharmankaya.com](https://rag.omerharmankaya.com).

The only substantive change is the inference client. Microsoft Foundry Local targets
macOS/Windows; the demo box is a small Linux VPS, so [Ollama](https://ollama.com) supplies
the equivalent OpenAI-compatible local endpoint there. Chunking, retrieval, the prompt and
the grounding rules are byte-for-byte the same logic — see
[`ollama_client.py`](ollama_client.py) next to the root's `foundry_client.py`.

```
Browser ──► nginx (TLS) ──► uvicorn 127.0.0.1:8000 ──► Ollama 127.0.0.1:11434
                                    │
                                    ├── /api/ask                streamed answers, rate limited
                                    ├── /api/limits             limits + this visitor's quota
                                    ├── /api/external/vera-qa   shared-secret, server-to-server
                                    └── /*                      React SPA from static/
```

## Files

| File | Purpose |
|---|---|
| [`app.py`](app.py) | FastAPI app: routes, CORS, rate limiting, SPA fallback. |
| [`rate_limit.py`](rate_limit.py) | Sliding-window limiter — per-visitor and global scopes. |
| [`client_ip.py`](client_ip.py) | Resolves the real caller behind the reverse proxy. |
| [`external_api.py`](external_api.py) | Authenticated endpoint for the landing-page widget. |
| [`answer.py`](answer.py) / [`retrieval.py`](retrieval.py) / [`ingest.py`](ingest.py) | The RAG pipeline, Ollama variant. |
| [`text_guard.py`](text_guard.py) | Stops runaway repetition mid-stream (identical to the root copy). |
| [`config.py`](config.py) | Models, retrieval/sampling settings, **rate limits**. |
| [`vera-rag.service`](vera-rag.service) | systemd unit (hardened: `ProtectSystem=strict`, dedicated user). |
| [`test_rate_limit.py`](test_rate_limit.py) / [`test_api.py`](test_api.py) / [`test_text_guard.py`](test_text_guard.py) | Tests — stdlib `unittest`, no model required. |

## Rate limits

A single answer occupies the whole CPU for tens of seconds, so the public endpoint enforces
two scopes at once. **Every** rule must pass; a rejected request consumes no quota.

| Scope | Per second | Per minute | Per day |
|---|---|---|---|
| Per visitor (IP) | 1 | 3 | 10 |
| All visitors combined | 3 | 5 | 100 |

Change them in one place — `DEMO_RATE_LIMITS` in [`config.py`](config.py) — as
`(limit, window_seconds, scope, label)` tuples. Keep the numbers shown to visitors in
`RAG/src/components/DemoNotice.jsx` in sync.

A rejection returns `429` with the rule that was hit:

```json
{
  "error": {
    "code": "rate_limited_user_minute",
    "scope": "ip",
    "window": "minute",
    "limit": 3,
    "retry_after": 38,
    "message": "You've hit the limit of 3 questions per minute. Please wait 38 seconds and try again."
  }
}
```

plus a `Retry-After` header. Successful responses carry `X-Demo-Quota-Remaining-Day` and
`X-Demo-Quota-Remaining-Minute` so the UI can show what the visitor has left. The frontend
renders `error.message` verbatim and disables the input until the countdown expires.

The landing-page widget endpoint is **not** part of this budget — it is server-to-server
traffic with its own looser allowance (`EXTERNAL_API_RATE_LIMITS`, 20/minute per caller).

## Endpoints

| Method | Path | Auth | Notes |
|---|---|---|---|
| `POST` | `/api/ask` | none | `{"question": "..."}` (1–500 chars) → `text/plain` token stream. Demo limits apply. |
| `GET` | `/api/limits` | none | Configured limits + the caller's remaining quota. |
| `POST` | `/api/external/vera-qa` | `X-Vera-QA-Secret` | `{"question": "...", "history": []}` → `{"answer": "...", "sources": [...]}`. `history` is accepted and ignored in v1. |
| `GET` | `/*` | none | Serves the React SPA. |

## Deploying

Assumes Debian/Ubuntu. Adjust paths to taste; the unit file expects `/opt/vera-rag`.

**1 — Ollama and the models**

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:1.5b
ollama pull nomic-embed-text
```

**2 — Application user and code**

```bash
sudo useradd --system --home /opt/vera-rag --shell /usr/sbin/nologin vera-rag
sudo mkdir -p /opt/vera-rag
sudo rsync -a server_deploy/ /opt/vera-rag/     # code (contents of the dir)
sudo rsync -a docs_vera /opt/vera-rag/         # knowledge base (the dir itself)
cd /opt/vera-rag
sudo python3 -m venv .venv
sudo .venv/bin/pip install -r requirements.txt
```

**3 — Secret and index**

```bash
sudo cp .env.example .env && sudo nano .env      # set VERA_QA_SHARED_SECRET
sudo .venv/bin/python ingest.py                  # builds vera_rag.db with nomic-embed-text
sudo chown -R vera-rag:vera-rag /opt/vera-rag
```

> The index must be rebuilt on the server: embeddings are model-specific, so a
> `vera_rag.db` built locally with `qwen3-embedding-0.6b` (1024-d) is not interchangeable
> with one built by `nomic-embed-text` (768-d).

**4 — Service**

```bash
sudo cp vera-rag.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vera-rag
sudo systemctl status vera-rag
```

**5 — nginx**

Two directives are not optional:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;

    # Required: without this every visitor looks like 127.0.0.1 to the app and the
    # per-visitor rate limits collapse into one shared bucket for the whole internet.
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header Host $host;

    # Required: answers stream token by token — buffering holds them back until the
    # response completes, which on a CPU box means 30 seconds of blank screen.
    proxy_buffering off;
    proxy_read_timeout 300s;
}
```

`TRUST_FORWARDED_FOR` in [`config.py`](config.py) must stay `True` for this, and is only
safe because uvicorn binds `127.0.0.1` — the header is client-controlled and trivially
spoofed if the port is ever exposed directly.

**6 — Frontend**

```bash
VERA_DEPLOY_HOST=root@your-server ../deploy-frontend.sh
```

Builds `RAG/` into `server_deploy/static/` and rsyncs it to `/opt/vera-rag/static/`.

## Local development

```bash
# terminal 1 — API on :8010 with reload
cd server_deploy && ../.venv/bin/python -m uvicorn app:app --port 8010 --reload

# terminal 2 — Vite dev server on :5183, proxying /api to :8010
cd RAG && npm run dev -- --port 5183
```

Both are also defined in [`.claude/launch.json`](../.claude/launch.json). Point the proxy
elsewhere with `VITE_API_PROXY=http://127.0.0.1:8000 npm run dev`.

Rate-limit behaviour can be exercised without Ollama running — generation fails gracefully
and the limit responses are unaffected:

```bash
cd server_deploy && python -m unittest discover -p "test_*.py" -v
```

## Operations

```bash
sudo systemctl restart vera-rag      # after a code change
sudo journalctl -u vera-rag -f       # logs (tracebacks from failed generations land here)
sudo systemctl status ollama
```

Rate-limit counters live in process memory, so a restart clears every visitor's quota.
