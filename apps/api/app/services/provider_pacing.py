"""Shared Global Fishing Watch pacing with a safe process-local fallback.

The Redis backend lets the backend and worker share one rolling request window
and one 429 cooldown. Redis is an existing local dependency; if it is unavailable
the helper degrades to process-local state rather than blocking provider work or
hanging on a connection attempt. This is a soft operational guard, not a
guarantee of account-wide provider quota compliance.
"""
from __future__ import annotations

import json
import time
from uuid import uuid4

from redis import Redis
from redis.exceptions import RedisError

from app.config import settings


class GfwPacer:
    def __init__(self, client=None, prefix="samudrasense:gfw:pacing", window_seconds=60,
                 max_requests=60, use_redis=True, clock=None):
        self._client = client
        self._prefix = prefix
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self._use_redis = use_redis
        self._clock = clock or time.time
        self._disabled_until = 0.0
        self._backend = "local"
        self._degraded = False
        self._local = []
        self._local_blocked_until = 0.0

    @property
    def window_key(self):
        return f"{self._prefix}:window"

    @property
    def block_key(self):
        return f"{self._prefix}:blocked"

    @property
    def rate_key(self):
        return f"{self._prefix}:rate"

    def _now(self, now=None):
        return self._clock() if now is None else now

    def _client_or_none(self):
        if not self._use_redis:
            return None
        if self._client is not None:
            if self._disabled_until > self._clock():
                return None
            return self._client
        if self._disabled_until > self._clock():
            return None
        try:
            self._client = Redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=0.2,
                socket_timeout=0.2,
                decode_responses=True,
            )
        except (RedisError, OSError, ValueError):
            self._degrade()
            return None
        return self._client

    def _shared_ok(self):
        self._backend = "redis"
        self._degraded = False

    def _degrade(self):
        self._backend = "local"
        self._degraded = True
        self._disabled_until = self._clock() + 30

    def _local_recent(self, now):
        self._local = [stamp for stamp in self._local if now - stamp < self.window_seconds]
        return len(self._local)

    def recent_count(self, now=None):
        now = self._now(now)
        client = self._client_or_none()
        if client is not None:
            try:
                client.zremrangebyscore(self.window_key, 0, now - self.window_seconds)
                count = int(client.zcard(self.window_key))
                self._shared_ok()
                return count
            except (RedisError, OSError, ValueError):
                self._degrade()
        return self._local_recent(now)

    def blocked_seconds(self, now=None):
        now = self._now(now)
        local = max(0.0, self._local_blocked_until - now)
        client = self._client_or_none()
        if client is not None:
            try:
                value = client.get(self.block_key)
                self._shared_ok()
                if value:
                    return max(local, max(0.0, float(value) - now))
                return local
            except (RedisError, OSError, ValueError):
                self._degrade()
        return local

    def try_acquire(self, now=None):
        now = self._now(now)
        if self.blocked_seconds(now) > 0:
            return False
        client = self._client_or_none()
        if client is not None:
            try:
                client.zremrangebyscore(self.window_key, 0, now - self.window_seconds)
                if int(client.zcard(self.window_key)) >= self.max_requests:
                    return False
                client.zadd(self.window_key, {f"{now:.6f}:{uuid4().hex}": now})
                client.expire(self.window_key, max(1, self.window_seconds * 2))
                self._shared_ok()
                return True
            except (RedisError, OSError, ValueError):
                self._degrade()
        if self._local_recent(now) >= self.max_requests:
            return False
        self._local.append(now)
        self._backend = "local"
        return True

    def block(self, seconds, now=None):
        now = self._now(now)
        seconds = max(0.0, float(seconds))
        until = now + seconds
        self._local_blocked_until = max(self._local_blocked_until, until)
        client = self._client_or_none()
        if client is not None:
            try:
                client.set(self.block_key, str(until), ex=max(1, min(int(seconds) + 1, 86400)))
                self._shared_ok()
            except (RedisError, OSError, ValueError):
                self._degrade()

    def store_rate(self, rate, observed_at):
        payload = json.dumps({"rate": dict(rate or {}), "observed_at": observed_at},
                             separators=(",", ":"), ensure_ascii=False)
        client = self._client_or_none()
        if client is not None:
            try:
                client.set(self.rate_key, payload, ex=7200)
                self._shared_ok()
                return
            except (RedisError, OSError, ValueError):
                self._degrade()

    def rate_snapshot(self):
        client = self._client_or_none()
        if client is None:
            return {}
        try:
            raw = client.get(self.rate_key)
            self._shared_ok()
        except (RedisError, OSError, ValueError):
            self._degrade()
            return {}
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def status(self):
        return {
            "backend": self._backend,
            "shared": self._backend == "redis",
            "degraded": self._degraded,
            "redis_configured": bool(self._use_redis),
            "window_seconds": self.window_seconds,
            "max_requests": self.max_requests,
        }

    def reset_local(self):
        self._local.clear()
        self._local_blocked_until = 0.0
