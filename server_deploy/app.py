"""Web interface for the Vera-Finance RAG Q&A assistant (FastAPI)."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from answer import stream_answer_query
from external_api import EXTERNAL_API_PATH
from external_api import router as external_api_router

STATIC_DIR = Path(__file__).parent / "static"

limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"])

app = FastAPI(title="Vera-Finance Q&A")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.post("/api/ask")
@limiter.limit("5/minute")
def ask(request: Request, q: Question) -> StreamingResponse:
    return StreamingResponse(stream_answer_query(q.question), media_type="text/plain")


app.include_router(external_api_router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/{full_path:path}", response_class=HTMLResponse)
def spa(full_path: str) -> str:
    # single-page app: let the React router handle any non-API, non-static path
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")
