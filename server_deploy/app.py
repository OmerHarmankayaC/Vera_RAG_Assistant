"""Web interface for the Vera-Finance RAG Q&A assistant (FastAPI)."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import config
from answer import stream_answer_query
from client_ip import get_client_ip
from external_api import EXTERNAL_API_PATH
from external_api import router as external_api_router
from rate_limit import RateLimiter, Rule, describe

STATIC_DIR = Path(__file__).parent / "static"

# Per-visitor *and* whole-server limits; see config.DEMO_RATE_LIMITS.
demo_limiter = RateLimiter([Rule(*rule) for rule in config.DEMO_RATE_LIMITS])

app = FastAPI(title="Vera-Finance Q&A")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    # so the embedded widget can read the quota/backoff hints cross-origin
    expose_headers=["Retry-After", "X-Demo-Quota-Remaining-Day", "X-Demo-Quota-Remaining-Minute"],
)


@app.middleware("http")
async def _strip_cors_for_external_api(request: Request, call_next):
    # The external API is server-to-server only (no browser origin) — drop any Origin
    # header before CORSMiddleware sees it so that route never gets CORS headers.
    # Starlette's add_middleware() inserts at the front of the stack, so the *last*
    # middleware registered ends up outermost — this must stay below CORSMiddleware
    # in the file for that ordering to hold. Every other route (including /api/ask)
    # is unaffected.
    if request.url.path == EXTERNAL_API_PATH:
        request.scope["headers"] = [
            (k, v) for k, v in request.scope["headers"] if k != b"origin"
        ]
    return await call_next(request)


class Question(BaseModel):
    # each answer costs several seconds to tens of seconds of CPU inference — cap length to limit abuse cost
    question: str = Field(min_length=1, max_length=500)


def _quota_headers(remaining: dict[str, int]) -> dict[str, str]:
    headers = {}
    if "day" in remaining:
        headers["X-Demo-Quota-Remaining-Day"] = str(remaining["day"])
    if "minute" in remaining:
        headers["X-Demo-Quota-Remaining-Minute"] = str(remaining["minute"])
    return headers


@app.get("/api/limits")
def limits(request: Request) -> JSONResponse:
    """What the demo allows, and what this visitor has left — powers the UI notice."""
    return JSONResponse(
        {
            "limits": {
                scope: {r.label: r.limit for r in demo_limiter.rules if r.scope == scope}
                for scope in ("ip", "global")
            },
            "remaining": demo_limiter.peek_remaining(get_client_ip(request)),
        }
    )


@app.post("/api/ask")
def ask(request: Request, q: Question):
    decision = demo_limiter.check(get_client_ip(request))
    if not decision.allowed:
        code, message = describe(decision.rejection)
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": code,
                    "scope": decision.rejection.rule.scope,
                    "window": decision.rejection.rule.label,
                    "limit": decision.rejection.rule.limit,
                    "retry_after": decision.rejection.retry_after_seconds,
                    "message": message,
                }
            },
            headers={
                "Retry-After": str(decision.rejection.retry_after_seconds),
                **_quota_headers(decision.remaining),
            },
        )

    return StreamingResponse(
        stream_answer_query(q.question),
        media_type="text/plain",
        headers=_quota_headers(decision.remaining),
    )


app.include_router(external_api_router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/{full_path:path}", response_class=HTMLResponse)
def spa(full_path: str) -> str:
    # single-page app: let the React router handle any non-API, non-static path
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")
