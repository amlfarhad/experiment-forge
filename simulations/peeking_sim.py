"""Simulation: The Peeking Problem.

This simulation PROVES that continuously monitoring p-values and stopping
when p < 0.05 inflates the false positive rate from 5% to ~26%.

This is the #1 experimentation mistake at companies without proper tooling.
Every FAANG interview on experimentation will test whether you understand this.

How it works:
- Generate A/A tests (no real effect — both groups are identical)
- Check p-value at multiple points during the experiment
- If p < 0.05 at ANY point, declare "significant" and stop
- Count how many A/A tests we falsely declare significant
- Expected: 5%. Actual with peeking: ~26%.
"""

import numpy as np
from scipy import stats


def simulate_peeking(
    n_simulations=10000,
    n_samples_per_group=1000,
    n_peeks=20,
    alpha=0.05,
    seed=42,
):
    """Simulate the peeking problem.

    Args:
        n_simulations: Number of A/A tests to run.
        n_samples_per_group: Final sample size per group.
        n_peeks: Number of times we check the p-value.
        alpha: Significance threshold.
        seed: Random seed.

    Returns:
        Dict with false positive rates for peeking vs. fixed-horizon.
    """
    rng = np.random.RandomState(seed)
    peek_points = np.linspace(
        n_samples_per_group // n_peeks,
        n_samples_per_group,
        n_peeks,
    ).astype(int)

    peeking_false_positives = 0
    fixed_false_positives = 0
    first_significant_peek = []

    for _ in range(n_simulations):
        # Both groups drawn from the SAME distribution (no effect)
        control = rng.normal(100, 15, n_samples_per_group)
        treatment = rng.normal(100, 15, n_samples_per_group)

        # Peeking: check at each peek point
        found_significant = False
        for i, n in enumerate(peek_points):
            _, p = stats.ttest_ind(control[:n], treatment[:n])
            if p < alpha:
                peeking_false_positives += 1
                first_significant_peek.append(i + 1)
                found_significant = True
                break

        if not found_significant:
            first_significant_peek.append(None)

        # Fixed horizon: only check at the end
        _, p_final = stats.ttest_ind(control, treatment)
        if p_final < alpha:
            fixed_false_positives += 1

    peeking_fpr = peeking_false_positives / n_simulations
    fixed_fpr = fixed_false_positives / n_simulations

    early_stops = [p for p in first_significant_peek if p is not None]

    return {
        "n_simulations": n_simulations,
        "n_peeks": n_peeks,
        "alpha": alpha,
        "peeking_false_positive_rate": peeking_fpr,
        "fixed_horizon_false_positive_rate": fixed_fpr,
        "inflation_factor": peeking_fpr / alpha,
        "expected_fpr": alpha,
        "median_early_stop_peek": int(np.median(early_stops)) if early_stops else None,
        "interpretation": (
            f"With {n_peeks} peeks at α={alpha}:\n"
            f"  Fixed-horizon FPR: {fixed_fpr:.1%} (expected {alpha:.1%})\n"
            f"  Peeking FPR:       {peeking_fpr:.1%} (inflated {peeking_fpr/alpha:.1f}x)\n"
            f"\n"
            f"  Peeking inflates false positives by {peeking_fpr/alpha:.1f}x!\n"
            f"  Use sequential testing (core/sequential.py) to stop early safely."
        ),
    }


def simulate_peeking_varying_checks(n_simulations=5000, max_peeks=50, seed=42):
    """Show how FPR increases with the number of peeks.

    Returns:
        Tuple of (n_peeks_list, fpr_list) for plotting.
    """
    peek_counts = list(range(1, max_peeks + 1, 2))
    fprs = []

    for n_peeks in peek_counts:
        result = simulate_peeking(
            n_simulations=n_simulations,
            n_peeks=n_peeks,
            seed=seed,
        )
        fprs.append(result["peeking_false_positive_rate"])

    return peek_counts, fprs


if __name__ == "__main__":
    print("Running peeking simulation...\n")
    result = simulate_peeking(n_simulations=10000)
    print(result["interpretation"])
