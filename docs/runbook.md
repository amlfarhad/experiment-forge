# Runbook

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Full Demo

```bash
python3 forge.py demo --workspace . --users 5000 --seed 42
```

This creates:

- `data/sample/*.csv`
- `data/warehouse/experiment_forge.duckdb`
- `reports/quality_audit.json`
- `reports/analysis.json`
- `reports/sample_quality_audit.md`
- `reports/sample_experiment_readout.md`
- `reports/dashboard.html`

## Individual Commands

```bash
python3 forge.py generate-demo-data --workspace .
python3 forge.py build-warehouse --workspace .
python3 forge.py audit-experiment --workspace .
python3 forge.py analyze --workspace .
python3 forge.py report --workspace .
```

## Verification

```bash
python3 -m pytest tests -q
python3 forge.py demo --workspace /tmp/experiment-forge-smoke --users 1000 --seed 42
```
