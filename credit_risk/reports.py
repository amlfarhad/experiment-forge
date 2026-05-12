"""Reporting artifacts for credit loss forecasts."""

from __future__ import annotations

import json
from pathlib import Path

from .modeling import CreditLossForecast


def write_credit_loss_report(forecast: CreditLossForecast, output_dir: str | Path) -> None:
    """Write model governance and business-readout artifacts."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    payload = forecast.to_dict()
    (output_path / "credit_loss_forecast.json").write_text(json.dumps(payload, indent=2))

    segment_rows = "\n".join(
        "| {fico_band} | {vehicle_type} | {loans} | {avg_pd:.2%} | {avg_lgd:.2%} | ${expected_loss:,.0f} |".format(
            **segment
        )
        for segment in forecast.high_risk_segments
    )
    report = f"""# Credit Loss Forecast Readout

## Model Scope

Auto-finance credit loss forecast using portfolio-level borrower attributes, loan terms, monthly performance, delinquency behavior, collateral price pressure, and macroeconomic drivers.

## Model Components

- Probability of Default (PD): logistic regression with borrower, loan, performance, and macroeconomic drivers.
- Loss Given Default (LGD): regression model trained on observed default outcomes.
- Exposure at Default (EAD): regression model trained on defaulted-account balances.
- Expected Credit Loss (ECL): PD x LGD x EAD for each active loan-month record.
- Stress scenario: unemployment +250 bps, used-vehicle collateral index -9%, interest-rate index +120 bps.

## Holdout Validation

| Metric | Value |
|---|---:|
| Holdout records scored | {forecast.records_scored:,} |
| PD AUC | {forecast.pd_auc:.3f} |
| PD Brier score | {forecast.pd_brier:.4f} |
| LGD MAE | {forecast.lgd_mae:.3f} |
| EAD MAPE | {forecast.ead_mape:.3f} |

## Forecast Summary

| Scenario | Expected credit loss |
|---|---:|
| Baseline | ${forecast.baseline_expected_loss:,.0f} |
| Stressed macro | ${forecast.stress_expected_loss:,.0f} |
| Stress lift | {forecast.stress_lift:.1%} |

## Highest-Loss Segments

| FICO band | Vehicle type | Loans | Avg PD | Avg LGD | Expected loss |
|---|---:|---:|---:|---:|---:|
{segment_rows}

## Governance Notes

- Uses a deterministic train/holdout split by observation month to avoid look-ahead leakage.
- Separates PD, LGD, and EAD so model performance and business assumptions can be reviewed independently.
- Writes scored holdout records for challenger-model comparison, audit review, and portfolio monitoring.
- Keeps stress assumptions explicit so Risk, Finance, and business partners can challenge or replace them.
"""
    (output_path / "credit_loss_forecast_readout.md").write_text(report)
