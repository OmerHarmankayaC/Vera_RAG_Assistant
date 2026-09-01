"""External-facing endpoint for the Vera-Finance landing page chat widget.

Wraps the existing RAG pipeline (answer.py / ollama_client.py) behind shared-secret
authentication and per-IP rate limiting. Does not change retrieval, generation, or
the existing `rag.omerharmankaya.com` frontend routes (see app.py's `/api/ask`).

Contract: see requirements-vera-qa-backend-external-api.md (Integration Contract) —
request/response shape here must stay in sync with that document.
"""

import hmac
import os
import traceback

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import config
import ollama_client
import text_guard
from answer import _prepare
from client_ip import get_client_ip
from rate_limit import RateLimiter, Rule

EXTERNAL_API_PATH = "/api/external/vera-qa"
SHARED_SECRET_HEADER = "X-Vera-QA-Secret"
MAX_QUESTION_LENGTH = 1000
FRIENDLY_ERROR = "Sorry, the assistant is temporarily unavailable. Please try again in a moment."

router = APIRouter()

# Server-to-server traffic from the landing page, so it keeps its own looser
# budget instead of drawing on the public demo's per-visitor/global limits.
_limiter = RateLimiter([Rule(*rule) for rule in config.EXTERNAL_API_RATE_LIMITS])


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


def _excerpt(content: str, limit: int = 300) -> str:
    content = content.strip()
    return content if len(content) <= limit else content[:limit].rstrip() + "..."


@router.post(EXTERNAL_API_PATH)
async def vera_qa(request: Request) -> JSONResponse:
    # Rate limit before auth: protects the server from floods regardless of secret validity.
    if not _limiter.check(get_client_ip(request)).allowed:
        return _error_response(429, "rate_limited", "Too many requests. Please try again shortly.")

    expected_secret = os.environ.get("VERA_QA_SHARED_SECRET")
    provided_secret = request.headers.get(SHARED_SECRET_HEADER)
    if not expected_secret or not provided_secret or not hmac.compare_digest(provided_secret, expected_secret):
        return _error_response(401, "unauthorized", "Missing or invalid credentials.")

    try:
        body = await request.json()
    except Exception:
        return _error_response(400, "invalid_request", "Request body must be valid JSON.")
    if not isinstance(body, dict):
        return _error_response(400, "invalid_request", "Request body must be a JSON object.")

    question = body.get("question")
    if not isinstance(question, str) or not question.strip():
        return _error_response(400, "invalid_request", "question is required and must not be empty.")
    question = question.strip()
    if len(question) > MAX_QUESTION_LENGTH:
        return _error_response(400, "invalid_request", f"question must not exceed {MAX_QUESTION_LENGTH} characters.")
    # `history` is accepted but ignored in v1 per the Integration Contract — no validation needed.

    try:
        messages, chunks = _prepare(question)
        raw = ollama_client.complete_chat(messages).choices[0].message.content
        answer = text_guard.clean_answer(raw)
    except Exception:
        traceback.print_exc()
        return _error_response(500, "internal_error", FRIENDLY_ERROR)

    declined = (
        "don't have that information" in answer
        or answer.startswith(text_guard.DEGENERATION_FALLBACK)
    )
    sources = [] if declined else [
        {"title": chunk["source"], "excerpt": _excerpt(chunk["content"]), "url": None}
        for chunk in chunks
    ]

    return JSONResponse(status_code=200, content={"answer": answer, "sources": sources})
