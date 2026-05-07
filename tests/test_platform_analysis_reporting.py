import json

from analysis.experiment_readout import analyze_experiment
from data_generation.synthetic_product import generate_demo_data
from quality.checks import run_quality_audit
from reporting.reports import write_dashboard_html, write_experiment_readout, write_quality_audit
from warehouse.build import build_warehouse


def test_analyze_experiment_returns_decision_payload(tmp_path):
    raw_dir = tmp_path / "raw"
    db_path = tmp_path / "warehouse.duckdb"
    generate_demo_data(raw_dir, seed=42, n_users=900)
    build_warehouse(raw_dir, db_path)
    audit = run_quality_audit(raw_dir, db_path)

    analysis = analyze_experiment(db_path=db_path, audit=audit)

    assert analysis.experiment_name == "checkout_progress_indicator"
    assert analysis.primary_metric == "conversion_rate"
    assert analysis.recommendation in {"launch", "hold", "iterate"}
    assert analysis.treatment.variant == "treatment"
    assert analysis.control.variant == "control"
    assert isinstance(json.dumps(analysis.to_dict()), str)


def test_reports_write_markdown_and_interactive_html(tmp_path):
    raw_dir = tmp_path / "raw"
    db_path = tmp_path / "warehouse.duckdb"
    report_dir = tmp_path / "reports"
    generate_demo_data(raw_dir, seed=42, n_users=900)
    build_warehouse(raw_dir, db_path)
    audit = run_quality_audit(raw_dir, db_path)
    analysis = analyze_experiment(db_path=db_path, audit=audit)

    quality_path = write_quality_audit(audit, report_dir / "quality.md")
    readout_path = write_experiment_readout(analysis, report_dir / "readout.md")
    dashboard_path = write_dashboard_html(db_path, analysis, report_dir / "dashboard.html")

    assert "# Experiment Quality Audit" in quality_path.read_text()
    assert "# Experiment Readout" in readout_path.read_text()
    assert "Plotly.newPlot" in dashboard_path.read_text()
    assert "checkout_progress_indicator" in dashboard_path.read_text()
