"""Write quality, decision, and dashboard artifacts."""

from __future__ import annotations

from pathlib import Path

import duckdb
import plotly.graph_objects as go
from plotly.offline import plot

from analysis.experiment_readout import ExperimentAnalysis
from quality.checks import QualityAudit


def _pct(value: float) -> str:
    return f"{value:.2%}"


def write_quality_audit(audit: QualityAudit, output_path: str | Path) -> Path:
    """Write a Markdown quality audit report."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Experiment Quality Audit",
        "",
        f"Overall status: **{audit.summary.status.upper()}**",
        "",
        "| Check | Status | Severity | Observed | Threshold | Detail |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for check in audit.checks:
        lines.append(
            f"| {check.name} | {check.status.upper()} | {check.severity} | "
            f"{check.observed} | {check.threshold} | {check.detail} |"
        )
    path.write_text("\n".join(lines) + "\n")
    return path


def write_experiment_readout(analysis: ExperimentAnalysis, output_path: str | Path) -> Path:
    """Write a decision-ready Markdown experiment readout."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Experiment Readout",
        "",
        f"Experiment: **{analysis.experiment_name}**",
        f"Primary metric: **{analysis.primary_metric}**",
        "",
        "## Recommendation",
        "",
        f"**{analysis.recommendation.upper()}**",
        "",
        "## Executive Rationale",
        "",
    ]
    for item in analysis.rationale:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Variant Metrics",
            "",
            "| Variant | Users | Conversion Rate | Revenue / User | Sessions / User | Support Tickets / User |",
            "|---|---:|---:|---:|---:|---:|",
            (
                f"| control | {analysis.control.assigned_users} | {_pct(analysis.control.conversion_rate)} | "
                f"${analysis.control.revenue_per_user:.2f} | {analysis.control.sessions_per_user:.2f} | "
                f"{analysis.control.support_tickets_per_user:.3f} |"
            ),
            (
                f"| treatment | {analysis.treatment.assigned_users} | {_pct(analysis.treatment.conversion_rate)} | "
                f"${analysis.treatment.revenue_per_user:.2f} | {analysis.treatment.sessions_per_user:.2f} | "
                f"{analysis.treatment.support_tickets_per_user:.3f} |"
            ),
            "",
            "## Statistical Summary",
            "",
            f"- Absolute conversion lift: {analysis.absolute_lift:+.4f}",
            f"- Relative conversion lift: {analysis.relative_lift:+.2%}",
            f"- p-value: {analysis.p_value:.5f}",
            f"- 95% confidence interval for conversion-rate difference: [{analysis.ci_lower:.4f}, {analysis.ci_upper:.4f}]",
            f"- Quality status: {analysis.quality_status.upper()}",
        ]
    )
    path.write_text("\n".join(lines) + "\n")
    return path


def write_dashboard_html(db_path: str | Path, analysis: ExperimentAnalysis, output_path: str | Path) -> Path:
    """Write an interactive Plotly HTML dashboard."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path), read_only=True) as con:
        readout = con.execute("select * from mart_experiment_readout order by variant").fetchdf()
        segments = con.execute("select * from mart_segment_readout order by segment, variant").fetchdf()
        daily = con.execute("select * from int_daily_experiment_metrics order by snapshot_date, variant").fetchdf()

    conversion_fig = go.Figure(
        data=[
            go.Bar(
                x=readout["variant"],
                y=readout["conversion_rate"],
                marker_color=["#334155", "#0f766e"],
                text=[f"{value:.2%}" for value in readout["conversion_rate"]],
                textposition="auto",
            )
        ],
        layout=go.Layout(title="Conversion Rate by Variant", yaxis_tickformat=".1%"),
    )

    segment_fig = go.Figure()
    for variant in sorted(segments["variant"].unique()):
        frame = segments.loc[segments["variant"] == variant]
        segment_fig.add_trace(go.Bar(name=variant, x=frame["segment"], y=frame["conversion_rate"]))
    segment_fig.update_layout(title="Segment Conversion Rate", barmode="group", yaxis_tickformat=".1%")

    daily_fig = go.Figure()
    daily_rollup = daily.groupby(["snapshot_date", "variant"], as_index=False)["cumulative_revenue"].sum()
    for variant in sorted(daily_rollup["variant"].unique()):
        frame = daily_rollup.loc[daily_rollup["variant"] == variant]
        daily_fig.add_trace(go.Scatter(name=variant, x=frame["snapshot_date"], y=frame["cumulative_revenue"]))
    daily_fig.update_layout(title="Cumulative Revenue Over Time")

    html = f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Experiment Forge Dashboard</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #111827; }}
    header {{ max-width: 980px; margin-bottom: 24px; }}
    .badge {{ display: inline-block; padding: 6px 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }}
    .panel {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; }}
    .wide {{ grid-column: 1 / -1; }}
  </style>
</head>
<body>
  <header>
    <div class="badge">{analysis.experiment_name}</div>
    <h1>Experiment Forge Dashboard</h1>
    <p>Recommendation: <strong>{analysis.recommendation.upper()}</strong></p>
  </header>
  <section class="grid">
    <div class="panel">{plot(conversion_fig, include_plotlyjs="cdn", output_type="div")}</div>
    <div class="panel">{plot(segment_fig, include_plotlyjs=False, output_type="div")}</div>
    <div class="panel wide">{plot(daily_fig, include_plotlyjs=False, output_type="div")}</div>
  </section>
</body>
</html>
"""
    path.write_text(html)
    return path
