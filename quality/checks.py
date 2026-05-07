"""Data quality checks for experiment source data and warehouse marts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb
import pandas as pd
from scipy import stats


@dataclass(frozen=True)
class QualityCheck:
    """Single quality check result."""

    name: str
    status: str
    severity: str
    observed: float
    threshold: float
    detail: str


@dataclass(frozen=True)
class QualitySummary:
    """Audit summary."""

    total_checks: int
    passed: int
    warnings: int
    failed: int
    status: str


@dataclass(frozen=True)
class QualityAudit:
    """Structured quality audit payload."""

    summary: QualitySummary
    checks: list[QualityCheck]

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": asdict(self.summary),
            "checks": [asdict(check) for check in self.checks],
        }


def _check(name: str, status: str, severity: str, observed: float, threshold: float, detail: str) -> QualityCheck:
    return QualityCheck(name=name, status=status, severity=severity, observed=observed, threshold=threshold, detail=detail)


def _status_from_count(count: int, severity: str = "critical") -> str:
    if count == 0:
        return "pass"
    return "fail" if severity == "critical" else "warn"


def run_quality_audit(raw_dir: str | Path, db_path: str | Path) -> QualityAudit:
    """Run source, experiment validity, and mart integrity checks."""

    raw_path = Path(raw_dir)
    assignments = pd.read_csv(raw_path / "raw_experiment_assignments.csv")
    events = pd.read_csv(raw_path / "raw_events.csv")
    orders = pd.read_csv(raw_path / "raw_orders.csv")
    checks: list[QualityCheck] = []

    canonical = assignments.sort_values(["assigned_at", "assignment_id"]).drop_duplicates(["experiment_name", "user_id"])
    split = canonical["variant"].value_counts()
    expected = [split.sum() / max(len(split), 1)] * len(split)
    p_value = float(stats.chisquare(split.to_list(), expected).pvalue) if len(split) > 1 else 1.0
    checks.append(
        _check(
            "sample_ratio_mismatch",
            "pass" if p_value >= 0.001 else "fail",
            "critical",
            p_value,
            0.001,
            f"Assignment split p-value is {p_value:.5f}.",
        )
    )

    duplicate_assignments = int(assignments.duplicated(["experiment_name", "user_id"]).sum())
    checks.append(
        _check(
            "duplicate_assignments",
            _status_from_count(duplicate_assignments),
            "critical",
            duplicate_assignments,
            0,
            f"{duplicate_assignments} duplicate experiment/user assignment rows found.",
        )
    )

    multi_variant = int((assignments.groupby(["experiment_name", "user_id"])["variant"].nunique() > 1).sum())
    checks.append(
        _check(
            "multiple_variant_assignments",
            _status_from_count(multi_variant),
            "critical",
            multi_variant,
            0,
            f"{multi_variant} users were assigned to multiple variants.",
        )
    )

    missing_assignment_timestamps = int(assignments["assigned_at"].isna().sum())
    checks.append(
        _check(
            "missing_assignment_timestamps",
            _status_from_count(missing_assignment_timestamps),
            "critical",
            missing_assignment_timestamps,
            0,
            f"{missing_assignment_timestamps} assignment timestamps are missing.",
        )
    )

    event_join = events.merge(canonical[["user_id", "assigned_at"]], on="user_id", how="left")
    event_join["event_at"] = pd.to_datetime(event_join["event_at"], errors="coerce")
    event_join["assigned_at"] = pd.to_datetime(event_join["assigned_at"], errors="coerce")
    events_before_assignment = int((event_join["event_at"] < event_join["assigned_at"]).sum())
    checks.append(
        _check(
            "events_before_assignment",
            _status_from_count(events_before_assignment),
            "critical",
            events_before_assignment,
            0,
            f"{events_before_assignment} events occurred before canonical assignment.",
        )
    )

    null_event_names = int(events["event_name"].isna().sum())
    checks.append(
        _check(
            "null_event_names",
            _status_from_count(null_event_names, severity="warning"),
            "warning",
            null_event_names,
            0,
            f"{null_event_names} events have null event_name values.",
        )
    )

    negative_revenue = int((orders["revenue"] < 0).sum())
    checks.append(
        _check(
            "negative_revenue",
            _status_from_count(negative_revenue),
            "critical",
            negative_revenue,
            0,
            f"{negative_revenue} order rows have negative revenue without refund modeling.",
        )
    )

    with duckdb.connect(str(db_path), read_only=True) as con:
        readout_rows = int(con.execute("select count(*) from mart_experiment_readout").fetchone()[0])
        segment_rows = int(con.execute("select count(*) from mart_segment_readout").fetchone()[0])
        guardrails = con.execute("select * from mart_metric_guardrails").fetchdf()
        control_sessions = float(guardrails.loc[guardrails["variant"] == "control", "sessions_per_user"].iloc[0])
        treatment_sessions = float(guardrails.loc[guardrails["variant"] == "treatment", "sessions_per_user"].iloc[0])
        session_ratio = treatment_sessions / control_sessions if control_sessions else 0.0

    checks.append(
        _check(
            "mart_experiment_readout_rows",
            "pass" if readout_rows == 2 else "fail",
            "critical",
            readout_rows,
            2,
            f"mart_experiment_readout has {readout_rows} rows.",
        )
    )
    checks.append(
        _check(
            "mart_segment_readout_rows",
            "pass" if segment_rows >= 6 else "fail",
            "critical",
            segment_rows,
            6,
            f"mart_segment_readout has {segment_rows} rows.",
        )
    )
    checks.append(
        _check(
            "guardrail_sessions_per_user",
            "pass" if session_ratio >= 0.98 else "warn",
            "warning",
            session_ratio,
            0.98,
            f"Treatment/control sessions per user ratio is {session_ratio:.3f}.",
        )
    )

    failed = sum(1 for check in checks if check.status == "fail")
    warnings = sum(1 for check in checks if check.status == "warn")
    status = "fail" if failed else "warn" if warnings else "pass"
    summary = QualitySummary(
        total_checks=len(checks),
        passed=sum(1 for check in checks if check.status == "pass"),
        warnings=warnings,
        failed=failed,
        status=status,
    )
    return QualityAudit(summary=summary, checks=checks)
