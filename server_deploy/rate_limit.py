"""Sliding-window rate limiting for the public demo endpoints.

The live demo runs a 1.5B model on CPU on a small VPS: a single answer costs
several seconds to tens of seconds of CPU. Without limits, one impatient visitor
(or a bot) can saturate the box and make the demo unusable for everyone else.

Two scopes are enforced at once:

* ``ip``     — per visitor, so no single person can monopolise the server.
* ``global`` — across all visitors, so the box as a whole stays responsive.

A request must pass *every* rule of *both* scopes; the request is only recorded
once all of them pass (all-or-nothing), so a rejected request never eats quota.

No Redis, no slowapi: the demo runs as a single uvicorn process, so plain
process-local state is exact and costs nothing. Limits are defined in config.py.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

GLOBAL_KEY = "__global__"

# how often expired counters for long-gone visitors are swept out of memory
_CLEANUP_INTERVAL_SECONDS = 300.0


@dataclass(frozen=True)
class Rule:
    """One limit: `limit` requests per `window_seconds`, within `scope`."""

    limit: int
    window_seconds: float
    scope: str  # "ip" | "global"
    label: str  # "second" | "minute" | "day" — used in user-facing messages


@dataclass(frozen=True)
class Rejection:
    rule: Rule
    retry_after_seconds: int  # rounded up, always >= 1


@dataclass
class Decision:
    """Outcome of a limit check. `remaining` is per-IP quota left afterwards."""

    rejection: Rejection | None = None
    remaining: dict[str, int] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.rejection is None


class RateLimiter:
    """Thread-safe sliding-window counter over a fixed set of rules."""

    def __init__(self, rules: list[Rule], clock=time.monotonic) -> None:
        if not rules:
            raise ValueError("RateLimiter needs at least one rule")
        self._rules = tuple(rules)
        self._clock = clock
        self._lock = threading.Lock()
        # (rule index, bucket key) -> timestamps of accepted requests in-window
        self._hits: dict[tuple[int, str], deque[float]] = defaultdict(deque)
        self._last_cleanup = clock()

    # -- public API ---------------------------------------------------------

    @property
    def rules(self) -> tuple[Rule, ...]:
        return self._rules

    def check(self, client_key: str) -> Decision:
        """Consume one slot for `client_key`, or explain why it was refused.

        FastAPI serves sync endpoints on a threadpool, so this runs under a lock.
        The work is a handful of deque operations — microseconds.
        """
        now = self._clock()
        with self._lock:
            self._maybe_cleanup(now)

            logs: list[deque[float]] = []
            for index, rule in enumerate(self._rules):
                log = self._window(index, rule, client_key, now)
                if len(log) >= rule.limit:
                    # oldest hit in the window decides when a slot frees up
                    retry_after = rule.window_seconds - (now - log[0])
                    return Decision(
                        rejection=Rejection(rule, max(1, _ceil(retry_after))),
                        remaining=self._remaining(client_key, now),
                    )
                logs.append(log)

            for log in logs:
                log.append(now)
            return Decision(remaining=self._remaining(client_key, now))

    def peek_remaining(self, client_key: str) -> dict[str, int]:
        """Per-IP quota left, without consuming anything."""
        now = self._clock()
        with self._lock:
            return self._remaining(client_key, now)

    # -- internals ----------------------------------------------------------

    def _window(self, index: int, rule: Rule, client_key: str, now: float) -> deque[float]:
        key = (index, GLOBAL_KEY if rule.scope == "global" else client_key)
        log = self._hits[key]
        while log and now - log[0] >= rule.window_seconds:
            log.popleft()
        return log

    def _remaining(self, client_key: str, now: float) -> dict[str, int]:
        remaining: dict[str, int] = {}
        for index, rule in enumerate(self._rules):
            if rule.scope != "ip":
                continue
            log = self._window(index, rule, client_key, now)
            remaining[rule.label] = max(0, rule.limit - len(log))
        return remaining

    def _maybe_cleanup(self, now: float) -> None:
        """Drop counters that have fully expired, so memory stays bounded."""
        if now - self._last_cleanup < _CLEANUP_INTERVAL_SECONDS:
            return
        self._last_cleanup = now
        for key in list(self._hits):
            rule = self._rules[key[0]]
            log = self._hits[key]
            while log and now - log[0] >= rule.window_seconds:
                log.popleft()
            if not log:
                del self._hits[key]


def _ceil(seconds: float) -> int:
    return int(seconds) + (1 if seconds > int(seconds) else 0)


# -- user-facing messages ---------------------------------------------------

_WINDOW_NOUN = {"second": "second", "minute": "minute", "day": "day"}


def format_duration(seconds: int) -> str:
    """Human-friendly wait time: '4 seconds', '2 minutes', '3h 12m'."""
    if seconds < 60:
        return f"{seconds} second{'s' if seconds != 1 else ''}"
    if seconds < 3600:
        minutes = _ceil(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    hours, minutes = divmod(seconds // 60, 60)
    return f"{hours}h {minutes:02d}m"


def describe(rejection: Rejection) -> tuple[str, str]:
    """Return (error code, message shown to the visitor)."""
    rule = rejection.rule
    wait = format_duration(rejection.retry_after_seconds)
    noun = _WINDOW_NOUN.get(rule.label, rule.label)

    if rule.scope == "ip":
        code = f"rate_limited_user_{rule.label}"
        if rule.label == "second":
            message = (
                "You're asking a bit too fast. This demo answers one question at a "
                f"time — please wait {wait} and send it again."
            )
        elif rule.label == "day":
            message = (
                f"You've used your {rule.limit} questions for today. This is a free "
                "demo on a small server, so the daily quota is deliberately tight — "
                f"it resets in {wait}."
            )
        else:
            message = (
                f"You've hit the limit of {rule.limit} questions per {noun}. "
                f"Please wait {wait} and try again."
            )
        return code, message

    code = f"rate_limited_global_{rule.label}"
    if rule.label == "day":
        message = (
            f"The demo has reached its shared daily budget of {rule.limit} questions "
            f"across all visitors. It resets in {wait}. The full project still runs "
            "locally — see the GitHub repository."
        )
    else:
        message = (
            "The demo is busy right now — too many people are asking at once and the "
            f"server answers one question at a time. Please try again in {wait}."
        )
    return code, message
