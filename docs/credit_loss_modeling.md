# Credit Loss Modeling

The credit-risk workflow extends Experiment Forge from product experimentation into auto-finance portfolio forecasting. It is designed around the model components used in credit loss analysis: Probability of Default (PD), Loss Given Default (LGD), Exposure at Default (EAD), and Expected Credit Loss (ECL).

## Workflow

```bash
python3 forge.py credit-risk-demo --workspace . --loans 6000 --seed 42
```

The command generates a synthetic auto-loan portfolio, trains model components, scores a holdout period, applies a stressed macro scenario, and writes governance-ready artifacts.

## Inputs

- Borrower attributes: FICO, income, debt-to-income, and vehicle type
- Loan attributes: original balance, APR, term, LTV, origination month, and channel
- Performance attributes: loan age, scheduled balance, delinquency state, default flag, observed LGD, and observed EAD
- Macro drivers: unemployment, used-vehicle price index, and interest-rate index

## Model Components

| Component | Method | Review metric |
|---|---|---|
| PD | Logistic regression | AUC and Brier score |
| LGD | Regression on defaulted accounts | Mean absolute error |
| EAD | Regression on defaulted-account balances | Mean absolute percentage error |
| ECL | PD x LGD x EAD | Portfolio expected loss |

## Scenario Design

The stress scenario is intentionally explicit:

- unemployment rate increases by 250 basis points
- used-vehicle collateral index declines by 9%
- interest-rate index increases by 120 basis points

Keeping these assumptions separate from the model lets Risk, Finance, and business partners challenge the macro scenario without rewriting the model pipeline.

## Governance Choices

- The train/holdout split uses observation month to avoid look-ahead leakage.
- PD, LGD, and EAD are modeled separately so performance and assumptions can be reviewed independently.
- The scored holdout file supports challenger-model comparison and portfolio monitoring.
- The readout separates model validation from business interpretation.

## Sample Results

The checked-in sample readout reports a PD AUC of 0.757, a baseline expected credit loss of $6.7M, and a stressed expected credit loss of $9.9M across 54,000 holdout loan-month records.
