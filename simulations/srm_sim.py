"""Simulation: Sample Ratio Mismatch (SRM) Detection.

Before analyzing ANY experiment, the first check should be: "Are the group
sizes what we expected?" If you randomized 50/50, are they actually 50/50?

If not, something went wrong — broken randomization, bot traffic, data pipeline
issues. Analyzing a broken experiment gives meaningless results.

SRM is the #1 diagnostic at Microsoft, Google, and every mature experimentation
platform. A chi-squared goodness-of-fit test detects it.

Reference: Fabijan et al., 2019 — "Diagnosing Sample Ratio Mismatch in
Online Controlled Experiments" (Microsoft)
"""

import numpy as np
from scipy import stats


def detect_srm(control_count, treatment_count, expected_ratio=0.5, alpha=0.001):
    """Detect Sample Ratio Mismatch using chi-squared test.

    Note: We use a very strict alpha (0.001) because SRM indicates a
    fundamental problem with the experiment — we want high certainty.

    Args:
        control_count: Number of users in control.
        treatment_count: Number of users in treatment.
        expected_ratio: Expected proportion in treatment (0.5 for 50/50).
        alpha: Significance level (default 0.001 — very strict).

    Returns:
        Dict with SRM detection result.
    """
    total = control_count + treatment_count
    observed = np.array([control_count, treatment_count])
    expected = np.array([total * (1 - expected_ratio), total * expected_ratio])

    chi2, p_value = stats.chisquare(observed, f_exp=expected)

    actual_ratio = treatment_count / total
    deviation = actual_ratio - expected_ratio

    return {
        "srm_detected": p_value < alpha,
        "p_value": p_value,
        "chi2_statistic": chi2,
        "control_count": control_count,
        "treatment_count": treatment_count,
        "actual_ratio": actual_ratio,
        "expected_ratio": expected_ratio,
        "deviation": deviation,
        "interpretation": (
            f"SRM {'DETECTED' if p_value < alpha else 'not detected'} "
            f"(p={p_value:.2e})\n"
            f"Expected ratio: {expected_ratio:.4f} | "
            f"Actual ratio: {actual_ratio:.4f} | "
            f"Deviation: {deviation:+.4f}"
        ),
    }


def simulate_srm_scenarios(n_simulations=5000, n_users=100000, seed=42):
    """Simulate various SRM scenarios and measure detection rates.

    Returns:
        Dict with detection rates for each scenario.
    """
    rng = np.random.RandomState(seed)
    scenarios = {
        "clean_50_50": {"true_ratio": 0.50, "expected": 0.50},
        "slight_imbalance": {"true_ratio": 0.505, "expected": 0.50},
        "moderate_imbalance": {"true_ratio": 0.52, "expected": 0.50},
        "severe_imbalance": {"true_ratio": 0.55, "expected": 0.50},
        "bot_traffic": {"true_ratio": 0.48, "expected": 0.50},
    }

    results = {}
    for name, params in scenarios.items():
        detections = 0
        for _ in range(n_simulations):
            treatment_count = rng.binomial(n_users, params["true_ratio"])
            control_count = n_users - treatment_count
            result = detect_srm(control_count, treatment_count, params["expected"])
            if result["srm_detected"]:
                detections += 1

        results[name] = {
            "true_ratio": params["true_ratio"],
            "detection_rate": detections / n_simulations,
            "expected_ratio": params["expected"],
        }

    return results


if __name__ == "__main__":
    print("Running SRM simulations...\n")

    print("Single test example:")
    result = detect_srm(49500, 50500)
    print(f"  {result['interpretation']}\n")

    print("Detection rates across scenarios:")
    scenarios = simulate_srm_scenarios(n_simulations=2000)
    for name, data in scenarios.items():
        print(f"  {name:25s} | true_ratio={data['true_ratio']:.3f} | "
              f"detection_rate={data['detection_rate']:.1%}")
