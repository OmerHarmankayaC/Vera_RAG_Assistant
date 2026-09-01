# Vera Q&A — frontend

React + Vite single-page app for the hosted demo of the
[Vera-Finance Local RAG Q&A Assistant](../README.md). It is a thin client: it streams tokens
from `POST /api/ask` and renders them, with the retrieval and generation happening in
[`server_deploy/`](../server_deploy/README.md).

## Structure

```
src/
├── pages/
│   ├── Home.jsx          # landing view + the "before you start" demo notice
│   ├── ChatPage.jsx      # standalone chat route (no shared header chrome)
│   └── Chat.jsx          # streaming, error handling, rate-limit countdown
└── components/
    ├── DemoNotice.jsx    # expectations: slow server, small model, usage limits
    ├── ChatMessage.jsx   # user / assistant / system-notice rendering + source line
    ├── SampleQuestions.jsx
    ├── Header.jsx
    └── Footer.jsx
```

Design is deliberately editorial and flat: one accent colour, hairline rules, no cards or
shadows. All styling is plain CSS with custom properties in `src/index.css` — no framework.

## What the chat client handles

- **Streaming.** Reads the `text/plain` response body incrementally so tokens appear as the
  model produces them, rather than after 30 seconds of blank screen.
- **Rate limits.** A `429` carries the exact limit that was hit; the message is rendered
  verbatim as a `NOTICE` message, the input is disabled, and a countdown ticks down from
  `Retry-After`.
- **Quota display.** `X-Demo-Quota-Remaining-Day` from each response drives the
  "*N questions left today*" line under the input.
- **Failure.** Network errors and server errors get distinct, non-alarming copy — on a
  CPU-only demo box, both are expected occasionally.

The usage numbers in `DemoNotice.jsx` are kept in sync by hand with `DEMO_RATE_LIMITS` in
[`server_deploy/config.py`](../server_deploy/config.py).

## Development

```bash
npm install
npm run dev -- --port 5183
```

`/api` is proxied to `http://127.0.0.1:8010` (the dev backend). Override with
`VITE_API_PROXY=http://127.0.0.1:8000 npm run dev`.

```bash
npm run lint      # oxlint
npm run build     # builds into ../server_deploy/static/, served by FastAPI under /static
```

Deploy with [`../deploy-frontend.sh`](../deploy-frontend.sh) — it builds and rsyncs in one step.
