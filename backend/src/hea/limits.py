"""Abuse and spend protection for model-backed endpoints on a public URL.

Serverless instances share no memory, so limits live in Redis (Upstash REST API, which Vercel's Redis
integration provisions; env KV_REST_API_URL/KV_REST_API_TOKEN or UPSTASH_REDIS_REST_URL/UPSTASH_REDIS_REST_TOKEN):

  * per-client: HEA_RATE_PER_HOUR model requests per IP per hour (default 10)
  * global: HEA_DAILY_USD_CAP dollars per UTC day (default 1.00), admitted against the worst case before a
    call and settled to measured cost after

Fails closed: on Vercel without Redis, model endpoints are disabled even if a model key is present. Locally an
in-process store is used.
"""

from __future__ import annotations

import os
import threading
import time
from datetime import UTC, datetime

import httpx


class LimitExceeded(RuntimeError):
    pass


class MemoryStore:
    def __init__(self):
        self.data: dict[str, float] = {}
        self.lock = threading.Lock()

    def incr(self, key: str, by: float, ttl: int) -> float:
        with self.lock:
            self.data[key] = self.data.get(key, 0.0) + by
            return self.data[key]


class UpstashStore:
    def __init__(self, url: str, token: str):
        self.url, self.headers = url.rstrip("/"), {"Authorization": f"Bearer {token}"}

    def incr(self, key: str, by: float, ttl: int) -> float:
        r = httpx.post(
            f"{self.url}/pipeline",
            headers=self.headers,
            timeout=5,
            json=[["INCRBYFLOAT", key, str(by)], ["EXPIRE", key, str(ttl), "NX"]],
        )
        r.raise_for_status()
        return float(r.json()[0]["result"])


def store_from_env():
    url = os.getenv("KV_REST_API_URL") or os.getenv("UPSTASH_REDIS_REST_URL")
    token = os.getenv("KV_REST_API_TOKEN") or os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if url and token:
        return UpstashStore(url, token)
    return None if os.getenv("VERCEL") else MemoryStore()


class Limiter:
    def __init__(self, store, per_hour: int, daily_usd: float):
        self.store, self.per_hour, self.daily_usd = store, per_hour, daily_usd

    @classmethod
    def from_env(cls) -> Limiter:
        return cls(
            store_from_env(),
            int(os.getenv("HEA_RATE_PER_HOUR", "10")),
            float(os.getenv("HEA_DAILY_USD_CAP", "1.00")),
        )

    @property
    def enabled(self) -> bool:
        return self.store is not None

    def admit(self, client: str, worst_case_usd: float) -> str:
        """Count the request and reserve its worst-case cost. Returns the day key used for settlement."""
        if self.store is None:
            raise LimitExceeded("model endpoints are disabled: no durable rate limiter is configured")
        hour = int(time.time() // 3600)
        if self.store.incr(f"rl:{client}:{hour}", 1, 3600) > self.per_hour:
            raise LimitExceeded(f"rate limit: {self.per_hour} model requests per hour")
        day = datetime.now(UTC).strftime("%Y-%m-%d")
        if self.store.incr(f"usd:{day}", worst_case_usd, 172800) > self.daily_usd:
            self.store.incr(f"usd:{day}", -worst_case_usd, 172800)
            raise LimitExceeded(f"daily demo budget of ${self.daily_usd:.2f} reached; try again tomorrow")
        return day

    def settle(self, day: str, reserved_usd: float, actual_usd: float) -> None:
        self.store.incr(f"usd:{day}", actual_usd - reserved_usd, 172800)


def client_id(headers) -> str:
    fwd = headers.get("x-vercel-forwarded-for") or headers.get("x-forwarded-for") or headers.get("x-real-ip") or ""
    return fwd.split(",")[0].strip() or "local"
