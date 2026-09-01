"""Resolve the real client IP behind the reverse proxy.

uvicorn binds 127.0.0.1 and nginx proxies to it, so `request.client.host` is the
proxy for *every* visitor — keying per-visitor rate limits on it would turn them
into a single shared bucket. nginx must therefore forward the caller with

    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

Only the left-most entry is trusted, and only because nothing but the local proxy
can reach the port (config.TRUST_FORWARDED_FOR). If the app is ever exposed
directly, flip that flag off: the header is client-controlled and trivially spoofed.
"""

from fastapi import Request

import config

UNKNOWN_IP = "unknown"


def get_client_ip(request: Request) -> str:
    if config.TRUST_FORWARDED_FOR:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # "client, proxy1, proxy2" — the original client is first
            client = forwarded.split(",")[0].strip()
            if client:
                return client
        real_ip = request.headers.get("X-Real-IP")
        if real_ip and real_ip.strip():
            return real_ip.strip()
    return request.client.host if request.client else UNKNOWN_IP
