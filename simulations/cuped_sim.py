"""Simulation: CUPED Variance Reduction Benefit.

Demonstrates that CUPED can reduce required sample size by 40-50%
by leveraging pre-experiment user behavior as a covariate.

This simulation:
1. Generates realistic user data with pre/post experiment metrics
2. Runs the experiment with and without CUPED
3. Shows how CUPED narrows confidence intervals
4. Measures the effective sample size multiplier
"""

import numpy as np
from scipy import stats

from variance_reduction.cuped import cuped_experiment


def simulate_cuped_benefit(
    n_per_group=5000,
    true_effect=2.0,
    base_mean=100.0,
    base_std=30.0,
    pre_post_correlation=0.7,
    n_simulations=1000,
    alpha=0.05,
    seed=42,
):
    """Simulate experiments with and without CUPED.

    Args:
        n_per_group: Users per group.
        true_effect: True treatment effect (added to treatment mean).
        base_mean: Baseline metric mean.
        base_std: Baseline metric standard deviation.
        pre_post_correlation: Correlation between pre and post metrics.
            Higher = more variance reduction. 0.7 is typical for engagement metrics.
        n_simulations: Number of simulated experiments.
        alpha: Significance level.
        seed: Random seed.

    Returns:
        Dict with power comparison and variance reduction stats.
    """
    rng = np.random.RandomState(seed)

    standard_significant = 0
    cuped_significant = 0
    variance_reductions = []
    se_reductions = []

    for _ in range(n_simulations):
        # Generate correlated pre/post data
        # Using bivariate normal with specified correlation
        cov_matrix = [
            [base_std**2, pre_post_correlation * base_std**2],
            [pre_post_correlation * base_std**2, base_std**2],
        ]

        control_data = rng.multivariate_normal(
            [base_mean, base_mean], cov_matrix, n_per_group
        )
        treatment_data = rng.multivariate_normal(
            [base_mean, base_mean + true_effect], cov_matrix, n_per_group
        )

        control_pre = control_data[:, 0]
        control_post = control_data[:, 1]
        treatment_pre = treatment_data[:, 0]
        treatment_post = treatment_data[:, 1]

        result = cuped_experiment(
            control_post, control_pre,
            treatment_post, treatment_pre,
            alpha=alpha,
        )

        if result["standard"]["significant"]:
            standard_significant += 1
        if result["cuped"]["significant"]:
            cuped_significant += 1

        avg_vr = (
            result["cuped"]["variance_reduction_control"]
            + result["cuped"]["variance_reduction_treatment"]
        ) / 2
        variance_reductions.append(avg_vr)
        se_reductions.append(result["improvement"]["se_reduction"])

    standard_power = standard_significant / n_simulations
    cuped_power = cuped_significant / n_simulations
    avg_variance_reduction = np.mean(variance_reductions)
    avg_se_reduction = np.mean(se_reductions)

    # Effective sample size multiplier: how many more users would standard
    # analysis need to match CUPED's precision?
    effective_multiplier = 1 / (1 - avg_variance_reduction) if avg_variance_reduction < 1 else float("inf")

    return {
        "n_per_group": n_per_group,
        "true_effect": true_effect,
        "pre_post_correlation": pre_post_correlation,
        "n_simulations": n_simulations,
        "standard_power": standard_power,
        "cuped_power": cuped_power,
        "power_improvement": cuped_power - standard_power,
        "avg_variance_reduction": avg_variance_reduction,
        "avg_se_reduction": avg_se_reduction,
        "effective_sample_multiplier": effective_multiplier,
        "interpretation": (
            f"With pre/post correlation of {pre_post_correlation}:\n"
            f"  Standard power: {standard_power:.1%}\n"
            f"  CUPED power:    {cuped_power:.1%} (+{cuped_power - standard_power:.1%})\n"
            f"\n"
            f"  Variance reduction: {avg_variance_reduction:.1%}\n"
            f"  SE reduction:       {avg_se_reduction:.1%}\n"
            f"  Effective sample multiplier: {effective_multiplier:.1f}x\n"
            f"\n"
            f"  CUPED makes {n_per_group:,} users as powerful as "
            f"{int(n_per_group * effective_multiplier):,} users without CUPED."
        ),
    }


def cuped_sensitivity_to_correlation(n_per_group=5000, n_simulations=500, seed=42):
    """Show how CUPED benefit depends on pre/post correlation.

    Returns:
        Tuple of (correlations, variance_reductions, power_gains).
    """
    correlations = np.arange(0.0, 1.0, 0.1)
    variance_reductions = []
    power_gains = []

    for corr in correlations:
        result = simulate_cuped_benefit(
            n_per_group=n_per_group,
            pre_post_correlation=corr,
            n_simulations=n_simulations,
            seed=seed,
        )
        variance_reductions.append(result["avg_variance_reduction"])
        power_gains.append(result["power_improvement"])

    return correlations.tolist(), variance_reductions, power_gains


if __name__ == "__main__":
    print("Running CUPED simulation...\n")
    result = simulate_cuped_benefit()
    print(result["interpretation"])
