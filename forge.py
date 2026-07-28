"""Command-line workflow for Product Experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from analysis.experiment_readout import analyze_experiment
from credit_risk.modeling import run_credit_loss_forecast
from credit_risk.reports import write_credit_loss_report
from credit_risk.synthetic_auto import generate_auto_loan_portfolio
from data_generation.synthetic_product import generate_demo_data
from quality.checks import run_quality_audit
from reporting.reports import write_dashboard_html, write_experiment_readout, write_quality_audit
from warehouse.build import build_warehouse


def workspace_paths(workspace: str | Path) -> dict[str, Path]:
    root = Path(workspace)
    return {
        "root": root,
        "raw": root / "data" / "sample",
        "warehouse": root / "data" / "warehouse",
        "db": root / "data" / "warehouse" / "experiment_forge.duckdb",
        "reports": root / "reports",
    }


def cmd_generate(args: argparse.Namespace) -> None:
    paths = workspace_paths(args.workspace)
    manifest = generate_demo_data(paths["raw"], seed=args.seed, n_users=args.users)
    print(f"Generated demo data: {len(manifest.files)} files in {paths['raw']}")


def cmd_build(args: argparse.Namespace) -> None:
    paths = workspace_paths(args.workspace)
    result = build_warehouse(paths["raw"], paths["db"])
    print(f"Built warehouse: {len(result.tables_built)} models in {paths['db']}")


def cmd_audit(args: argparse.Namespace):
    paths = workspace_paths(args.workspace)
    audit = run_quality_audit(paths["raw"], paths["db"])
    paths["reports"].mkdir(parents=True, exist_ok=True)
    (paths["reports"] / "quality_audit.json").write_text(json.dumps(audit.to_dict(), indent=2))
    print(
        f"Quality audit: {audit.summary.passed} passed, "
        f"{audit.summary.warnings} warnings, {audit.summary.failed} failed"
    )
    return audit


def cmd_analyze(args: argparse.Namespace, audit=None):
    paths = workspace_paths(args.workspace)
    if audit is None:
        audit = run_quality_audit(paths["raw"], paths["db"])
    analysis = analyze_experiment(paths["db"], audit)
    paths["reports"].mkdir(parents=True, exist_ok=True)
    (paths["reports"] / "analysis.json").write_text(json.dumps(analysis.to_dict(), indent=2))
    print(f"Experiment analysis: recommendation={analysis.recommendation}")
    return analysis


def cmd_report(args: argparse.Namespace, audit=None, analysis=None) -> None:
    paths = workspace_paths(args.workspace)
    if audit is None:
        audit = run_quality_audit(paths["raw"], paths["db"])
    if analysis is None:
        analysis = analyze_experiment(paths["db"], audit)
    write_quality_audit(audit, paths["reports"] / "sample_quality_audit.md")
    write_experiment_readout(analysis, paths["reports"] / "sample_experiment_readout.md")
    write_dashboard_html(paths["db"], analysis, paths["reports"] / "dashboard.html")
    print(f"Wrote reports: {paths['reports']}")


def cmd_demo(args: argparse.Namespace) -> None:
    cmd_generate(args)
    cmd_build(args)
    audit = cmd_audit(args)
    analysis = cmd_analyze(args, audit=audit)
    cmd_report(args, audit=audit, analysis=analysis)


def cmd_credit_risk_demo(args: argparse.Namespace) -> None:
    paths = workspace_paths(args.workspace)
    raw_dir = paths["raw"] / "credit_risk"
    manifest = generate_auto_loan_portfolio(raw_dir, seed=args.seed, n_loans=args.loans)
    forecast = run_credit_loss_forecast(raw_dir, paths["reports"])
    write_credit_loss_report(forecast, paths["reports"])
    print(
        "Credit loss forecast: "
        f"loans={args.loans}, files=3, pd_auc={forecast.pd_auc:.3f}, "
        f"stress_lift={forecast.stress_lift:.1%}, reports={paths['reports']}"
    )
    print(f"Source files: {manifest.loans_path}, {manifest.performance_path}, {manifest.macro_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Product Experiments analytics workflow")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command_name in ["generate-demo-data", "build-warehouse", "audit-experiment", "analyze", "report", "demo"]:
        subparser = subparsers.add_parser(command_name)
        subparser.add_argument("--workspace", default=".", help="Workspace for data and report artifacts")
        subparser.add_argument("--users", type=int, default=5000, help="Number of synthetic users to generate")
        subparser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    subparsers.choices["generate-demo-data"].set_defaults(func=cmd_generate)
    subparsers.choices["build-warehouse"].set_defaults(func=cmd_build)
    subparsers.choices["audit-experiment"].set_defaults(func=cmd_audit)
    subparsers.choices["analyze"].set_defaults(func=cmd_analyze)
    subparsers.choices["report"].set_defaults(func=cmd_report)
    subparsers.choices["demo"].set_defaults(func=cmd_demo)

    credit_parser = subparsers.add_parser("credit-risk-demo")
    credit_parser.add_argument("--workspace", default=".", help="Workspace for data and report artifacts")
    credit_parser.add_argument("--loans", type=int, default=6000, help="Number of synthetic auto loans")
    credit_parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    credit_parser.set_defaults(func=cmd_credit_risk_demo)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
