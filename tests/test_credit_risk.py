import json
import subprocess
import sys

from credit_risk.modeling import run_credit_loss_forecast
from credit_risk.reports import write_credit_loss_report
from credit_risk.synthetic_auto import generate_auto_loan_portfolio


def test_credit_loss_forecast_writes_model_artifacts(tmp_path):
    raw_dir = tmp_path / "data" / "sample" / "credit_risk"
    reports_dir = tmp_path / "reports"

    manifest = generate_auto_loan_portfolio(raw_dir, seed=7, n_loans=1200)
    assert manifest.loans_path.exists()
    assert manifest.performance_path.exists()
    assert manifest.macro_path.exists()

    forecast = run_credit_loss_forecast(raw_dir, reports_dir)
    write_credit_loss_report(forecast, reports_dir)

    assert forecast.records_scored > 0
    assert forecast.pd_auc >= 0.6
    assert forecast.stress_expected_loss > forecast.baseline_expected_loss
    assert len(forecast.high_risk_segments) > 0
    assert (reports_dir / "credit_loss_scored_holdout.csv").exists()
    assert (reports_dir / "credit_loss_forecast_readout.md").exists()

    payload = json.loads((reports_dir / "credit_loss_forecast.json").read_text())
    assert payload["stress_lift"] > 0
    assert payload["records_scored"] == forecast.records_scored


def test_credit_risk_cli_runs_end_to_end(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "forge.py",
            "credit-risk-demo",
            "--workspace",
            str(tmp_path),
            "--loans",
            "1000",
            "--seed",
            "17",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "credit loss forecast" in result.stdout.lower()
    assert (tmp_path / "reports" / "credit_loss_forecast.json").exists()
    assert (tmp_path / "reports" / "credit_loss_forecast_readout.md").exists()
