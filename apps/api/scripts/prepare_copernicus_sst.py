"""Convert a small Copernicus ODYSSEA NetCDF subset into a local API artifact.

Run in a separate environment with requirements-copernicus.txt installed.
Existing output is never overwritten. Only use a subset of the documented
dataset/version with sea_surface_temperature in kelvin.
"""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import xarray as xr

DATASET = "IFREMER-GLOB-SST-L3-NRT-OBS_FULL_TIME_SERIE"
VERSION = "202211"


def build_artifact(source: Path):
    with xr.open_dataset(source) as dataset:
        if dataset.attrs.get("id") != "ODYSSEA-IFR-L3S-GLO_010-v3":
            raise ValueError("Unexpected source product ID; verify dataset provenance")
        temperature = dataset["sea_surface_temperature"]
        if temperature.attrs.get("units", "").lower() not in ("kelvin", "k"):
            raise ValueError("Expected SST in kelvin; verify the product and units")
        if set(temperature.dims) != {"time", "latitude", "longitude"}:
            raise ValueError("Unexpected SST dimensions")
        values = []
        for time in dataset.time.values:
            for lat in dataset.latitude.values:
                for lon in dataset.longitude.values:
                    kelvin = float(temperature.sel(time=time, latitude=lat, longitude=lon).item())
                    if math.isfinite(kelvin):
                        values.append({"observed_at": str(time)[:19] + "Z", "latitude": float(lat),
                                       "longitude": float(lon), "temperature_c": round(kelvin - 273.15, 3)})
        if not values:
            raise ValueError("Subset has no valid observations")
    return {"source": "Copernicus Marine Service", "product": "SST_GLO_SST_L3S_NRT_OBSERVATIONS_010_010",
            "dataset": DATASET, "dataset_version": VERSION, "doi": "10.48670/moi-00164",
            "source_url": "https://data.marine.copernicus.eu/product/SST_GLO_SST_L3S_NRT_OBSERVATIONS_010_010/description",
            "source_file": source.name, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "prepared_at": datetime.now(timezone.utc).isoformat(), "source_unit": "kelvin", "unit": "°C",
            "kind": "satellite_observation", "mode": "historical_subset", "values": values,
            "limitations": "Satellite-derived daily gridded observations; missing cells are omitted. Not a live forecast or proof of fishing activity."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    artifact = build_artifact(args.source)
    with args.output.open("x", encoding="utf-8") as target:
        json.dump(artifact, target, ensure_ascii=False, separators=(",", ":"))
    print(f"Prepared {len(artifact['values'])} observations")
