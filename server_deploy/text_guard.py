"""Guard against runaway repetition from small models.

A 1.5B model asked something awkward — an off-topic question, or one in a language
it handles less confidently — sometimes falls into a degeneration loop and emits the
same fragment until it runs out of tokens:

    "Premium sürüm, hizmetlerini tamamen tamamen tamamen tamamen tamamen ..."
    "############################################################ ..."

Sampling penalties reduce this but cannot eliminate it (and pushed too far they cause
loops of their own), so it is caught in code instead: detect the repetition, stop
generating, and either keep the good prefix or admit the answer failed.

Used by both deployments — see the identical copy in the project root.
"""

from __future__ import annotations

import re

# A short unit repeated back-to-back at the end of the text. Non-greedy so the
# smallest repeating unit wins ("#" rather than "####").
_REPEAT_AT_END = re.compile(r"(.{1,60}?)\1{3,}\s*$", re.DOTALL)

# Thresholds: a repeat must be both frequent and long enough to be degeneration
# rather than legitimate structure (blank lines, a row of bullet dashes).
MIN_REPEATS = 4
MIN_SPAN_CHARS = 30
WINDOW_CHARS = 400  # only the tail can be an in-progress loop

DEGENERATION_NOTICE = (
    "\n\n[The local model started repeating itself here, so generation was stopped. "
    "Rephrasing the question usually helps.]"
)
DEGENERATION_FALLBACK = (
    "The local model got stuck repeating itself before it produced a usable answer. "
    "This happens occasionally with a model this small — please try rephrasing the question."
)

# below this, the salvageable prefix isn't worth showing
_MIN_USEFUL_PREFIX = 40


def find_repetition_start(text: str) -> int | None:
    """Index where a runaway repetition begins, or None if the text looks fine."""
    tail = text[-WINDOW_CHARS:]
    offset = len(text) - len(tail)
    match = _REPEAT_AT_END.search(tail)
    if not match:
        return None
    if len(match.group(0)) < MIN_SPAN_CHARS:
        return None
    return offset + match.start()


def clean_answer(text: str) -> str:
    """Trim a degenerated tail, keeping the usable prefix.

    Returns the fallback message when nothing usable survives.
    """
    start = find_repetition_start(text)
    if start is None:
        return text

    prefix = text[:start].rstrip()
    # prefer to end on a sentence boundary rather than mid-word
    boundary = max(prefix.rfind(". "), prefix.rfind(".\n"), prefix.rfind("\n"))
    if boundary > _MIN_USEFUL_PREFIX:
        prefix = prefix[: boundary + 1].rstrip()

    if len(prefix) < _MIN_USEFUL_PREFIX:
        return DEGENERATION_FALLBACK
    return prefix + DEGENERATION_NOTICE


class RepetitionGuard:
    """Streaming counterpart: watches tokens and says when to stop generating.

    Stopping early is not only about output quality — on a CPU-only box it also
    frees the server from generating another 200 tokens of garbage.
    """

    def __init__(self) -> None:
        self._buffer = ""

    def feed(self, chunk: str) -> bool:
        """Add a streamed chunk; return True once degeneration is detected."""
        self._buffer = (self._buffer + chunk)[-WINDOW_CHARS:]
        return find_repetition_start(self._buffer) is not None
