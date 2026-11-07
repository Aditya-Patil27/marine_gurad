import unittest
from datetime import date
import json
import hashlib
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi import HTTPException

from app.api import gfw
from app.services.provider_pacing import GfwPacer


class GFWTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        gfw._cache.clear()
        gfw._rate.clear()
        gfw._rate_checked_monotonic = 0
        gfw._last_request_at = 0
        gfw._blocked_until = 0
        gfw._recent_requests.clear()
        gfw._pacer = GfwPacer(use_redis=False)

    def client_with(self, response):
        client = AsyncMock()
        client.get.return_value = response
        context = AsyncMock()
        context.__aenter__.return_value = client
        return client, context

    async def test_search_caches_and_returns_rate_headers_without_token(self):
        response = Mock(status_code=200, headers=httpx.Headers({
            "x-ratelimit-daily-remaining-requests": "12000"}))
        response.json.return_value = {"total": 1, "entries": [{"id": "example"}]}
        client, context = self.client_with(response)
        with patch.object(gfw.settings, "GFW_API_TOKEN", "test-secret"), patch.object(gfw.httpx, "AsyncClient", return_value=context):
            first = await gfw.search_vessels("7831410")
            second = await gfw.search_vessels("7831410")
            status = await gfw.status()
        self.assertEqual(first["data"]["total"], 1)
        self.assertEqual(second["delivery"], "cached")
        self.assertEqual(status["rate_limits"]["daily_remaining_requests"], 12000)
        self.assertEqual(status["local_requests_last_30_minutes"], 1)
        self.assertEqual(status["pacing"]["backend"], "local")
        self.assertIn("shared", status["pacing"])
        self.assertNotIn("test-secret", str(first) + str(status))
        client.get.assert_awaited_once()

    async def test_rate_limit_does_not_retry(self):
        response = Mock(status_code=429, headers=httpx.Headers({}))
        client, context = self.client_with(response)
        with patch.object(gfw.settings, "GFW_API_TOKEN", "test-secret"), patch.object(gfw.httpx, "AsyncClient", return_value=context):
            with self.assertRaises(HTTPException) as error:
                await gfw.search_vessels("7831410")
        self.assertEqual(error.exception.status_code, 503)
        client.get.assert_awaited_once()

    async def test_local_request_cap_blocks_new_provider_call(self):
        gfw._recent_requests.extend([gfw.monotonic()] * 60)
        with patch.object(gfw.settings, "GFW_API_TOKEN", "test-secret"), patch.object(gfw.httpx, "AsyncClient") as client:
            with self.assertRaises(HTTPException) as error:
                await gfw.search_vessels("7831410")
        self.assertEqual(error.exception.status_code, 503)
        client.assert_not_called()

    async def test_regional_events_share_cache_and_use_exclusive_end(self):
        response = Mock(status_code=201, headers=httpx.Headers({}))
        response.json.return_value = {"total": 1, "entries": [{"type": "fishing"}]}
        client = AsyncMock()
        client.post.return_value = response
        context = AsyncMock()
        context.__aenter__.return_value = client
        with patch.object(gfw.settings, "GFW_API_TOKEN", "test-secret"), patch.object(gfw.httpx, "AsyncClient", return_value=context):
            first = await gfw.regional_events(date(2024, 1, 1), date(2025, 1, 1), 0, 20)
            second = await gfw.regional_events(date(2024, 1, 1), date(2025, 1, 1), 0, 20)
        self.assertEqual(first["requested_end_exclusive"], "2025-01-01")
        self.assertEqual(second["delivery"], "cached")
        self.assertEqual(first["data"]["entries"][0]["type"], "fishing")
        client.post.assert_awaited_once()

    async def test_evidence_exports_selected_event_and_context(self):
        page = {"source": "Global Fishing Watch", "dataset": "sample", "source_url": "https://example.com",
                "retrieved_at": "2026-11-04T00:00:00Z", "requested_region": {},
                "requested_start": "2024-01-01", "requested_end_exclusive": "2025-01-01",
                "limitations": "inferred", "data": {"entries": [{"id": "event-1"}]}}
        with patch.object(gfw, "regional_events", AsyncMock(return_value=page)), patch.object(gfw, "load_satellite_observations", return_value={"values": []}):
            response = await gfw.export_event_evidence("event-1", date(2024, 1, 1), date(2025, 1, 1), 0, 20, True)
        data = json.loads(response.body)
        self.assertEqual(data["snapshot"]["event"]["id"], "event-1")
        self.assertIn("not necessarily concurrent", data["snapshot"]["regional_ocean_context"]["association"])
        canonical = json.dumps(data["snapshot"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.assertEqual(data["sha256"], hashlib.sha256(canonical).hexdigest())

    async def test_geojson_preserves_event_times_and_omits_invalid_positions(self):
        page = {"source": "Global Fishing Watch", "dataset": "sample", "source_url": "https://example.com",
                "retrieved_at": "2026-11-04T00:00:00Z", "delivery": "cached", "requested_start": "2024-01-01",
                "requested_end_exclusive": "2024-02-01", "data": {"total": 2, "entries": [
                    {"id": "e1", "start": "2024-01-03T00:00:00Z", "position": {"lat": 8, "lon": 78}, "vessel": {"ssvid": "123456789"}},
                    {"id": "e2", "position": {"lat": 999, "lon": 78}},
                ]}}
        with patch.object(gfw, "regional_events", AsyncMock(return_value=page)):
            result = await gfw.regional_events_geojson(date(2024, 1, 1), date(2024, 2, 1), 0, 20)
        self.assertEqual(result["features"][0]["geometry"]["coordinates"], [78.0, 8.0])
        self.assertEqual(result["features"][0]["properties"]["start"], "2024-01-03T00:00:00Z")
        self.assertEqual(result["omitted_invalid_positions"], 1)
        self.assertEqual(result["mode"], "historical")
