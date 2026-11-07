"""Contract checks for the marine-data adapter without contacting the provider."""
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.api import ocean


class OceanAdapterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        ocean._cache.clear()

    async def test_attribution_grid_cell_and_cache(self):
        response = unittest.mock.Mock()
        response.json.return_value = {
            "latitude": 8.79, "longitude": 78.88,
            "hourly_units": {"sea_surface_temperature": "°C"},
            "hourly": {"time": ["2020-01-01T00:00", "2999-01-01T00:00"],
                       "sea_surface_temperature": [28.0, 29.0]},
        }
        client = AsyncMock()
        client.get.return_value = response
        context = AsyncMock()
        context.__aenter__.return_value = client
        with patch.object(ocean.httpx, "AsyncClient", return_value=context):
            first = await ocean.sea_surface_temperature(8.8, 78.9)
            second = await ocean.sea_surface_temperature(8.8, 78.9)
        self.assertEqual(first["kind"], "modelled_marine_data")
        self.assertEqual(first["grid_location"]["latitude"], 8.79)
        self.assertEqual(len(first["values"]), 1)
        self.assertEqual(second["delivery"], "cached")
        client.get.assert_awaited_once()

    async def test_missing_data_is_unavailable(self):
        response = unittest.mock.Mock()
        response.json.return_value = {"hourly": {}}
        client = AsyncMock()
        client.get.return_value = response
        context = AsyncMock()
        context.__aenter__.return_value = client
        with patch.object(ocean.httpx, "AsyncClient", return_value=context):
            with self.assertRaises(HTTPException) as error:
                await ocean.sea_surface_temperature(8.8, 78.9)
        self.assertEqual(error.exception.status_code, 503)
