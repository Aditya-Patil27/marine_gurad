"""Transparent, availability-aware hotspot baselines and rolling evaluation.

The module deliberately contains no trained model.  It evaluates three simple
rankings against later activity while ensuring that every input feature was
available at the prediction time.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1.0"
VALID_MODES = {"historical", "live", "recorded", "replay", "synthetic"}
REAL_EVALUATION_MODES = {"historical", "live", "recorded"}


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp must include a UTC offset: {value}")
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return sha256(encoded).hexdigest()


def report_sha256(report: dict[str, Any]) -> str:
    """Hash report content while excluding the checksum field itself."""
    content = dict(report)
    content.pop("evaluation_sha256", None)
    return _canonical_sha256(content)


def load_activity_dataset(path: str | Path) -> dict[str, Any]:
    """Load and validate the bounded activity-evaluation interchange format."""
    with Path(path).open(encoding="utf-8") as source:
        data = json.load(source)
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"activity dataset schema_version must be {SCHEMA_VERSION}")
    metadata = data.get("dataset")
    if not isinstance(metadata, dict):
        raise ValueError("dataset metadata is required")
    required = ("name", "source", "mode", "permissions", "grid_resolution_degrees")
    missing = [field for field in required if metadata.get(field) in (None, "")]
    if missing:
        raise ValueError(f"dataset metadata missing: {', '.join(missing)}")
    if metadata["mode"] not in VALID_MODES:
        raise ValueError(f"unsupported dataset mode: {metadata['mode']}")
    resolution = metadata["grid_resolution_degrees"]
    if not isinstance(resolution, (int, float)) or not 0 < resolution <= 10:
        raise ValueError("grid_resolution_degrees must be in (0, 10]")

    cells = data.get("cells")
    if not isinstance(cells, list) or not cells:
        raise ValueError("cells must be a non-empty list")
    cell_ids = []
    for cell in cells:
        if not isinstance(cell, dict) or not isinstance(cell.get("cell_id"), str):
            raise ValueError("every cell requires a string cell_id")
        cell_ids.append(cell["cell_id"])
    if len(cell_ids) != len(set(cell_ids)):
        raise ValueError("cell_id values must be unique")

    records = data.get("records")
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    known = set(cell_ids)
    for index, record in enumerate(records):
        if not isinstance(record, dict) or record.get("cell_id") not in known:
            raise ValueError(f"record {index} references an unknown cell")
        observed = _utc(record.get("observed_at", ""))
        available = _utc(record.get("available_at", ""))
        if available < observed:
            raise ValueError(f"record {index} is available before it was observed")
        quality = record.get("quality", "valid")
        if quality not in {"valid", "missing", "cloud", "invalid"}:
            raise ValueError(f"record {index} has unsupported quality: {quality}")
        effort = record.get("effort_hours")
        if quality == "valid":
            if not isinstance(effort, (int, float)) or not math.isfinite(effort) or effort < 0:
                raise ValueError(f"record {index} valid effort_hours must be finite and non-negative")
        elif effort is not None:
            raise ValueError(f"record {index} masked effort_hours must be null")
    return data


def _valid_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [record for record in records if record.get("quality", "valid") == "valid"]


def _scores(
    cells: list[str], history: list[dict[str, Any]], prediction_at: datetime, lookback_days: int
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, Any]]]:
    recent_start = prediction_at - timedelta(days=lookback_days)
    by_cell: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in history:
        by_cell[record["cell_id"]].append(record)

    scores = {"persistence": {}, "recent_effort": {}, "uniform": {}}
    factors: dict[str, dict[str, Any]] = {}
    for cell_id in cells:
        rows = sorted(by_cell[cell_id], key=lambda row: (_utc(row["observed_at"]), _utc(row["available_at"])))
        latest = rows[-1] if rows else None
        recent = [row for row in rows if _utc(row["observed_at"]) >= recent_start]
        latest_effort = float(latest["effort_hours"]) if latest else 0.0
        recent_effort = sum(float(row["effort_hours"]) for row in recent)
        scores["persistence"][cell_id] = latest_effort
        scores["recent_effort"][cell_id] = recent_effort
        scores["uniform"][cell_id] = 1.0
        factors[cell_id] = {
            "latest_effort_hours": latest_effort,
            "latest_observed_at": latest["observed_at"] if latest else None,
            "recent_effort_hours": recent_effort,
            "recent_observation_count": len(recent),
            "lookback_days": lookback_days,
        }
    return scores, factors


def _stable_order(cells: Iterable[str], target_start: datetime) -> list[str]:
    day = target_start.date().isoformat()
    return sorted(cells, key=lambda cell: (sha256(f"{day}:{cell}".encode()).hexdigest(), cell))


def plan_scan(
    scores: dict[str, float],
    budget: int,
    target_start: datetime,
    *,
    reserve_fraction: float = 0.20,
    uniform: bool = False,
) -> list[dict[str, Any]]:
    """Select exactly ``budget`` cells, reserving coverage outside the top budget."""
    if not 0 < budget < len(scores):
        raise ValueError("scan budget must be positive and smaller than the candidate cell count")
    if not 0 <= reserve_fraction < 1:
        raise ValueError("reserve_fraction must be in [0, 1)")
    if uniform:
        return [
            {"cell_id": cell, "score": scores[cell], "coverage_slot": "uniform"}
            for cell in _stable_order(scores, target_start)[:budget]
        ]

    ranked = sorted(scores, key=lambda cell: (-scores[cell], cell))
    reserve = max(1, math.ceil(budget * reserve_fraction))
    hotspot_count = budget - reserve
    non_hotspot_pool = ranked[budget:]
    if len(non_hotspot_pool) < reserve:
        raise ValueError("not enough cells outside the top-budget hotspot set for reserved coverage")
    selected = [
        {"cell_id": cell, "score": scores[cell], "coverage_slot": "hotspot"}
        for cell in ranked[:hotspot_count]
    ]
    selected.extend(
        {"cell_id": cell, "score": scores[cell], "coverage_slot": "non_hotspot"}
        for cell in _stable_order(non_hotspot_pool, target_start)[:reserve]
    )
    return selected


def evaluate_activity(
    data: dict[str, Any],
    *,
    scan_budget: int,
    lookback_days: int = 7,
    min_history_days: int = 7,
    min_evaluation_folds: int = 3,
) -> dict[str, Any]:
    """Run expanding-window daily folds without using future-observed inputs."""
    if lookback_days < 1 or min_history_days < 1 or min_evaluation_folds < 1:
        raise ValueError("lookback/history/fold requirements must be positive")
    metadata = data["dataset"]
    cells = [cell["cell_id"] for cell in data["cells"]]
    if not 0 < scan_budget < len(cells):
        raise ValueError("scan_budget must be positive and smaller than the candidate cell count")

    valid = _valid_records(data["records"])
    days = sorted({_utc(record["observed_at"]).date() for record in valid})
    folds = []
    for day_index in range(min_history_days, len(days)):
        target_start = datetime.combine(days[day_index], datetime.min.time(), timezone.utc)
        target_end = target_start + timedelta(days=1)
        history = [
            record
            for record in valid
            if _utc(record["observed_at"]) < target_start and _utc(record["available_at"]) <= target_start
        ]
        target = [record for record in valid if target_start <= _utc(record["observed_at"]) < target_end]
        if not history or not target:
            continue
        scores, factors = _scores(cells, history, target_start, lookback_days)
        truth = defaultdict(float)
        for record in target:
            truth[record["cell_id"]] += float(record["effort_hours"])
        total_effort = sum(truth.values())
        active_cells = {cell for cell, effort in truth.items() if effort > 0}
        fold_results = {}
        for baseline, cell_scores in scores.items():
            selected = plan_scan(
                cell_scores,
                scan_budget,
                target_start,
                uniform=baseline == "uniform",
            )
            selected_ids = {item["cell_id"] for item in selected}
            captured = sum(truth[cell] for cell in selected_ids)
            fold_results[baseline] = {
                "captured_effort_hours": captured,
                "total_effort_hours": total_effort,
                "capture_rate": captured / total_effort if total_effort else None,
                "active_cells_detected": len(active_cells & selected_ids),
                "active_cells_missed": len(active_cells - selected_ids),
                "selected_cell_count": len(selected),
                "non_hotspot_reserved_count": sum(
                    item["coverage_slot"] == "non_hotspot" for item in selected
                ),
                "non_hotspot_reserved_fraction": sum(
                    item["coverage_slot"] == "non_hotspot" for item in selected
                ) / len(selected),
                "selection": [
                    {**item, "factors": factors[item["cell_id"]]}
                    for item in selected
                ],
            }
        folds.append(
            {
                "target_start": _iso(target_start),
                "prediction_at": _iso(target_start),
                "history_record_count": len(history),
                "target_record_count": len(target),
                "leakage_audit": {
                    "latest_history_observed_at": _iso(max(_utc(record["observed_at"]) for record in history)),
                    "latest_history_available_at": _iso(max(_utc(record["available_at"]) for record in history)),
                    "passed": all(
                        _utc(record["observed_at"]) < target_start
                        and _utc(record["available_at"]) <= target_start
                        for record in history
                    ),
                },
                "baselines": fold_results,
            }
        )

    aggregate = {}
    for baseline in ("persistence", "recent_effort", "uniform"):
        results = [fold["baselines"][baseline] for fold in folds]
        captured = sum(item["captured_effort_hours"] for item in results)
        total = sum(item["total_effort_hours"] for item in results)
        aggregate[baseline] = {
            "fold_count": len(results),
            "captured_effort_hours": captured,
            "total_effort_hours": total,
            "capture_rate": captured / total if total else None,
            "active_cells_detected": sum(item["active_cells_detected"] for item in results),
            "active_cells_missed": sum(item["active_cells_missed"] for item in results),
        }

    blockers = []
    if metadata["mode"] not in REAL_EVALUATION_MODES:
        blockers.append("evaluation input is not a permitted historical/live/recorded dataset")
    if str(metadata.get("permissions", "")).strip().lower() in {"", "unknown", "unverified"}:
        blockers.append("source permissions are not verified")
    if len(folds) < min_evaluation_folds:
        blockers.append(
            f"only {len(folds)} evaluable folds; at least {min_evaluation_folds} are required"
        )
    if folds and not any(
        fold["baselines"]["uniform"]["total_effort_hours"] > 0 for fold in folds
    ):
        blockers.append("evaluation folds contain no positive target effort")
    if any(not fold["leakage_audit"]["passed"] for fold in folds):
        blockers.append("availability/observation leakage audit failed")

    report = {
        "schema_version": SCHEMA_VERSION,
        "kind": "activity_hotspot_baseline_evaluation",
        "claim_scope": "Fishing-effort ranking only; not illegal-activity prediction or satellite tasking.",
        "dataset": metadata,
        "configuration": {
            "scan_budget_cells": scan_budget,
            "non_hotspot_reserve_fraction": 0.20,
            "recent_effort_lookback_days": lookback_days,
            "minimum_history_days": min_history_days,
            "minimum_evaluation_folds": min_evaluation_folds,
        },
        "gate": {
            "status": "blocked" if blockers else "evaluable",
            "blockers": blockers,
        },
        "metrics": aggregate,
        "folds": folds,
        "latest_recommendations": folds[-1] if folds else None,
    }
    report["evaluation_sha256"] = report_sha256(report)
    return report


def evaluate_sst_persistence(data: dict[str, Any], *, min_pairs: int = 7) -> dict[str, Any]:
    """Evaluate cell-level next-observation persistence when availability permits."""
    if min_pairs < 1:
        raise ValueError("min_pairs must be positive")
    values = data.get("values", [])
    valid = [
        item for item in values
        if item.get("quality", "valid") == "valid"
        and isinstance(item.get("temperature_c"), (int, float))
        and math.isfinite(item["temperature_c"])
    ]
    days = sorted({item["observed_at"][:10] for item in valid})
    cells = {(round(item["latitude"], 6), round(item["longitude"], 6)) for item in valid}
    blockers = []
    if data.get("mode") not in REAL_EVALUATION_MODES:
        blockers.append("condition input is not a permitted historical/live/recorded dataset")
    availability_missing = any("available_at" not in item for item in valid)
    if availability_missing:
        blockers.append("per-observation availability times are absent")
    pairs = []
    if not availability_missing:
        by_cell: dict[tuple[float, float], list[dict[str, Any]]] = defaultdict(list)
        for item in valid:
            observed = _utc(item["observed_at"])
            available = _utc(item["available_at"])
            if available < observed:
                raise ValueError("SST value is available before it was observed")
            by_cell[(round(item["latitude"], 6), round(item["longitude"], 6))].append(item)
        for cell, rows in by_cell.items():
            ordered = sorted(rows, key=lambda item: _utc(item["observed_at"]))
            for target in ordered[1:]:
                prediction_at = _utc(target["observed_at"])
                candidates = [
                    item for item in ordered
                    if _utc(item["observed_at"]) < prediction_at
                    and _utc(item["available_at"]) <= prediction_at
                ]
                if not candidates:
                    continue
                source = max(candidates, key=lambda item: _utc(item["observed_at"]))
                predicted = float(source["temperature_c"])
                observed = float(target["temperature_c"])
                pairs.append({
                    "cell": {"latitude": cell[0], "longitude": cell[1]},
                    "prediction_at": _iso(prediction_at),
                    "source_observed_at": _iso(_utc(source["observed_at"])),
                    "source_available_at": _iso(_utc(source["available_at"])),
                    "predicted_temperature_c": predicted,
                    "observed_temperature_c": observed,
                    "absolute_error_c": abs(predicted - observed),
                })
    if len(pairs) < min_pairs:
        blockers.append(f"only {len(pairs)} availability-aware pairs; at least {min_pairs} are required")
    return {
        "kind": "sst_persistence_evaluation",
        "status": "blocked" if blockers else "evaluable",
        "blockers": blockers,
        "source": data.get("source"),
        "product": data.get("product"),
        "dataset": data.get("dataset"),
        "mode": data.get("mode"),
        "unit": data.get("unit"),
        "observation_count": len(valid),
        "observation_days": days,
        "observed_cell_count": len(cells),
        "pair_count": len(pairs),
        "mae_c": sum(pair["absolute_error_c"] for pair in pairs) / len(pairs) if pairs else None,
        "leakage_audit_passed": all(
            _utc(pair["source_observed_at"]) < _utc(pair["prediction_at"])
            and _utc(pair["source_available_at"]) <= _utc(pair["prediction_at"])
            for pair in pairs
        ),
        "pairs": pairs,
        "limitations": data.get("limitations"),
    }


def artifact_manifest(
    activity_path: str | Path,
    report: dict[str, Any],
    *,
    sst_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return stable checksums for the exact inputs, configuration and report."""
    activity = Path(activity_path)
    artifacts = [{
        "role": "activity_input",
        "path": activity.as_posix(),
        "sha256": sha256(activity.read_bytes()).hexdigest(),
    }]
    if sst_path is not None:
        sst = Path(sst_path)
        artifacts.append({
            "role": "sst_input",
            "path": sst.as_posix(),
            "sha256": sha256(sst.read_bytes()).hexdigest(),
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "evaluator": "ml.hotspot_baselines",
        "evaluator_version": SCHEMA_VERSION,
        "artifacts": artifacts,
        "configuration_sha256": _canonical_sha256(report["configuration"]),
        "evaluation_sha256": report_sha256(report),
    }
