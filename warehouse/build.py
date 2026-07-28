"""Build a local DuckDB warehouse from Product Experiments source CSVs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb


MODEL_ROOT = Path(__file__).resolve().parent / "models"
RAW_TABLES = {
    "raw_users": "raw_users.csv",
    "raw_experiment_assignments": "raw_experiment_assignments.csv",
    "raw_events": "raw_events.csv",
    "raw_sessions": "raw_sessions.csv",
    "raw_orders": "raw_orders.csv",
    "raw_feature_exposures": "raw_feature_exposures.csv",
    "raw_support_tickets": "raw_support_tickets.csv",
    "raw_user_daily_snapshots": "raw_user_daily_snapshots.csv",
}
MODEL_ORDER = [
    "staging/stg_users.sql",
    "staging/stg_experiment_assignments.sql",
    "staging/stg_events.sql",
    "staging/stg_sessions.sql",
    "staging/stg_orders.sql",
    "staging/stg_feature_exposures.sql",
    "staging/stg_support_tickets.sql",
    "staging/stg_user_daily_snapshots.sql",
    "intermediate/int_canonical_assignments.sql",
    "intermediate/int_user_experiment_metrics.sql",
    "intermediate/int_daily_experiment_metrics.sql",
    "marts/mart_experiment_readout.sql",
    "marts/mart_metric_guardrails.sql",
    "marts/mart_segment_readout.sql",
    "marts/mart_experiment_health.sql",
]


@dataclass(frozen=True)
class WarehouseBuildResult:
    """Result of a warehouse build."""

    db_path: Path
    raw_tables: list[str]
    tables_built: list[str]


def _load_raw_tables(con: duckdb.DuckDBPyConnection, raw_dir: Path) -> list[str]:
    loaded: list[str] = []
    for table_name, filename in RAW_TABLES.items():
        csv_path = raw_dir / filename
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing required source file: {csv_path}")
        con.execute(
            f"create or replace table {table_name} as select * from read_csv_auto(?, header=true)",
            [str(csv_path)],
        )
        loaded.append(table_name)
    return loaded


def build_warehouse(raw_dir: str | Path, db_path: str | Path) -> WarehouseBuildResult:
    """Build raw, staging, intermediate, and mart tables."""

    raw_path = Path(raw_dir)
    database_path = Path(db_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    tables_built: list[str] = []

    with duckdb.connect(str(database_path)) as con:
        raw_tables = _load_raw_tables(con, raw_path)
        for relative_model_path in MODEL_ORDER:
            sql_path = MODEL_ROOT / relative_model_path
            con.execute(sql_path.read_text())
            tables_built.append(sql_path.stem)

    return WarehouseBuildResult(db_path=database_path, raw_tables=raw_tables, tables_built=tables_built)


def list_tables(db_path: str | Path) -> list[str]:
    """List tables in the DuckDB database."""

    with duckdb.connect(str(db_path), read_only=True) as con:
        rows = con.execute("show tables").fetchall()
    return sorted(row[0] for row in rows)
