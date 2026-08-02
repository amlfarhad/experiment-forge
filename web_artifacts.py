"""Build deterministic, browser-friendly payloads from the Experiment Forge pipeline."""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
import yaml

from analysis.experiment_readout import analyze_experiment
from data_generation.synthetic_product import generate_demo_data
from quality.checks import run_quality_audit
from warehouse.build import build_warehouse


SCHEMA_VERSION = "1.0"
REPO_ROOT = Path(__file__).resolve().parent

SAMPLE_DEFINITIONS = (
    {
        "experiment_name": "checkout_progress_indicator",
        "title": "Checkout progress indicator",
        "profile": "flawed",
        "seed": 42,
        "treatment_lift": None,
        "takeaway": "A positive-looking lift is not decision-ready while assignment and event data fail quality gates.",
    },
    {
        "experiment_name": "search_autocomplete_refresh",
        "title": "Search autocomplete refresh",
        "profile": "clean",
        "seed": 84,
        "treatment_lift": 0.025,
        "takeaway": "The treatment clears the practical and adjusted statistical thresholds with no critical quality failures.",
    },
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return round(value, 10)
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True) + "\n")


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_manifest(raw_dir: Path) -> dict[str, Any]:
    files: dict[str, Any] = {}
    for path in sorted(raw_dir.glob("*.csv")):
        rows = max(sum(1 for _ in path.open()) - 1, 0)
        files[path.name] = {"rows": rows, "sha256": _hash_file(path)}
    return files


def _read_metrics() -> dict[str, Any]:
    payload = yaml.safe_load((REPO_ROOT / "config" / "metrics.yml").read_text()) or {}
    return dict(payload.get("metrics", {}))


def _read_experiment_policy(experiment_name: str) -> dict[str, Any]:
    payload = yaml.safe_load((REPO_ROOT / "config" / "experiments.yml").read_text()) or {}
    return dict(payload.get("experiments", {}).get(experiment_name, {}))


def _lineage() -> list[dict[str, Any]]:
    return [
        {
            "stage": "source",
            "artifact": "data/sample/*.csv",
            "description": "Deterministic synthetic product sources generated with an explicit seed.",
        },
        {
            "stage": "warehouse",
            "artifact": "data/warehouse/experiment_forge.duckdb",
            "description": "DuckDB raw, staging, intermediate, and mart models built from the CSV contract.",
        },
        {
            "stage": "quality",
            "artifact": "quality.checks.run_quality_audit",
            "description": "Assignment, temporal, source, metric, mart, and guardrail checks.",
        },
        {
            "stage": "analysis",
            "artifact": "analysis.experiment_readout.analyze_experiment",
            "description": "Primary two-proportion test, secondary continuous test, practical threshold, and decision mapping.",
        },
        {
            "stage": "browser",
            "artifact": "web/data/experiments/*.json",
            "description": "Stable JSON payload consumed by the credential-free Decision Desk.",
        },
    ]


def _methodology(metrics: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    primary = metrics.get("conversion_rate", {})
    return {
        "primary_metric": {
            "name": "conversion_rate",
            "label": "Purchase conversion",
            "grain": primary.get("grain", "assigned_user"),
            "numerator": primary.get("numerator", "users with at least one post-assignment purchase event"),
            "denominator": primary.get("denominator", "canonically assigned users"),
        },
        "uncertainty": "95% normal-approximation confidence interval for the treatment minus control conversion-rate difference.",
        "multiple_testing": {
            "method": analysis.get("multiple_testing_method", "Holm-Bonferroni"),
            "family": "The pre-specified primary conversion metric and revenue-per-user secondary metric.",
            "segments": "Segment cuts are exploratory and are not used to upgrade the launch decision.",
        },
        "practical_significance": {
            "threshold": analysis.get("practical_threshold", 0.01),
            "explanation": "A statistically supported result must also clear the minimum relative lift threshold before launch or stop.",
        },
    }


def _build_one(
    build_root: Path,
    definition: dict[str, Any],
    n_users: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_dir = build_root / definition["experiment_name"] / "data" / "sample"
    db_path = build_root / definition["experiment_name"] / "data" / "warehouse" / "experiment_forge.duckdb"
    manifest = generate_demo_data(
        raw_dir,
        seed=int(definition["seed"]),
        n_users=n_users,
        experiment_name=definition["experiment_name"],
        quality_profile=definition["profile"],
        treatment_lift=definition["treatment_lift"],
    )
    build_warehouse(raw_dir, db_path)
    audit = run_quality_audit(raw_dir, db_path)
    analysis = analyze_experiment(db_path, audit)
    analysis_payload = analysis.to_dict()
    quality_payload = audit.to_dict()
    policy = _read_experiment_policy(definition["experiment_name"])
    metrics = _read_metrics()

    with duckdb.connect(str(db_path), read_only=True) as con:
        guardrails = con.execute(
            "select * from mart_metric_guardrails order by variant"
        ).fetchdf().to_dict("records")
        segments = con.execute(
            "select * from mart_segment_readout order by segment, variant"
        ).fetchdf().to_dict("records")
        daily = con.execute(
            """
            select
                cast(snapshot_date as varchar) as snapshot_date,
                variant,
                sum(users) as users,
                sum(cumulative_sessions) as cumulative_sessions,
                sum(cumulative_events) as cumulative_events,
                sum(cumulative_revenue) as cumulative_revenue
            from int_daily_experiment_metrics
            group by 1, 2
            order by 1, 2
            """
        ).fetchdf().to_dict("records")
        health = con.execute("select * from mart_experiment_health").fetchdf().to_dict("records")

    summary = {
        **(health[0] if health else {}),
        "quality_status": audit.summary.status,
        "decision": analysis.decision,
        "relative_lift": analysis.relative_lift,
        "adjusted_p_value": analysis.adjusted_p_value,
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "experiment": {
            "id": definition["experiment_name"],
            "title": definition["title"],
            "owner": policy.get("owner", "product_analytics"),
            "hypothesis": policy.get("hypothesis", "Synthetic experiment hypothesis."),
            "allocation": policy.get("allocation", {"control": 0.5, "treatment": 0.5}),
            "guardrails": policy.get("guardrails", []),
            "sample_profile": definition["profile"],
            "synthetic": True,
        },
        "analysis": analysis_payload,
        "quality": quality_payload,
        "summary": summary,
        "guardrails": guardrails,
        "segments": segments,
        "daily_trend": daily,
        "metrics": metrics,
        "methodology": _methodology(metrics, analysis_payload),
        "lineage": _lineage(),
        "limitations": [
            "All records are deterministic synthetic data; they do not represent production users or adoption.",
            "The conversion confidence interval uses a normal approximation for a two-proportion difference.",
            "Guardrail comparisons are descriptive and should be confirmed with a pre-registered operating plan.",
            "The browser CSV panel validates schema locally but does not upload or analyze private data.",
        ],
        "source_manifest": {
            "seed": int(definition["seed"]),
            "n_users_requested": int(n_users),
            "n_users_generated": int(manifest.n_users),
            "files": _source_manifest(raw_dir),
        },
        "ui": {
            "takeaway": definition["takeaway"],
            "status_label": "Synthetic sample • " + definition["profile"],
        },
    }
    catalog_item = {
        "id": definition["experiment_name"],
        "title": definition["title"],
        "path": f"experiments/{definition['experiment_name']}.json",
        "decision": analysis.decision,
        "quality_status": audit.summary.status,
        "assigned_users": summary.get("canonical_assigned_users", 0),
        "relative_lift": analysis.relative_lift,
        "takeaway": definition["takeaway"],
        "sample_profile": definition["profile"],
    }
    return payload, catalog_item


def write_web_artifacts(
    output_dir: str | Path,
    n_users: int = 5000,
    seed: int = 42,
) -> dict[str, Any]:
    """Run the real pipeline for both sample profiles and write browser JSON artifacts."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    catalog_items: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="experiment-forge-web-") as temp_dir:
        build_root = Path(temp_dir)
        for index, definition in enumerate(SAMPLE_DEFINITIONS):
            adjusted_definition = {**definition, "seed": seed if index == 0 else seed + 42}
            payload, catalog_item = _build_one(build_root, adjusted_definition, n_users)
            _write_json(output_path / "experiments" / f"{definition['experiment_name']}.json", payload)
            catalog_items.append(catalog_item)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "seed": seed,
        "n_users": n_users,
        "experiments": [item["id"] for item in catalog_items],
        "artifact_contract": "Each JSON payload is generated from raw CSVs, DuckDB marts, quality audit, and statistical analysis.",
    }
    _write_json(output_path / "catalog.json", {"schema_version": SCHEMA_VERSION, "experiments": catalog_items})
    _write_json(output_path / "manifest.json", manifest)
    return manifest
