"""Decision analysis for Experiment Forge marts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

import duckdb
import yaml

from core.experiment import analyze_continuous, analyze_proportion
from core.multiple_testing import holm_bonferroni
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
    avg_session_duration_seconds: float = 0.0
    high_priority_tickets_per_user: float = 0.0
    negative_revenue_user_rate: float = 0.0


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
    decision: str = "continue"
    practical_threshold: float = 0.01
    practical_significance: bool = False
    effect_size: float = 0.0
    test_statistic: float = 0.0
    adjusted_p_value: float = 1.0
    multiple_testing_method: str = "Holm-Bonferroni"
    confirmatory_metrics: list[dict[str, object]] = field(default_factory=list)

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
        avg_session_duration_seconds=float(row.get("avg_session_duration_seconds", 0.0)),
        high_priority_tickets_per_user=float(row.get("high_priority_tickets_per_user", 0.0)),
        negative_revenue_user_rate=float(row.get("negative_revenue_user_rate", 0.0)),
    )


def _policy_for(experiment_name: str, config_path: str | Path | None) -> dict[str, object]:
    path = Path(config_path) if config_path else Path(__file__).resolve().parents[1] / "config" / "experiments.yml"
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text()) or {}
    return dict(payload.get("experiments", {}).get(experiment_name, {}))


def analyze_experiment(
    db_path: str | Path,
    audit: QualityAudit,
    config_path: str | Path | None = None,
) -> ExperimentAnalysis:
    """Analyze the primary metric and produce a traceable decision recommendation."""

    with duckdb.connect(str(db_path), read_only=True) as con:
        readout = con.execute("select * from mart_experiment_readout order by variant").fetchdf()
        user_metrics = con.execute("select * from int_user_experiment_metrics").fetchdf()

    control_row = readout.loc[readout["variant"] == "control"].iloc[0]
    treatment_row = readout.loc[readout["variant"] == "treatment"].iloc[0]
    control = _variant_metrics(control_row)
    treatment = _variant_metrics(treatment_row)

    experiment_name = str(control_row["experiment_name"])
    policy = _policy_for(experiment_name, config_path)
    launch_criteria = dict(policy.get("launch_criteria", {}))
    alpha = float(launch_criteria.get("max_p_value", 0.05))
    practical_threshold = float(launch_criteria.get("min_relative_lift", 0.01))

    stat_result = analyze_proportion(
        control_successes=control.conversions,
        control_total=control.assigned_users,
        treatment_successes=treatment.conversions,
        treatment_total=treatment.assigned_users,
        alpha=alpha,
    )
    revenue_result = analyze_continuous(
        user_metrics.loc[user_metrics["variant"] == "control", "revenue"].to_numpy(),
        user_metrics.loc[user_metrics["variant"] == "treatment", "revenue"].to_numpy(),
        alpha=alpha,
    )
    absolute_lift = treatment.conversion_rate - control.conversion_rate
    relative_lift = absolute_lift / control.conversion_rate if control.conversion_rate else 0.0
    practical_significance = abs(relative_lift) >= practical_threshold

    correction = holm_bonferroni([stat_result.p_value, revenue_result.p_value], alpha=alpha)
    adjusted_values = correction["adjusted_p_values"]
    confirmatory_metrics = [
        {
            "metric": "conversion_rate",
            "role": "primary",
            "p_value": float(stat_result.p_value),
            "adjusted_p_value": float(adjusted_values[0]),
            "effect": float(relative_lift),
            "significant": bool(adjusted_values[0] < alpha),
        },
        {
            "metric": "revenue_per_user",
            "role": "secondary",
            "p_value": float(revenue_result.p_value),
            "adjusted_p_value": float(adjusted_values[1]),
            "effect": float(revenue_result.relative_lift),
            "significant": bool(adjusted_values[1] < alpha),
        },
    ]

    rationale: list[str] = []
    if audit.summary.failed:
        recommendation = "hold"
        decision = "investigate"
        rationale.append("Critical quality checks failed, so the result should not be used for launch decisions yet.")
    elif adjusted_values[0] < alpha and absolute_lift > 0 and practical_significance:
        recommendation = "launch"
        decision = "launch"
        rationale.append("Treatment improved the primary metric with adjusted statistical significance and cleared the practical threshold.")
    elif adjusted_values[0] < alpha and absolute_lift < 0 and practical_significance:
        recommendation = "iterate"
        decision = "stop"
        rationale.append("Treatment harmed the primary metric with adjusted statistical significance and exceeded the practical harm threshold.")
    elif absolute_lift > 0:
        recommendation = "iterate"
        decision = "continue"
        rationale.append("Treatment direction is positive, but evidence is not strong enough for a full launch.")
    else:
        recommendation = "iterate"
        decision = "continue"
        rationale.append("Treatment did not improve the primary metric.")

    if treatment.sessions_per_user < control.sessions_per_user * 0.98:
        rationale.append("Session engagement guardrail is weaker for treatment.")
    if treatment.support_tickets_per_user > control.support_tickets_per_user * 1.10:
        rationale.append("Support ticket burden is higher for treatment.")
    if not practical_significance:
        rationale.append(
            f"The relative primary-metric change is {relative_lift:+.2%}, below the {practical_threshold:.2%} practical threshold."
        )
    rationale.append("The primary and secondary metrics use Holm-Bonferroni adjustment; segments remain exploratory.")

    return ExperimentAnalysis(
        experiment_name=experiment_name,
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
        decision=decision,
        practical_threshold=practical_threshold,
        practical_significance=practical_significance,
        effect_size=float(stat_result.effect_size),
        test_statistic=float(stat_result.statistic),
        adjusted_p_value=float(adjusted_values[0]),
        multiple_testing_method="Holm-Bonferroni",
        confirmatory_metrics=confirmatory_metrics,
    )
