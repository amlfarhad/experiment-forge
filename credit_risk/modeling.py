"""PD/LGD/EAD modeling and expected credit loss reporting."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm


FEATURES = [
    "fico",
    "debt_to_income",
    "loan_to_value",
    "apr",
    "term_months",
    "used_vehicle",
    "loan_age_months",
    "scheduled_balance",
    "unemployment_rate",
    "used_vehicle_price_index",
    "interest_rate_index",
]


@dataclass(frozen=True)
class CreditLossForecast:
    """Summary outputs from a credit loss model run."""

    pd_auc: float
    pd_brier: float
    lgd_mae: float
    ead_mape: float
    baseline_expected_loss: float
    stress_expected_loss: float
    stress_lift: float
    high_risk_segments: list[dict[str, float | str]]
    records_scored: int

    def to_dict(self) -> dict[str, object]:
        return {
            "pd_auc": round(self.pd_auc, 4),
            "pd_brier": round(self.pd_brier, 4),
            "lgd_mae": round(self.lgd_mae, 4),
            "ead_mape": round(self.ead_mape, 4),
            "baseline_expected_loss": round(self.baseline_expected_loss, 2),
            "stress_expected_loss": round(self.stress_expected_loss, 2),
            "stress_lift": round(self.stress_lift, 4),
            "high_risk_segments": self.high_risk_segments,
            "records_scored": self.records_scored,
        }


def _load_model_frame(raw_dir: Path) -> pd.DataFrame:
    loans = pd.read_csv(raw_dir / "auto_loans.csv")
    performance = pd.read_csv(raw_dir / "monthly_performance.csv")
    frame = performance.merge(loans, on="loan_id", how="left", validate="many_to_one")
    frame["defaulted"] = frame["defaulted"].astype(int)
    frame["loss_given_default_observed"] = frame["loss_given_default"].fillna(0)
    frame["exposure_at_default_observed"] = frame["exposure_at_default"].fillna(frame["scheduled_balance"])
    frame["fico_band"] = pd.cut(
        frame["fico"],
        bins=[0, 620, 680, 720, 850],
        labels=["subprime", "near_prime", "prime", "super_prime"],
        include_lowest=True,
    ).astype(str)
    return frame


def _design_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    X = frame[FEATURES].copy()
    return sm.add_constant(X, has_constant="add")


def _roc_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    positives = y_score[y_true == 1]
    negatives = y_score[y_true == 0]
    if len(positives) == 0 or len(negatives) == 0:
        return 0.5
    sample_limit = 250000
    pair_count = len(positives) * len(negatives)
    if pair_count > sample_limit:
        rng = np.random.default_rng(17)
        pos = rng.choice(positives, size=int(np.sqrt(sample_limit)), replace=True)
        neg = rng.choice(negatives, size=int(np.sqrt(sample_limit)), replace=True)
    else:
        pos = positives
        neg = negatives
    comparisons = (pos[:, None] > neg[None, :]).mean()
    ties = (pos[:, None] == neg[None, :]).mean()
    return float(comparisons + 0.5 * ties)


def _fit_pd_model(train: pd.DataFrame):
    X_train = _design_matrix(train)
    y_train = train["defaulted"]
    return sm.Logit(y_train, X_train).fit(disp=False, maxiter=250)


def _fit_lgd_model(train: pd.DataFrame):
    defaults = train[train["defaulted"] == 1].copy()
    X_train = _design_matrix(defaults)
    y_train = defaults["loss_given_default_observed"]
    return sm.OLS(y_train, X_train).fit()


def _fit_ead_model(train: pd.DataFrame):
    defaults = train[train["defaulted"] == 1].copy()
    X_train = _design_matrix(defaults)
    y_train = defaults["exposure_at_default_observed"]
    return sm.OLS(y_train, X_train).fit()


def _score_frame(frame: pd.DataFrame, pd_model, lgd_model, ead_model) -> pd.DataFrame:
    scored = frame.copy()
    X = _design_matrix(scored)
    scored["pd_forecast"] = np.clip(pd_model.predict(X), 0.001, 0.75)
    scored["lgd_forecast"] = np.clip(lgd_model.predict(X), 0.04, 0.95)
    scored["ead_forecast"] = np.clip(ead_model.predict(X), 500, scored["original_balance"])
    scored["expected_credit_loss"] = scored["pd_forecast"] * scored["lgd_forecast"] * scored["ead_forecast"]
    return scored


def _stress_scenario(frame: pd.DataFrame) -> pd.DataFrame:
    stressed = frame.copy()
    stressed["unemployment_rate"] = np.clip(stressed["unemployment_rate"] + 0.025, 0, 0.16)
    stressed["used_vehicle_price_index"] = np.clip(stressed["used_vehicle_price_index"] - 0.09, 0.65, 1.2)
    stressed["interest_rate_index"] = np.clip(stressed["interest_rate_index"] + 0.012, 0, 0.18)
    return stressed


def _segment_table(scored: pd.DataFrame) -> list[dict[str, float | str]]:
    grouped = (
        scored.groupby(["fico_band", "used_vehicle"], observed=True)
        .agg(
            loans=("loan_id", "nunique"),
            default_rate=("defaulted", "mean"),
            avg_pd=("pd_forecast", "mean"),
            avg_lgd=("lgd_forecast", "mean"),
            expected_loss=("expected_credit_loss", "sum"),
        )
        .reset_index()
        .sort_values("expected_loss", ascending=False)
        .head(5)
    )
    grouped["vehicle_type"] = np.where(grouped["used_vehicle"] == 1, "used", "new")
    return [
        {
            "fico_band": row["fico_band"],
            "vehicle_type": row["vehicle_type"],
            "loans": int(row["loans"]),
            "default_rate": round(float(row["default_rate"]), 4),
            "avg_pd": round(float(row["avg_pd"]), 4),
            "avg_lgd": round(float(row["avg_lgd"]), 4),
            "expected_loss": round(float(row["expected_loss"]), 2),
        }
        for _, row in grouped.iterrows()
    ]


def run_credit_loss_forecast(raw_dir: str | Path, reports_dir: str | Path) -> CreditLossForecast:
    """Train PD, LGD, and EAD models and write forecast artifacts."""

    raw_path = Path(raw_dir)
    report_path = Path(reports_dir)
    report_path.mkdir(parents=True, exist_ok=True)

    frame = _load_model_frame(raw_path)
    train = frame[frame["month"] <= 27].copy()
    holdout = frame[frame["month"] > 27].copy()

    pd_model = _fit_pd_model(train)
    lgd_model = _fit_lgd_model(train)
    ead_model = _fit_ead_model(train)

    scored = _score_frame(holdout, pd_model, lgd_model, ead_model)
    stressed = _score_frame(_stress_scenario(holdout), pd_model, lgd_model, ead_model)

    y_true = scored["defaulted"].to_numpy()
    y_score = scored["pd_forecast"].to_numpy()
    pd_auc = _roc_auc(y_true, y_score)
    pd_brier = float(np.mean((y_true - y_score) ** 2))

    default_holdout = scored[scored["defaulted"] == 1]
    lgd_mae = float(np.mean(np.abs(default_holdout["loss_given_default_observed"] - default_holdout["lgd_forecast"])))
    ead_mape = float(
        np.mean(
            np.abs(default_holdout["exposure_at_default_observed"] - default_holdout["ead_forecast"])
            / np.maximum(default_holdout["exposure_at_default_observed"], 1)
        )
    )
    baseline_expected_loss = float(scored["expected_credit_loss"].sum())
    stress_expected_loss = float(stressed["expected_credit_loss"].sum())
    stress_lift = float((stress_expected_loss / baseline_expected_loss) - 1)

    forecast = CreditLossForecast(
        pd_auc=pd_auc,
        pd_brier=pd_brier,
        lgd_mae=lgd_mae,
        ead_mape=ead_mape,
        baseline_expected_loss=baseline_expected_loss,
        stress_expected_loss=stress_expected_loss,
        stress_lift=stress_lift,
        high_risk_segments=_segment_table(scored),
        records_scored=len(scored),
    )

    scored[
        [
            "loan_id",
            "month",
            "fico_band",
            "used_vehicle",
            "scheduled_balance",
            "pd_forecast",
            "lgd_forecast",
            "ead_forecast",
            "expected_credit_loss",
            "defaulted",
        ]
    ].to_csv(report_path / "credit_loss_scored_holdout.csv", index=False)
    return forecast
