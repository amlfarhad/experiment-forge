# Product Experiments

Product experimentation analytics platform built with Python, SQL, DuckDB, and Plotly.

Product Experiments turns raw product event data into tested experiment marts, audits common experimentation failures, analyzes treatment impact, and writes decision-ready artifacts for product stakeholders.

## Platform Capabilities

Experimentation work needs a full data platform around the test:

- canonical exposure and assignment data
- raw-to-staging warehouse models
- reusable user-level and daily metric marts
- sample ratio mismatch checks
- duplicate and multi-variant assignment detection
- temporal validity checks for events before assignment
- guardrail metrics for engagement and support load
- launch / hold / iterate recommendations
- readable reports and an interactive dashboard

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 forge.py demo --workspace . --users 5000 --seed 42
```

The demo writes:

- `data/sample/*.csv`
- `data/warehouse/experiment_forge.duckdb`
- `reports/quality_audit.json`
- `reports/analysis.json`
- `reports/sample_quality_audit.md`
- `reports/sample_experiment_readout.md`
- `reports/dashboard.html`

## CLI

```bash
python3 forge.py generate-demo-data --workspace .
python3 forge.py build-warehouse --workspace .
python3 forge.py audit-experiment --workspace .
python3 forge.py analyze --workspace .
python3 forge.py report --workspace .
python3 forge.py demo --workspace .
python3 forge.py credit-risk-demo --workspace . --loans 6000 --seed 42
```

## Platform Layers

| Layer | Purpose |
|---|---|
| `data_generation/` | Synthetic source systems for users, assignments, events, sessions, orders, exposures, support tickets, and daily snapshots |
| `warehouse/` | DuckDB raw, staging, intermediate, and mart models |
| `quality/` | Assignment, source, temporal, mart, and guardrail checks |
| `analysis/` | Statistical readout and decision recommendation |
| `credit_risk/` | Auto-finance PD, LGD, EAD, expected credit loss, and stress-scenario modeling |
| `reporting/` | Markdown reports and Plotly HTML dashboard |
| `config/` | Experiment and metric registry |

## Warehouse Models

```text
raw_* source tables
  -> stg_* cleaned source models
  -> int_canonical_assignments
  -> int_user_experiment_metrics
  -> int_daily_experiment_metrics
  -> mart_experiment_readout
  -> mart_metric_guardrails
  -> mart_segment_readout
  -> mart_experiment_health
```

## Quality Checks

- Sample ratio mismatch
- Duplicate assignments
- Multiple variant assignments
- Missing assignment timestamps
- Events before assignment
- Null event names
- Negative revenue
- Required mart row counts
- Sessions-per-user guardrail

## Statistical Modules

The original statistics toolkit is still included:

- Welch and Student t-tests
- Two-proportion z-tests
- Delta method ratio metrics
- Power analysis and MDE estimation
- Sequential testing
- CUPED variance reduction
- Multiple testing correction
- Bayesian A/B testing
- Multi-armed bandit simulations

## Credit Loss Forecasting

Product Experiments includes an auto-finance credit-risk workflow for portfolio loss forecasting:

- synthetic auto-loan origination and monthly performance data
- borrower risk, loan term, LTV, APR, collateral, delinquency, and macroeconomic drivers
- Probability of Default (PD), Loss Given Default (LGD), and Exposure at Default (EAD) models
- Expected Credit Loss (ECL) scoring using PD x LGD x EAD
- holdout validation with PD AUC, Brier score, LGD MAE, and EAD MAPE
- stress scenario with unemployment, used-vehicle collateral, and rate shocks
- model governance readout with assumptions, validation results, and high-loss segments

Generated artifacts:

- `reports/credit_loss_forecast.json`
- `reports/credit_loss_forecast_readout.md`
- `reports/credit_loss_scored_holdout.csv`

## Reports

Sample generated artifacts:

- [`reports/sample_quality_audit.md`](reports/sample_quality_audit.md)
- [`reports/sample_experiment_readout.md`](reports/sample_experiment_readout.md)
- `reports/dashboard.html`

## Tests

```bash
python3 -m pytest tests -q
```

## Portfolio Summary

Built an experimentation analytics platform using Python, SQL, and DuckDB to generate product event data, model experiment metric marts, detect SRM/assignment/data-quality failures, and produce launch recommendations with primary and guardrail metrics.
