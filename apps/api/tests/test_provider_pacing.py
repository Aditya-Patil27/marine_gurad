"""Focused tests for shared GFW pacing and its process-local fallback."""
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi import HTTPException
from redis.exceptions import RedisError

from app.api import gfw
from app.services.provider_pacing import GfwPacer

NOW = 1_800_000_000.0


class FakeRedis:
    def __init__(self):
        self.sets = {}
        self.values = {}
        self.fail = False
        self.calls = 0

    def _check(self):
        self.calls += 1
        if self.fail:
            raise RedisError("unavailable")

    def zremrangebyscore(self, key, minimum, maximum):
        self._check()
        current = self.sets.get(key, {})
        self.sets[key] = {member: score for member, score in current.items() if score > maximum}

    def zcard(self, key):
        self._check()
        return len(self.sets.get(key, {}))

    def zadd(self, key, mapping):
        self._check()
        self.sets.setdefault(key, {}).update(mapping)

    def expire(self, key, seconds):
        self._check()
        return True

    def set(self, key, value, ex=None):
        self._check()
        self.values[key] = value

    def get(self, key):
        self._check()
        return self.values.get(key)


def test_shared_window_enforces_limit_and_expires():
    pacer = GfwPacer(client=FakeRedis(), max_requests=2, window_seconds=60, clock=lambda: NOW)
    assert pacer.try_acquire(NOW)
    assert pacer.try_acquire(NOW + 1)
    assert not pacer.try_acquire(NOW + 2)
    assert pacer.recent_count(NOW + 2) == 2
    assert pacer.recent_count(NOW + 61) == 0
    assert pacer.try_acquire(NOW + 61)


def test_cooldown_blocks_new_requests():
    pacer = GfwPacer(client=FakeRedis(), clock=lambda: NOW)
    pacer.block(30, NOW)
    assert round(pacer.blocked_seconds(NOW), 3) == 30.0
    assert not pacer.try_acquire(NOW + 1)
    assert pacer.blocked_seconds(NOW + 31) == 0


def test_redis_error_falls_back_to_local_without_raising():
    fake = FakeRedis()
    fake.fail = True
    pacer = GfwPacer(client=fake, max_requests=1, clock=lambda: NOW)
    assert pacer.blocked_seconds(NOW) == 0
    assert pacer.try_acquire(NOW)
    assert not pacer.try_acquire(NOW + 1)
    status = pacer.status()
    assert status["backend"] == "local"
    assert status["shared"] is False
    assert status["degraded"] is True
    assert "redis://" not in str(status)


def test_redis_failure_suspends_retries_for_existing_client():
    fake = FakeRedis()
    fake.fail = True
    current = {"t": NOW}
    pacer = GfwPacer(client=fake, max_requests=1, clock=lambda: current["t"])
    assert pacer.blocked_seconds(NOW) == 0
    calls_after_failure = fake.calls
    assert calls_after_failure > 0
    # Within the 30-second suspension an existing client is not retried.
    assert pacer.try_acquire(NOW + 5)
    assert pacer.blocked_seconds(NOW + 5) == 0
    assert fake.calls == calls_after_failure
    # After the suspension expires the client is retried and can recover.
    fake.fail = False
    current["t"] = NOW + 31
    assert pacer.blocked_seconds(NOW + 31) == 0
    assert fake.calls > calls_after_failure
    assert pacer.status()["backend"] == "redis"
    assert pacer.status()["degraded"] is False


def test_rate_snapshot_roundtrip():
    pacer = GfwPacer(client=FakeRedis(), clock=lambda: NOW)
    pacer.store_rate({"daily_remaining_requests": 10}, "2026-11-06T12:00:00+00:00")
    snapshot = pacer.rate_snapshot()
    assert snapshot["rate"] == {"daily_remaining_requests": 10}
    assert snapshot["observed_at"] == "2026-11-06T12:00:00+00:00"


def test_gfw_status_reports_pacing_without_secret():
    with patch.object(gfw, "_pacer", GfwPacer(use_redis=False)):
        health = gfw.provider_health()
    assert health["pacing"]["backend"] == "local"
    assert health["pacing"]["shared"] is False
    assert "api_token" not in str(health).lower()


def test_gfw_call_refuses_second_request_when_shared_window_is_full():
    import asyncio

    async def run():
        gfw._cache.clear()
        gfw._recent_requests.clear()
        gfw._last_request_at = 0
        gfw._blocked_until = 0
        gfw._pacer = GfwPacer(use_redis=False, max_requests=1)

        response = Mock(status_code=200, headers=httpx.Headers({}))
        response.json.return_value = {"total": 0, "entries": []}
        client = AsyncMock()
        client.get.return_value = response
        context = AsyncMock()
        context.__aenter__.return_value = client

        with patch.object(gfw.settings, "GFW_API_TOKEN", "test-secret"), \
             patch.object(gfw.httpx, "AsyncClient", return_value=context):
            first = await gfw.search_vessels("7831410")
            assert first["data"]["total"] == 0
            try:
                await gfw.search_vessels("7831411")
            except HTTPException as exc:
                assert exc.status_code == 503
            else:
                raise AssertionError("second request should be paced")

        client.get.assert_awaited_once()

    asyncio.run(run())
