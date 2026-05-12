"""Synthetic auto-loan portfolio generation for credit loss modeling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CreditDataManifest:
    """Paths written by the synthetic auto-loan generator."""

    loans_path: Path
    performance_path: Path
    macro_path: Path


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-values))


def generate_auto_loan_portfolio(output_dir: str | Path, seed: int = 42, n_loans: int = 6000) -> CreditDataManifest:
    """Generate a deterministic auto-finance portfolio with borrower, loan, and macro drivers.

    The generated data intentionally mirrors credit-loss modeling inputs rather than generic
    classification data: origination risk, term, LTV, FICO band, utilization, unemployment,
    used/new vehicle flags, recovery outcomes, and monthly exposure at default.
    """

    rng = np.random.default_rng(seed)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    loan_ids = np.arange(1, n_loans + 1)
    fico = np.clip(rng.normal(690, 72, n_loans).round(), 520, 840).astype(int)
    borrower_income = np.clip(rng.lognormal(mean=10.9, sigma=0.42, size=n_loans), 26000, 180000)
    debt_to_income = np.clip(rng.beta(2.3, 5.6, n_loans) + rng.normal(0, 0.025, n_loans), 0.08, 0.64)
    ltv = np.clip(rng.normal(0.88, 0.16, n_loans), 0.45, 1.35)
    apr = np.clip(0.035 + (760 - fico) * 0.00032 + (ltv - 0.8) * 0.025 + rng.normal(0, 0.01, n_loans), 0.025, 0.24)
    original_balance = np.clip(rng.normal(31500, 9300, n_loans), 8500, 76000).round(2)
    term_months = rng.choice([48, 60, 72, 84], size=n_loans, p=[0.16, 0.44, 0.34, 0.06])
    used_vehicle = rng.binomial(1, p=np.clip(0.35 + (720 - fico) / 900, 0.22, 0.62), size=n_loans)
    channel = rng.choice(["dealer", "direct", "refinance"], size=n_loans, p=[0.68, 0.19, 0.13])
    origination_month = rng.integers(1, 25, n_loans)

    loans = pd.DataFrame(
        {
            "loan_id": loan_ids,
            "origination_month": origination_month,
            "fico": fico,
            "borrower_income": borrower_income.round(2),
            "debt_to_income": debt_to_income.round(4),
            "loan_to_value": ltv.round(4),
            "apr": apr.round(4),
            "original_balance": original_balance,
            "term_months": term_months,
            "used_vehicle": used_vehicle,
            "channel": channel,
        }
    )

    months = np.arange(1, 37)
    unemployment = 0.036 + 0.0008 * months + 0.012 * np.sin(months / 6) + rng.normal(0, 0.002, len(months))
    used_vehicle_price_index = 1.02 - 0.0045 * months + 0.025 * np.sin(months / 5)
    interest_rate_index = 0.044 + 0.0012 * months + rng.normal(0, 0.0025, len(months))
    macro = pd.DataFrame(
        {
            "month": months,
            "unemployment_rate": np.clip(unemployment, 0.025, 0.09).round(4),
            "used_vehicle_price_index": used_vehicle_price_index.round(4),
            "interest_rate_index": np.clip(interest_rate_index, 0.025, 0.1).round(4),
        }
    )

    panel_frames = []
    for month in months:
        active = loans[loans["origination_month"] <= month].copy()
        if active.empty:
            continue
        age = month - active["origination_month"] + 1
        amortization = np.clip(age / active["term_months"], 0, 0.96)
        scheduled_balance = active["original_balance"] * (1 - amortization**0.92)
        macro_row = macro.loc[macro["month"] == month].iloc[0]

        logit = (
            -5.15
            + (660 - active["fico"]) / 95
            + 2.25 * (active["debt_to_income"] - 0.28)
            + 1.55 * (active["loan_to_value"] - 0.88)
            + 0.75 * active["used_vehicle"]
            + 16.0 * (macro_row["unemployment_rate"] - 0.045)
            + 0.95 * (active["apr"] - 0.08)
            + 0.014 * age
        )
        default_probability = np.clip(_sigmoid(logit), 0.002, 0.38)
        defaulted = rng.binomial(1, default_probability)

        delinquency_probability = np.clip(default_probability * 2.8 + 0.015, 0.02, 0.55)
        days_past_due = rng.choice([0, 15, 30, 60, 90], size=len(active), p=[0.79, 0.09, 0.06, 0.04, 0.02])
        delinquent = rng.binomial(1, delinquency_probability)
        days_past_due = np.where(delinquent == 1, days_past_due, 0)

        collateral_stress = np.clip(1.05 - macro_row["used_vehicle_price_index"], -0.04, 0.24)
        lgd = np.clip(
            0.28
            + 0.34 * (active["loan_to_value"] - 0.8)
            + 0.15 * active["used_vehicle"]
            + 0.42 * collateral_stress
            + rng.normal(0, 0.08, len(active)),
            0.05,
            0.92,
        )
        ead = np.clip(scheduled_balance * (1 + 0.03 * (days_past_due >= 60)), 500, active["original_balance"])

        panel_frames.append(
            pd.DataFrame(
                {
                    "loan_id": active["loan_id"].to_numpy(),
                    "month": month,
                    "loan_age_months": age.to_numpy(),
                    "scheduled_balance": scheduled_balance.round(2).to_numpy(),
                    "days_past_due": days_past_due,
                    "defaulted": defaulted,
                    "loss_given_default": np.where(defaulted == 1, lgd.round(4), np.nan),
                    "exposure_at_default": np.where(defaulted == 1, ead.round(2), np.nan),
                    "unemployment_rate": macro_row["unemployment_rate"],
                    "used_vehicle_price_index": macro_row["used_vehicle_price_index"],
                    "interest_rate_index": macro_row["interest_rate_index"],
                }
            )
        )

    performance = pd.concat(panel_frames, ignore_index=True)

    loans_path = output_path / "auto_loans.csv"
    performance_path = output_path / "monthly_performance.csv"
    macro_path = output_path / "macro_scenarios.csv"
    loans.to_csv(loans_path, index=False)
    performance.to_csv(performance_path, index=False)
    macro.to_csv(macro_path, index=False)
    return CreditDataManifest(loans_path=loans_path, performance_path=performance_path, macro_path=macro_path)
