import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path
import sys

import numpy as np
import xarray as xr

from scripts.prepare_copernicus_sst import build_artifact


class CopernicusSubsetTests(unittest.TestCase):
    def test_converts_kelvin_and_omits_missing_observations(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.nc"
            data = xr.Dataset({"sea_surface_temperature": (("time", "latitude", "longitude"),
                np.array([[[300.0, np.nan]]]), {"units": "kelvin"})},
                coords={"time": [np.datetime64("2026-10-18")], "latitude": [8.8],
                        "longitude": [78.8, 78.9]},
                attrs={"id": "ODYSSEA-IFR-L3S-GLO_010-v3"})
            data.to_netcdf(source, engine="h5netcdf")
            result = build_artifact(source)
        self.assertEqual(len(result["values"]), 1)
        self.assertEqual(result["values"][0]["temperature_c"], 26.85)
        self.assertEqual(result["values"][0]["observed_at"], "2026-10-18T00:00:00Z")
        self.assertEqual(result["kind"], "satellite_observation")
        self.assertEqual(len(result["source_sha256"]), 64)

    def test_fetch_refuses_large_estimate_without_downloading(self):
        # The fetcher imports the adjacent converter when run as a script.
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        import fetch_copernicus_sst as fetch
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            with patch.object(fetch, "DIRECTORY", output_dir), patch.object(fetch, "NETCDF", output_dir / "sample.nc"), patch.object(fetch, "OUTPUT", output_dir / "sample.json"), patch.dict("os.environ", {"COPERNICUS_MARINE_USERNAME": "test", "COPERNICUS_MARINE_PASSWORD": "test"}), patch.object(fetch.copernicusmarine, "subset", return_value=SimpleNamespace(file_size=1, data_transfer_size=11)) as subset:
                with self.assertRaises(SystemExit):
                    fetch.main()
                self.assertEqual(subset.call_count, 1)
                self.assertTrue(subset.call_args.kwargs["dry_run"])
