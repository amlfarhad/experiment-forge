# experiment-forge

Experimentation analytics platform and credential-free decision product built with Python, SQL, DuckDB, Plotly, and a static browser layer.

Experiment Forge turns raw product event data into tested experiment marts, audits common experimentation failures, analyzes treatment impact, and gives a product manager a traceable launch / stop / continue / investigate decision.

Repository: [github.com/amlfarhad/experiment-forge](https://github.com/amlfarhad/experiment-forge)

## Platform Capabilities

Experimentation work needs a full data platform around the test:

- canonical exposure and assignment data;
- raw-to-staging warehouse models;
- reusable user-level and daily metric marts;
- sample ratio mismatch checks;
- duplicate and multi-variant assignment detection;
- temporal validity checks for events before assignment;
- guardrail metrics for engagement and support load;
- launch / stop / continue / investigate decisioning;
- readable reports, reproducible JSON artifacts, and a browser workflow.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 forge.py demo --workspace . --users 5000 --seed 42
```

The CLI demo writes raw CSVs, a local DuckDB warehouse, JSON analysis and quality artifacts, Markdown readouts, and the existing Plotly dashboard.

## Decision Desk

The browser product is a static, no-login interface backed by reproducibly generated JSON artifacts. It contains two deterministic workspaces:

- **Checkout progress indicator** — deliberately flawed. It has a positive-looking primary lift but fails critical assignment, temporal, and revenue-quality gates, so the product says **investigate**.
- **Search autocomplete refresh** — clean comparison sample. It uses the same generator, warehouse, quality audit, and statistical readout with injected source failures disabled, so the sample can demonstrate a **launch** decision.

Build and serve it locally:

```bash
python3 forge.py web-build --workspace . --output web/data --users 5000 --seed 42
python3 -m http.server 8000 --directory web
```

Open [http://localhost:8000](http://localhost:8000). The UI reads `web/data/catalog.json` and the experiment payloads generated from raw CSVs, DuckDB marts, the quality audit, and statistical analysis. The CSV panel validates documented headers locally; it does not upload private data or pretend to analyze it.

Deploy the static product from the repository root with Vercel:

```bash
vercel deploy web --prod -y
```

See [`docs/methodology.md`](docs/methodology.md), [`docs/data_lineage.md`](docs/data_lineage.md), and [`docs/limitations.md`](docs/limitations.md) for the evidence contract and boundaries.

## CLI

```bash
python3 forge.py generate-demo-data --workspace .
python3 forge.py build-warehouse --workspace .
python3 forge.py audit-experiment --workspace .
python3 forge.py analyze --workspace .
python3 forge.py report --workspace .
python3 forge.py demo --workspace .
python3 forge.py credit-risk-demo --workspace . --loans 6000 --seed 42
python3 forge.py web-build --workspace . --output web/data
```

## Platform Layers

| Layer | Purpose |
|---|---|
| `data_generation/` | Synthetic source systems for users, assignments, events, sessions, orders, exposures, support tickets, and daily snapshots |
| `warehouse/` | DuckDB raw, staging, intermediate, and mart models |
| `quality/` | Assignment, source, temporal, mart, and guardrail checks |
| `analysis/` | Statistical readout, practical significance, multiple-testing adjustment, and decision recommendation |
| `reporting/` | Markdown reports and Plotly HTML dashboard |
| `web_artifacts.py` | Runs the real pipeline and emits stable browser payloads |
| `web/` | Accessible static Decision Desk UI and committed sample artifacts |
| `credit_risk/` | Auto-finance PD, LGD, EAD, expected credit loss, and stress-scenario modeling |
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

Critical failures block launch and stop calls. Warnings stay visible in the readout.

## Statistical Modules

The original statistics toolkit is still included:

- Welch and Student t-tests;
- two-proportion z-tests;
- delta method ratio metrics;
- power analysis and MDE estimation;
- sequential testing;
- CUPED variance reduction;
- multiple testing correction;
- Bayesian A/B testing;
- multi-armed bandit simulations.

The Decision Desk uses a two-proportion primary test, a continuous secondary test, Holm-Bonferroni adjustment across that confirmatory family, and a 1% practical relative-lift threshold from the experiment registry.

## Credit Loss Forecasting

Experiment Forge also includes an auto-finance credit-risk workflow for portfolio loss forecasting:

- synthetic auto-loan origination and monthly performance data;
- borrower risk, loan term, LTV, APR, collateral, delinquency, and macroeconomic drivers;
- Probability of Default (PD), Loss Given Default (LGD), and Exposure at Default (EAD) models;
- Expected Credit Loss (ECL) scoring using PD x LGD x EAD;
- holdout validation with PD AUC, Brier score, LGD MAE, and EAD MAPE;
- stress scenario with unemployment, used-vehicle collateral, and rate shocks;
- model governance readout with assumptions, validation results, and high-loss segments.

## Reports

Sample generated artifacts:

- [`reports/sample_quality_audit.md`](reports/sample_quality_audit.md)
- [`reports/sample_experiment_readout.md`](reports/sample_experiment_readout.md)
- `reports/dashboard.html`

## Tests

```bash
python3 -m pytest tests --ignore=tests/browser -q
```

Browser regression tests use Playwright. Install the development dependency and browser once, then serve the repository root in another terminal:

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m playwright install chromium
python3 -m http.server 8766 --bind 127.0.0.1 --directory .
EXPERIMENT_FORGE_BASE_URL=http://127.0.0.1:8766 python3 -m pytest tests/browser -q
```

## Portfolio Summary

Built an experimentation decision product using Python, SQL, DuckDB, and browser-native rendering to generate product event data, model experiment metric marts, detect assignment and data-quality failures, expose uncertainty and guardrails, and produce traceable product decisions.
