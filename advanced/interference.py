"""Network interference detection in experiments.

The fundamental assumption of A/B testing: one user's treatment assignment
doesn't affect another user's outcome (SUTVA — Stable Unit Treatment Value
Assumption). This BREAKS in networked products:

- Social networks: If user A gets a new feature and shares content with
  user B (in control), B's engagement changes because of A's treatment.
- Marketplaces: If treatment sellers lower prices, control sellers lose
  customers — the control group is contaminated.
- Ride-sharing: Surge pricing in one zone affects driver supply in adjacent zones.

This module detects and quantifies interference effects.
"""

import numpy as np
from scipy import stats


def detect_interference_spillover(
    control_metric,
    treatment_metric,
    control_exposure_to_treatment,
    threshold_percentile=75,
):
    """Detect spillover effects by comparing control users with high vs. low
    exposure to treated users.

    If control users who are "close to" treatment users behave differently
    from control users who are "far from" treatment users, interference exists.

    Args:
        control_metric: Metric values for control group users.
        treatment_metric: Metric values for treatment group users.
        control_exposure_to_treatment: For each control user, a measure of
            how many of their neighbors are in the treatment group.
        threshold_percentile: Split control into high/low exposure groups.

    Returns:
        Dict with interference test results.
    """
    control_metric = np.asarray(control_metric, dtype=float)
    exposure = np.asarray(control_exposure_to_treatment, dtype=float)

    threshold = np.percentile(exposure, threshold_percentile)

    high_exposure = control_metric[exposure >= threshold]
    low_exposure = control_metric[exposure < threshold]

    if len(high_exposure) < 2 or len(low_exposure) < 2:
        return {
            "interference_detected": False,
            "error": "Insufficient data in one or both exposure groups.",
        }

    t_stat, p_value = stats.ttest_ind(high_exposure, low_exposure, equal_var=False)

    return {
        "interference_detected": p_value < 0.05,
        "p_value": p_value,
        "t_statistic": t_stat,
        "high_exposure_mean": high_exposure.mean(),
        "low_exposure_mean": low_exposure.mean(),
        "difference": high_exposure.mean() - low_exposure.mean(),
        "n_high_exposure": len(high_exposure),
        "n_low_exposure": len(low_exposure),
        "threshold": threshold,
        "interpretation": (
            "INTERFERENCE DETECTED: Control users with high exposure to "
            "treatment users show significantly different outcomes. "
            "Standard A/B test estimates may be biased."
            if p_value < 0.05 else
            "No significant interference detected."
        ),
    }


def simulate_network_experiment(
    n_users=10000,
    n_edges_per_user=20,
    base_rate=0.10,
    true_direct_effect=0.02,
    spillover_strength=0.5,
    treatment_fraction=0.5,
    seed=42,
):
    """Simulate an A/B test with network interference.

    Demonstrates how naive A/B testing underestimates treatment effects
    when spillover exists.

    Args:
        n_users: Total users in the experiment.
        n_edges_per_user: Average connections per user.
        base_rate: Baseline conversion rate.
        true_direct_effect: Direct treatment effect on conversion.
        spillover_strength: Fraction of direct effect that spills to neighbors.
        treatment_fraction: Fraction assigned to treatment.
        seed: Random seed.

    Returns:
        Dict with naive estimate, true effect, and bias.
    """
    rng = np.random.RandomState(seed)

    # Assign treatment
    is_treatment = rng.random(n_users) < treatment_fraction

    # Generate random network (simplified)
    treatment_neighbor_fraction = np.zeros(n_users)
    for i in range(n_users):
        n_neighbors = rng.poisson(n_edges_per_user)
        neighbors = rng.choice(n_users, size=min(n_neighbors, n_users - 1), replace=False)
        if len(neighbors) > 0:
            treatment_neighbor_fraction[i] = is_treatment[neighbors].mean()

    # Generate outcomes with spillover
    spillover_effect = spillover_strength * true_direct_effect * treatment_neighbor_fraction
    direct_effect = np.where(is_treatment, true_direct_effect, 0)
    conversion_prob = base_rate + direct_effect + spillover_effect
    conversion_prob = np.clip(conversion_prob, 0, 1)
    outcomes = rng.random(n_users) < conversion_prob

    # Naive estimate (ignores spillover)
    control_rate = outcomes[~is_treatment].mean()
    treatment_rate = outcomes[is_treatment].mean()
    naive_estimate = treatment_rate - control_rate

    # True total effect (direct + average spillover)
    avg_spillover = spillover_effect.mean()
    true_total_effect = true_direct_effect + avg_spillover

    return {
        "naive_estimate": naive_estimate,
        "true_direct_effect": true_direct_effect,
        "true_total_effect": true_total_effect,
        "bias": naive_estimate - true_direct_effect,
        "bias_fraction": (naive_estimate - true_direct_effect) / true_direct_effect if true_direct_effect != 0 else 0,
        "control_rate": control_rate,
        "treatment_rate": treatment_rate,
        "avg_spillover_on_control": spillover_effect[~is_treatment].mean(),
        "interpretation": (
            f"Naive A/B estimate: {naive_estimate:.4f}\n"
            f"True direct effect: {true_direct_effect:.4f}\n"
            f"Spillover inflates control by {spillover_effect[~is_treatment].mean():.4f}, "
            f"causing the naive estimate to UNDERESTIMATE the true effect by "
            f"{abs(naive_estimate - true_direct_effect) / true_direct_effect:.1%}"
        ),
    }
