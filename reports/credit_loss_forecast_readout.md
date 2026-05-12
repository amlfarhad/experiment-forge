# Credit Loss Forecast Readout

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
| Holdout records scored | 54,000 |
| PD AUC | 0.757 |
| PD Brier score | 0.0132 |
| LGD MAE | 0.067 |
| EAD MAPE | 0.000 |

## Forecast Summary

| Scenario | Expected credit loss |
|---|---:|
| Baseline | $6,673,263 |
| Stressed macro | $9,854,389 |
| Stress lift | 47.7% |

## Highest-Loss Segments

| FICO band | Vehicle type | Loans | Avg PD | Avg LGD | Expected loss |
|---|---:|---:|---:|---:|---:|
| subprime | used | 533 | 4.62% | 51.27% | $2,303,008 |
| near_prime | used | 732 | 2.05% | 51.34% | $1,443,010 |
| subprime | new | 483 | 2.16% | 36.93% | $692,216 |
| near_prime | new | 911 | 1.04% | 37.55% | $670,419 |
| prime | used | 515 | 1.14% | 51.35% | $544,132 |

## Governance Notes

- Uses a deterministic train/holdout split by observation month to avoid look-ahead leakage.
- Separates PD, LGD, and EAD so model performance and business assumptions can be reviewed independently.
- Writes scored holdout records for challenger-model comparison, audit review, and portfolio monitoring.
- Keeps stress assumptions explicit so Risk, Finance, and business partners can challenge or replace them.
