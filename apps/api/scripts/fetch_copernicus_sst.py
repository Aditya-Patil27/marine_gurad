"""Reproduce the small regional SST sample in a separate toolbox environment."""
import os
from pathlib import Path

import copernicusmarine
from prepare_copernicus_sst import DATASET, VERSION, build_artifact
import json

DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "copernicus"
NETCDF = DIRECTORY / "gulf_mannar_sst_20261018_20.nc"
OUTPUT = DIRECTORY / "gulf_mannar_sst_20261018_20.json"
MAX_ESTIMATED_MB = 10


def main():
    username = os.environ.get("COPERNICUS_MARINE_USERNAME")
    password = os.environ.get("COPERNICUS_MARINE_PASSWORD")
    if not username or not password:
        raise SystemExit("Copernicus Marine credentials must be provided in environment variables")
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    if NETCDF.exists() or OUTPUT.exists():
        raise SystemExit("Output already exists; choose a clean data directory before downloading")
    options = dict(dataset_id=DATASET, dataset_version=VERSION, username=username, password=password,
        variables=["sea_surface_temperature"], minimum_longitude=78, maximum_longitude=79,
        minimum_latitude=8, maximum_latitude=9, start_datetime="2026-10-18", end_datetime="2026-10-20",
        output_directory=DIRECTORY, output_filename=NETCDF.name, disable_progress_bar=True)
    estimate = copernicusmarine.subset(**options, dry_run=True)
    if estimate.file_size is None or estimate.data_transfer_size is None:
        raise SystemExit("Provider did not supply both size estimates; download cancelled")
    if max(estimate.file_size, estimate.data_transfer_size) > MAX_ESTIMATED_MB:
        raise SystemExit("Estimated file or transfer exceeds the 10 MB limit; download cancelled")
    copernicusmarine.subset(**options, overwrite=False)
    artifact = build_artifact(NETCDF)
    with OUTPUT.open("x", encoding="utf-8") as target:
        json.dump(artifact, target, ensure_ascii=False, separators=(",", ":"))
    print(f"Prepared {len(artifact['values'])} satellite observations")


if __name__ == "__main__":
    main()
