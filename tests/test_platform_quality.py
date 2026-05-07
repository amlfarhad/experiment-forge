from data_generation.synthetic_product import generate_demo_data
from quality.checks import run_quality_audit
from warehouse.build import build_warehouse


def test_quality_audit_covers_source_warehouse_and_experiment_validity(tmp_path):
    raw_dir = tmp_path / "raw"
    db_path = tmp_path / "warehouse.duckdb"
    generate_demo_data(raw_dir, seed=42, n_users=800)
    build_warehouse(raw_dir, db_path)

    audit = run_quality_audit(raw_dir=raw_dir, db_path=db_path)
    names = {check.name for check in audit.checks}

    assert "sample_ratio_mismatch" in names
    assert "duplicate_assignments" in names
    assert "multiple_variant_assignments" in names
    assert "events_before_assignment" in names
    assert "negative_revenue" in names
    assert "mart_experiment_readout_rows" in names
    assert "guardrail_sessions_per_user" in names
    assert audit.summary.total_checks == len(audit.checks)


def test_quality_audit_serializes_to_dict(tmp_path):
    raw_dir = tmp_path / "raw"
    db_path = tmp_path / "warehouse.duckdb"
    generate_demo_data(raw_dir, seed=1, n_users=400)
    build_warehouse(raw_dir, db_path)

    audit = run_quality_audit(raw_dir=raw_dir, db_path=db_path)
    payload = audit.to_dict()

    assert payload["summary"]["total_checks"] == len(payload["checks"])
    assert all("severity" in check for check in payload["checks"])
    assert payload["summary"]["status"] in {"pass", "warn", "fail"}
