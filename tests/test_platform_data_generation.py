from pathlib import Path

import pandas as pd

from data_generation.synthetic_product import generate_demo_data


def test_generate_demo_data_creates_platform_sources(tmp_path):
    manifest = generate_demo_data(tmp_path, seed=2026, n_users=600)

    expected = {
        "raw_users.csv",
        "raw_experiment_assignments.csv",
        "raw_events.csv",
        "raw_sessions.csv",
        "raw_orders.csv",
        "raw_feature_exposures.csv",
        "raw_support_tickets.csv",
        "raw_user_daily_snapshots.csv",
    }

    assert {Path(path).name for path in manifest.files} == expected
    assert manifest.n_users == 600
    assert manifest.experiment_name == "checkout_progress_indicator"


def test_generated_sources_include_realistic_quality_failures(tmp_path):
    generate_demo_data(tmp_path, seed=42, n_users=900)

    assignments = pd.read_csv(tmp_path / "raw_experiment_assignments.csv")
    events = pd.read_csv(tmp_path / "raw_events.csv")
    orders = pd.read_csv(tmp_path / "raw_orders.csv")
    tickets = pd.read_csv(tmp_path / "raw_support_tickets.csv")

    assert assignments.duplicated(["experiment_name", "user_id"]).any()
    assert events["event_name"].isna().any()
    assert (orders["revenue"] < 0).any()
    assert tickets["priority"].isin(["urgent"]).any()


def test_generated_data_is_reproducible(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"

    generate_demo_data(first, seed=99, n_users=250)
    generate_demo_data(second, seed=99, n_users=250)

    pd.testing.assert_frame_equal(
        pd.read_csv(first / "raw_user_daily_snapshots.csv"),
        pd.read_csv(second / "raw_user_daily_snapshots.csv"),
    )
