"""Statistical power analysis and sample size calculation.

Before running any experiment, you need to answer:
"How many users do I need to detect an X% change with Y% confidence?"

Getting this wrong means either:
- Too few users → can't detect real effects (wasted experiment time)
- Too many users → unnecessarily delayed decisions (wasted opportunity cost)
"""

import numpy as np
from scipy import stats


def required_sample_size(
    baseline_rate,
    mde,
    alpha=0.05,
    power=0.80,
    two_sided=True,
    metric_type="proportion",
    baseline_std=None,
):
    """Calculate the minimum sample size per group for an A/B test.

    Args:
        baseline_rate: Baseline metric value (e.g., 0.05 for 5% CTR).
        mde: Minimum Detectable Effect as relative change (e.g., 0.10 for 10% lift).
        alpha: Type I error rate (false positive rate).
        power: 1 - Type II error rate (true positive rate).
        two_sided: Whether the test is two-sided.
        metric_type: 'proportion' or 'continuous'.
        baseline_std: Standard deviation (required for continuous metrics).

    Returns:
        Required sample size per group (integer).
    """
    z_alpha = stats.norm.ppf(1 - alpha / (2 if two_sided else 1))
    z_beta = stats.norm.ppf(power)

    if metric_type == "proportion":
        p1 = baseline_rate
        p2 = baseline_rate * (1 + mde)
        # Variance under H0 and H1
        var_h0 = p1 * (1 - p1) + p2 * (1 - p2)
        var_h1 = p1 * (1 - p1) + p2 * (1 - p2)
        n = (z_alpha * np.sqrt(var_h0) + z_beta * np.sqrt(var_h1)) ** 2 / (p2 - p1) ** 2

    elif metric_type == "continuous":
        if baseline_std is None:
            raise ValueError("baseline_std required for continuous metrics.")
        absolute_mde = baseline_rate * mde
        n = 2 * ((z_alpha + z_beta) * baseline_std / absolute_mde) ** 2

    else:
        raise ValueError(f"Unknown metric_type: {metric_type}")

    return int(np.ceil(n))


def compute_power(
    n_per_group,
    baseline_rate,
    mde,
    alpha=0.05,
    two_sided=True,
    metric_type="proportion",
    baseline_std=None,
):
    """Compute statistical power for a given sample size.

    Args:
        n_per_group: Sample size per group.
        baseline_rate: Baseline metric value.
        mde: Minimum Detectable Effect (relative).
        alpha: Significance level.
        two_sided: Two-sided test.
        metric_type: 'proportion' or 'continuous'.
        baseline_std: Std dev for continuous metrics.

    Returns:
        Statistical power (float between 0 and 1).
    """
    z_alpha = stats.norm.ppf(1 - alpha / (2 if two_sided else 1))

    if metric_type == "proportion":
        p1 = baseline_rate
        p2 = baseline_rate * (1 + mde)
        se = np.sqrt(p1 * (1 - p1) / n_per_group + p2 * (1 - p2) / n_per_group)

    elif metric_type == "continuous":
        if baseline_std is None:
            raise ValueError("baseline_std required for continuous metrics.")
        se = baseline_std * np.sqrt(2 / n_per_group)
        p2 = baseline_rate * (1 + mde)

    else:
        raise ValueError(f"Unknown metric_type: {metric_type}")

    absolute_effect = abs(baseline_rate * mde)
    z_effect = absolute_effect / se if se > 0 else 0

    power = 1 - stats.norm.cdf(z_alpha - z_effect)
    if two_sided:
        power += stats.norm.cdf(-z_alpha - z_effect)

    return power


def power_curve(baseline_rate, mde, alpha=0.05, metric_type="proportion",
                baseline_std=None, n_range=None):
    """Generate a power curve: power vs. sample size.

    Useful for understanding the sensitivity of your experiment design.

    Returns:
        Tuple of (sample_sizes, powers).
    """
    if n_range is None:
        # Estimate a reasonable range
        target_n = required_sample_size(baseline_rate, mde, alpha=alpha,
                                         metric_type=metric_type, baseline_std=baseline_std)
        n_range = np.linspace(max(10, target_n // 5), target_n * 2, 50).astype(int)

    powers = [
        compute_power(n, baseline_rate, mde, alpha, metric_type=metric_type,
                      baseline_std=baseline_std)
        for n in n_range
    ]

    return n_range, powers


def mde_for_sample_size(n_per_group, baseline_rate, alpha=0.05, power=0.80,
                        metric_type="proportion", baseline_std=None):
    """Given a fixed sample size, what's the smallest effect we can detect?

    This is the inverse question: "I have 100K users. What's my MDE?"

    Returns:
        Minimum Detectable Effect as relative change.
    """
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)

    if metric_type == "proportion":
        se = np.sqrt(2 * baseline_rate * (1 - baseline_rate) / n_per_group)
        absolute_mde = (z_alpha + z_beta) * se
        return absolute_mde / baseline_rate if baseline_rate > 0 else 0

    elif metric_type == "continuous":
        if baseline_std is None:
            raise ValueError("baseline_std required for continuous metrics.")
        se = baseline_std * np.sqrt(2 / n_per_group)
        absolute_mde = (z_alpha + z_beta) * se
        return absolute_mde / baseline_rate if baseline_rate > 0 else 0

    raise ValueError(f"Unknown metric_type: {metric_type}")
