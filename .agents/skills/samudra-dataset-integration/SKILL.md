---
name: samudra-dataset-integration
description: Acquire or integrate a bounded real marine dataset in SamudraSense with verified schema, provenance, access limits and truthful data modes.
---

Start with the assigned task and `docs/DATA_MANIFEST.md`; read only the provider entry and corresponding adapter. A configured credential or catalogue entry does not prove coverage, redistribution rights or point-level access.

1. Use recorded official product/source links. When current API/schema/terms research is needed, use configured Firecrawl for authoritative documentation; do not reinstall it. Record exact dataset/version, rights, access method, valid/availability dates, bounds, units, masks and anticipated size.
2. Use existing local credentials without displaying values. If account/manual access is missing, ask for local setup and record the blocked criterion. Do not search endless alternatives when the user can supply access. Never confuse Fishing Watch with Forest/Nature Watch.
3. Before download, check compressed and extracted estimates and plan storage reserve/budgets. Subset the AOI/time/variables. No full xView3 corpus. Keep raw files ignored; never overwrite existing evidence to rerun a fetch. Current Copernicus fetch has a stricter 10 MB estimate guard and separate requirements environment.
4. Inspect a small real sample: geometry order/CRS, timestamp meaning, identifiers, missing/unknown codes, units and quality flags. Define the mapping to actual source/observation records; reject invalid rows with a recorded reason. Do not invent AIS tracks from event summaries or vessel points from grids.
5. Integrate the mapped records into the assigned API/job/case path with provenance, idempotence and mode separation. Preserve observation vs retrieval time and independent environmental dates. Cache/pause/back off within provider limits; GFW counters can lag 30 minutes and current app limits are process-local.
6. Verify one representative ingestion and relevant missing/duplicate/error condition. For models, use independent time/scene splits and report overlap uncertainty. A descriptive SST layer is not a forecast or accuracy benchmark.
7. Update the one canonical data manifest: local path/structure, actual bytes/checksum, acquisition/preprocessing/integration states, code references, licence/retention/export limits and reproduction. Return limitations in the task result. Synthetic test fixtures must be labelled and never reported as real evaluation data.
