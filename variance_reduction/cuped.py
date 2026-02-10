"""CUPED — Controlled-experiment Using Pre-Experiment Data.

The single most impactful technique in modern experimentation.
Used at Microsoft, Netflix, Meta, Uber, and practically every FAANG company.

The idea: if you know what a user's metric looked like BEFORE the experiment,
you can use that as a covariate to reduce variance in the experiment metric.
This lets you detect smaller effects with the same sample size (or the same
effects with 40-50% fewer users).

Reference: Deng et al., 2013 — "Improving the Sensitivity of Online
Controlled Experiments by Utilizing Pre-Experiment Data" (Microsoft)
"""

import numpy as np
from scipy import stats


def cuped_adjust(metric_values, pre_experiment_values):
    """Apply CUPED variance reduction to experiment metric values.

    The adjusted metric is: Y_adjusted = Y - θ * (X - E[X])
    where θ = Cov(Y, X) / Var(X) and X is the pre-experiment covariate.

    Args:
        metric_values: Array of experiment metric values (Y).
        pre_experiment_values: Array of pre-experiment covariate values (X).

    Returns:
        Dict with adjusted values, theta, variance reduction fraction.
    """
    Y = np.asarray(metric_values, dtype=float)
    X = np.asarray(pre_experiment_values, dtype=float)

    if len(Y) != len(X):
        raise ValueError("metric_values and pre_experiment_values must have the same length.")

    # Compute optimal theta (regression coefficient)
    cov_xy = np.cov(Y, X, ddof=1)[0, 1]
    var_x = np.var(X, ddof=1)

    if var_x == 0:
        return {
            "adjusted_values": Y,
            "theta": 0.0,
            "variance_reduction": 0.0,
            "original_variance": np.var(Y, ddof=1),
            "adjusted_variance": np.var(Y, ddof=1),
        }

    theta = cov_xy / var_x

    # Adjusted metric
    Y_adjusted = Y - theta * (X - X.mean())

    original_var = np.var(Y, ddof=1)
    adjusted_var = np.var(Y_adjusted, ddof=1)
    reduction = 1 - adjusted_var / original_var if original_var > 0 else 0

    return {
        "adjusted_values": Y_adjusted,
        "theta": theta,
        "variance_reduction": reduction,
        "original_variance": original_var,
        "adjusted_variance": adjusted_var,
    }


def cuped_experiment(control_metric, control_pre, treatment_metric, treatment_pre,
                     alpha=0.05):
    """Run a CUPED-adjusted experiment analysis.

    Args:
        control_metric: Control group experiment metric values.
        control_pre: Control group pre-experiment covariate values.
        treatment_metric: Treatment group experiment metric values.
        treatment_pre: Treatment group pre-experiment covariate values.
        alpha: Significance level.

    Returns:
        Dict comparing standard vs. CUPED-adjusted analysis.
    """
    # Standard analysis (no CUPED)
    ctrl = np.asarray(control_metric, dtype=float)
    treat = np.asarray(treatment_metric, dtype=float)

    std_diff = treat.mean() - ctrl.mean()
    std_se = np.sqrt(ctrl.var(ddof=1) / len(ctrl) + treat.var(ddof=1) / len(treat))
    std_z = std_diff / std_se if std_se > 0 else 0
    std_p = 2 * (1 - stats.norm.cdf(abs(std_z)))

    # CUPED-adjusted analysis
    ctrl_adj = cuped_adjust(control_metric, control_pre)
    treat_adj = cuped_adjust(treatment_metric, treatment_pre)

    ctrl_values = ctrl_adj["adjusted_values"]
    treat_values = treat_adj["adjusted_values"]

    adj_diff = treat_values.mean() - ctrl_values.mean()
    adj_se = np.sqrt(
        ctrl_values.var(ddof=1) / len(ctrl_values)
        + treat_values.var(ddof=1) / len(treat_values)
    )
    adj_z = adj_diff / adj_se if adj_se > 0 else 0
    adj_p = 2 * (1 - stats.norm.cdf(abs(adj_z)))

    z_crit = stats.norm.ppf(1 - alpha / 2)

    return {
        "standard": {
            "difference": std_diff,
            "standard_error": std_se,
            "z_statistic": std_z,
            "p_value": std_p,
            "ci_lower": std_diff - z_crit * std_se,
            "ci_upper": std_diff + z_crit * std_se,
            "significant": std_p < alpha,
        },
        "cuped": {
            "difference": adj_diff,
            "standard_error": adj_se,
            "z_statistic": adj_z,
            "p_value": adj_p,
            "ci_lower": adj_diff - z_crit * adj_se,
            "ci_upper": adj_diff + z_crit * adj_se,
            "significant": adj_p < alpha,
            "variance_reduction_control": ctrl_adj["variance_reduction"],
            "variance_reduction_treatment": treat_adj["variance_reduction"],
        },
        "improvement": {
            "se_reduction": 1 - adj_se / std_se if std_se > 0 else 0,
            "effective_sample_multiplier": (std_se / adj_se) ** 2 if adj_se > 0 else 1,
        },
    }
