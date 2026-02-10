"""Stratified estimation for variance reduction.

When users have very different baseline behaviors (e.g., power users vs. casual),
the variance of your metric is inflated. Stratified estimation accounts for this
by estimating the treatment effect within each stratum and combining them.

This is simpler than CUPED but still effective, especially when you have
clear categorical segments (country, platform, user tier).
"""

import numpy as np
from scipy import stats


def stratified_mean(values, strata, weights=None):
    """Compute stratified mean estimate.

    Args:
        values: Array of metric values.
        strata: Array of stratum labels (same length as values).
        weights: Optional dict mapping stratum -> weight.
                 If None, uses proportion of total population.

    Returns:
        Dict with stratified mean, variance, and per-stratum stats.
    """
    values = np.asarray(values, dtype=float)
    strata = np.asarray(strata)

    unique_strata = np.unique(strata)
    n_total = len(values)

    stratum_stats = {}
    for s in unique_strata:
        mask = strata == s
        s_values = values[mask]
        stratum_stats[s] = {
            "mean": s_values.mean(),
            "var": s_values.var(ddof=1) if len(s_values) > 1 else 0,
            "n": len(s_values),
            "proportion": len(s_values) / n_total,
        }

    if weights is None:
        weights = {s: stats["proportion"] for s, stats in stratum_stats.items()}

    # Stratified mean: Σ w_s * mean_s
    strat_mean = sum(weights[s] * stratum_stats[s]["mean"] for s in unique_strata)

    # Stratified variance: Σ w_s² * var_s / n_s
    strat_var = sum(
        weights[s] ** 2 * stratum_stats[s]["var"] / stratum_stats[s]["n"]
        for s in unique_strata
        if stratum_stats[s]["n"] > 0
    )

    return {
        "stratified_mean": strat_mean,
        "stratified_variance": strat_var,
        "stratified_se": np.sqrt(strat_var),
        "simple_mean": values.mean(),
        "simple_variance": values.var(ddof=1) / n_total,
        "stratum_stats": stratum_stats,
    }


def stratified_experiment(control_values, control_strata,
                          treatment_values, treatment_strata,
                          alpha=0.05):
    """Run a stratified experiment analysis.

    Args:
        control_values: Control group metric values.
        control_strata: Control group stratum labels.
        treatment_values: Treatment group metric values.
        treatment_strata: Treatment group stratum labels.
        alpha: Significance level.

    Returns:
        Dict comparing simple vs. stratified analysis.
    """
    ctrl = stratified_mean(control_values, control_strata)
    treat = stratified_mean(treatment_values, treatment_strata)

    # Simple analysis
    simple_diff = np.mean(treatment_values) - np.mean(control_values)
    simple_se = np.sqrt(
        np.var(control_values, ddof=1) / len(control_values)
        + np.var(treatment_values, ddof=1) / len(treatment_values)
    )
    simple_z = simple_diff / simple_se if simple_se > 0 else 0
    simple_p = 2 * (1 - stats.norm.cdf(abs(simple_z)))

    # Stratified analysis
    strat_diff = treat["stratified_mean"] - ctrl["stratified_mean"]
    strat_se = np.sqrt(ctrl["stratified_variance"] + treat["stratified_variance"])
    strat_z = strat_diff / strat_se if strat_se > 0 else 0
    strat_p = 2 * (1 - stats.norm.cdf(abs(strat_z)))

    z_crit = stats.norm.ppf(1 - alpha / 2)

    return {
        "simple": {
            "difference": simple_diff,
            "se": simple_se,
            "z": simple_z,
            "p_value": simple_p,
            "significant": simple_p < alpha,
        },
        "stratified": {
            "difference": strat_diff,
            "se": strat_se,
            "z": strat_z,
            "p_value": strat_p,
            "significant": strat_p < alpha,
        },
        "se_reduction": 1 - strat_se / simple_se if simple_se > 0 else 0,
    }
