# experiment-forge

Product experimentation analytics platform built with Python, SQL, DuckDB, and Plotly.

Experiment Forge turns raw product event data into tested experiment marts, audits common experimentation failures, analyzes treatment impact, and writes decision-ready artifacts for product stakeholders.

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
```

## Platform Layers

| Layer | Purpose |
|---|---|
| `data_generation/` | Synthetic source systems for users, assignments, events, sessions, orders, exposures, support tickets, and daily snapshots |
| `warehouse/` | DuckDB raw, staging, intermediate, and mart models |
| `quality/` | Assignment, source, temporal, mart, and guardrail checks |
| `analysis/` | Statistical readout and decision recommendation |
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
