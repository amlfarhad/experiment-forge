"""Main entry point: run all simulations and demonstrations."""

import argparse
import numpy as np

from core.experiment import analyze_continuous, analyze_proportion
from core.power_analysis import required_sample_size, mde_for_sample_size
from core.sequential import SequentialTest
from core.multiple_testing import compare_corrections
from simulations.peeking_sim import simulate_peeking
from simulations.cuped_sim import simulate_cuped_benefit
from simulations.srm_sim import detect_srm, simulate_srm_scenarios
from advanced.bandits import (
    EpsilonGreedy, UCB1, ThompsonSampling, run_bandit_simulation
)
from advanced.bayesian import bayesian_proportion_test


def run_all_demos():
    """Run all experiment-forge demonstrations."""
    print("=" * 70)
    print("  experiment-forge — Statistical Experimentation Platform")
    print("=" * 70)

    # ── 1. Power Analysis ──────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  [1] POWER ANALYSIS")
    print("─" * 70)

    baseline_ctr = 0.05
    for mde in [0.05, 0.10, 0.20]:
        n = required_sample_size(baseline_ctr, mde)
        print(f"  Baseline CTR={baseline_ctr:.0%}, MDE={mde:.0%} → "
              f"Need {n:,} users/group ({n*2:,} total)")

    n_available = 100_000
    achievable_mde = mde_for_sample_size(n_available, baseline_ctr)
    print(f"\n  With {n_available:,} users/group, smallest detectable effect: {achievable_mde:.1%}")

    # ── 2. Experiment Analysis ─────────────────────────────────────
    print("\n" + "─" * 70)
    print("  [2] EXPERIMENT ANALYSIS")
    print("─" * 70)

    np.random.seed(42)
    control = np.random.normal(50, 10, 5000)
    treatment = np.random.normal(51, 10, 5000)

    result = analyze_continuous(control, treatment)
    print(f"\n{result}")

    print(f"\n  Proportion test example:")
    prop_result = analyze_proportion(500, 10000, 550, 10000)
    print(f"  {prop_result}")

    # ── 3. Peeking Problem ─────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  [3] PEEKING PROBLEM SIMULATION")
    print("─" * 70)

    peek_result = simulate_peeking(n_simulations=5000, n_peeks=20)
    print(f"\n{peek_result['interpretation']}")

    # ── 4. Sequential Testing ──────────────────────────────────────
    print("\n" + "─" * 70)
    print("  [4] SEQUENTIAL TESTING (Safe Early Stopping)")
    print("─" * 70)

    seq_test = SequentialTest(n_analyses=5, spending="obrien_fleming")
    print(f"\n  O'Brien-Fleming boundaries:\n{seq_test.get_boundaries_table()}")

    # ── 5. CUPED Variance Reduction ────────────────────────────────
    print("\n" + "─" * 70)
    print("  [5] CUPED VARIANCE REDUCTION")
    print("─" * 70)

    cuped_result = simulate_cuped_benefit(n_simulations=500)
    print(f"\n{cuped_result['interpretation']}")

    # ── 6. Multiple Testing Correction ─────────────────────────────
    print("\n" + "─" * 70)
    print("  [6] MULTIPLE TESTING CORRECTION")
    print("─" * 70)

    p_values = [0.001, 0.013, 0.029, 0.04, 0.049, 0.12, 0.31, 0.67]
    corrections = compare_corrections(p_values)
    print(f"\n  Raw p-values: {p_values}")
    for method, result in corrections.items():
        print(f"  {result['method']:30s} → {result['n_significant']} significant")

    # ── 7. SRM Detection ──────────────────────────────────────────
    print("\n" + "─" * 70)
    print("  [7] SAMPLE RATIO MISMATCH (SRM)")
    print("─" * 70)

    srm = detect_srm(49200, 50800)
    print(f"\n  {srm['interpretation']}")

    # ── 8. Multi-Armed Bandits ─────────────────────────────────────
    print("\n" + "─" * 70)
    print("  [8] MULTI-ARMED BANDITS")
    print("─" * 70)

    arm_probs = [0.05, 0.07, 0.10, 0.04]
    print(f"\n  True arm probabilities: {arm_probs}")
    print(f"  Best arm: {np.argmax(arm_probs)} (p={max(arm_probs)})\n")

    for BanditClass, name in [
        (lambda: EpsilonGreedy(4, epsilon=0.1), "ε-Greedy (ε=0.1)"),
        (lambda: UCB1(4), "UCB1"),
        (lambda: ThompsonSampling(4), "Thompson Sampling"),
    ]:
        bandit = BanditClass()
        result = run_bandit_simulation(bandit, arm_probs, n_rounds=10000)
        print(f"  {name:25s} | Regret: {result['final_regret']:.0f} | "
              f"Best arm chosen: {result['arm_counts'][np.argmax(arm_probs)]/sum(result['arm_counts']):.1%}")

    # ── 9. Bayesian A/B Test ───────────────────────────────────────
    print("\n" + "─" * 70)
    print("  [9] BAYESIAN A/B TEST")
    print("─" * 70)

    bayes = bayesian_proportion_test(500, 10000, 550, 10000)
    print(f"\n  P(treatment better): {bayes['prob_treatment_better']:.1%}")
    print(f"  Expected lift: {bayes['expected_lift']:.2%}")
    print(f"  Recommendation: {bayes['recommendation']}")

    print("\n" + "=" * 70)
    print("  All demonstrations complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="experiment-forge — Run all demos")
    parser.add_argument("--quick", action="store_true", help="Fewer simulations for speed")
    args = parser.parse_args()
    run_all_demos()
