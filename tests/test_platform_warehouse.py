import duckdb

from data_generation.synthetic_product import generate_demo_data
from warehouse.build import build_warehouse, list_tables


def test_build_warehouse_creates_analytics_engineering_tables(tmp_path):
    raw_dir = tmp_path / "raw"
    db_path = tmp_path / "warehouse" / "experiment_forge.duckdb"
    generate_demo_data(raw_dir, seed=7, n_users=700)

    result = build_warehouse(raw_dir=raw_dir, db_path=db_path)

    expected_tables = {
        "stg_users",
        "stg_experiment_assignments",
        "stg_events",
        "stg_sessions",
        "stg_orders",
        "stg_feature_exposures",
        "stg_support_tickets",
        "stg_user_daily_snapshots",
        "int_canonical_assignments",
        "int_user_experiment_metrics",
        "int_daily_experiment_metrics",
        "mart_experiment_readout",
        "mart_metric_guardrails",
        "mart_segment_readout",
        "mart_experiment_health",
    }

    assert expected_tables.issubset(set(result.tables_built))
    assert expected_tables.issubset(set(list_tables(db_path)))

    with duckdb.connect(str(db_path)) as con:
        readout_rows = con.execute("select count(*) from mart_experiment_readout").fetchone()[0]
        segment_rows = con.execute("select count(*) from mart_segment_readout").fetchone()[0]
        health_rows = con.execute("select count(*) from mart_experiment_health").fetchone()[0]

    assert readout_rows == 2
    assert segment_rows >= 6
    assert health_rows == 1
