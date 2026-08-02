import json

import pandas as pd

from analysis.experiment_readout import analyze_experiment
from data_generation.synthetic_product import generate_demo_data
from quality.checks import run_quality_audit
from warehouse.build import build_warehouse


def test_default_profile_stays_deliberately_flawed(tmp_path):
    raw_dir = tmp_path / "raw"
    db_path = tmp_path / "warehouse.duckdb"

    generate_demo_data(raw_dir, seed=42, n_users=700)
    build_warehouse(raw_dir, db_path)
    audit = run_quality_audit(raw_dir, db_path)
    analysis = analyze_experiment(db_path, audit)

    assert audit.summary.failed >= 1
    assert analysis.decision == "investigate"
    assert analysis.recommendation == "hold"
    assert analysis.multiple_testing_method == "Holm-Bonferroni"
    assert analysis.confirmatory_metrics
    json.dumps(analysis.to_dict())


def test_clean_profile_has_no_injected_source_failures(tmp_path):
    raw_dir = tmp_path / "raw"
    db_path = tmp_path / "warehouse.duckdb"

    generate_demo_data(
        raw_dir,
        seed=42,
        n_users=5000,
        experiment_name="search_autocomplete_refresh",
        quality_profile="clean",
        treatment_lift=0.025,
    )
    build_warehouse(raw_dir, db_path)
    audit = run_quality_audit(raw_dir, db_path)

    assert not pd.read_csv(raw_dir / "raw_experiment_assignments.csv").duplicated(
        ["experiment_name", "user_id"]
    ).any()
    assert not pd.read_csv(raw_dir / "raw_events.csv")["event_name"].isna().any()
    assert not (pd.read_csv(raw_dir / "raw_orders.csv")["revenue"] < 0).any()
    assert audit.summary.failed == 0


def test_analysis_reports_practical_and_adjusted_evidence(tmp_path):
    raw_dir = tmp_path / "raw"
    db_path = tmp_path / "warehouse.duckdb"

    generate_demo_data(
        raw_dir,
        seed=42,
        n_users=5000,
        experiment_name="search_autocomplete_refresh",
        quality_profile="clean",
        treatment_lift=0.025,
    )
    build_warehouse(raw_dir, db_path)
    audit = run_quality_audit(raw_dir, db_path)
    analysis = analyze_experiment(db_path, audit)

    assert analysis.decision == "launch"
    assert analysis.practical_threshold == 0.01
    assert analysis.practical_significance is True
    assert analysis.adjusted_p_value >= analysis.p_value
    assert {item["metric"] for item in analysis.confirmatory_metrics} == {
        "conversion_rate",
        "revenue_per_user",
    }
