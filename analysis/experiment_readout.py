"""Decision analysis for Product Experiments marts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb

from core.experiment import analyze_proportion
from quality.checks import QualityAudit


@dataclass(frozen=True)
class VariantMetrics:
    """Metric values for one variant."""

    variant: str
    assigned_users: int
    conversions: int
    conversion_rate: float
    revenue_per_user: float
    sessions_per_user: float
    support_tickets_per_user: float


@dataclass(frozen=True)
class ExperimentAnalysis:
    """Product-facing experiment analysis payload."""

    experiment_name: str
    primary_metric: str
    control: VariantMetrics
    treatment: VariantMetrics
    absolute_lift: float
    relative_lift: float
    p_value: float
    ci_lower: float
    ci_upper: float
    recommendation: str
    rationale: list[str]
    quality_status: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _variant_metrics(row) -> VariantMetrics:
    return VariantMetrics(
        variant=str(row["variant"]),
        assigned_users=int(row["assigned_users"]),
        conversions=int(row["conversions"]),
        conversion_rate=float(row["conversion_rate"]),
        revenue_per_user=float(row["revenue_per_user"]),
        sessions_per_user=float(row["sessions_per_user"]),
        support_tickets_per_user=float(row["support_tickets_per_user"]),
    )


def analyze_experiment(db_path: str | Path, audit: QualityAudit) -> ExperimentAnalysis:
    """Analyze the primary conversion metric and produce a decision recommendation."""

    with duckdb.connect(str(db_path), read_only=True) as con:
        readout = con.execute("select * from mart_experiment_readout order by variant").fetchdf()

    control_row = readout.loc[readout["variant"] == "control"].iloc[0]
    treatment_row = readout.loc[readout["variant"] == "treatment"].iloc[0]
    control = _variant_metrics(control_row)
    treatment = _variant_metrics(treatment_row)

    stat_result = analyze_proportion(
        control_successes=control.conversions,
        control_total=control.assigned_users,
        treatment_successes=treatment.conversions,
        treatment_total=treatment.assigned_users,
    )
    absolute_lift = treatment.conversion_rate - control.conversion_rate
    relative_lift = absolute_lift / control.conversion_rate if control.conversion_rate else 0.0

    rationale: list[str] = []
    if audit.summary.failed:
        recommendation = "hold"
        rationale.append("Critical quality checks failed, so the result should not be used for launch decisions yet.")
    elif stat_result.is_significant and absolute_lift > 0:
        recommendation = "launch"
        rationale.append("Treatment improved the primary metric with statistical significance.")
    elif absolute_lift > 0:
        recommendation = "iterate"
        rationale.append("Treatment direction is positive, but evidence is not strong enough for a full launch.")
    else:
        recommendation = "iterate"
        rationale.append("Treatment did not improve the primary metric.")

    if treatment.sessions_per_user < control.sessions_per_user * 0.98:
        rationale.append("Session engagement guardrail is weaker for treatment.")
    if treatment.support_tickets_per_user > control.support_tickets_per_user * 1.10:
        rationale.append("Support ticket burden is higher for treatment.")

    return ExperimentAnalysis(
        experiment_name=str(control_row["experiment_name"]),
        primary_metric="conversion_rate",
        control=control,
        treatment=treatment,
        absolute_lift=float(absolute_lift),
        relative_lift=float(relative_lift),
        p_value=float(stat_result.p_value),
        ci_lower=float(stat_result.ci_lower),
        ci_upper=float(stat_result.ci_upper),
        recommendation=recommendation,
        rationale=rationale,
        quality_status=audit.summary.status,
    )
