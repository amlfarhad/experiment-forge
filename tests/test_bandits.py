"""Tests for multi-armed bandit algorithms."""

import pytest
import numpy as np

from advanced.bandits import (
    EpsilonGreedy, UCB1, ThompsonSampling, run_bandit_simulation
)


class TestEpsilonGreedy:

    def test_initialization(self):
        bandit = EpsilonGreedy(3, epsilon=0.1)
        assert bandit.n_arms == 3
        assert bandit.epsilon == 0.1
        assert all(c == 0 for c in bandit.counts)

    def test_update(self):
        bandit = EpsilonGreedy(2)
        bandit.update(0, 1.0)
        bandit.update(0, 0.0)
        assert bandit.counts[0] == 2
        assert bandit.values[0] == 0.5

    def test_exploitation(self):
        """With epsilon=0, should always pick the best known arm."""
        bandit = EpsilonGreedy(3, epsilon=0.0)
        bandit.update(0, 0.5)
        bandit.update(1, 0.9)
        bandit.update(2, 0.1)

        # Should always pick arm 1
        for _ in range(100):
            assert bandit.select_arm() == 1


class TestUCB1:

    def test_explores_all_arms_first(self):
        bandit = UCB1(3)
        arms_selected = set()
        for _ in range(3):
            arm = bandit.select_arm()
            arms_selected.add(arm)
            bandit.update(arm, 0.5)
        assert arms_selected == {0, 1, 2}

    def test_converges_to_best_arm(self):
        np.random.seed(42)
        arm_probs = [0.1, 0.5, 0.2]
        bandit = UCB1(3)
        result = run_bandit_simulation(bandit, arm_probs, n_rounds=5000)
        # Should mostly pull arm 1
        assert result["chosen_arm"] == 1


class TestThompsonSampling:

    def test_initialization(self):
        bandit = ThompsonSampling(4)
        assert all(a == 1 for a in bandit.alpha)
        assert all(b == 1 for b in bandit.beta)

    def test_update_success(self):
        bandit = ThompsonSampling(2)
        bandit.update(0, 1)
        assert bandit.alpha[0] == 2
        assert bandit.beta[0] == 1

    def test_update_failure(self):
        bandit = ThompsonSampling(2)
        bandit.update(0, 0)
        assert bandit.alpha[0] == 1
        assert bandit.beta[0] == 2

    def test_converges_to_best(self):
        np.random.seed(42)
        arm_probs = [0.05, 0.08, 0.12, 0.03]
        bandit = ThompsonSampling(4)
        result = run_bandit_simulation(bandit, arm_probs, n_rounds=10000)
        assert result["chosen_arm"] == 2  # Best arm

    def test_posteriors(self):
        bandit = ThompsonSampling(2)
        for _ in range(10):
            bandit.update(0, 1)
        for _ in range(10):
            bandit.update(1, 0)

        posteriors = bandit.get_posteriors()
        assert posteriors[0]["mean"] > posteriors[1]["mean"]


class TestBanditSimulation:

    def test_regret_increases(self):
        np.random.seed(42)
        bandit = EpsilonGreedy(2, epsilon=0.1)
        result = run_bandit_simulation(bandit, [0.3, 0.5], n_rounds=1000)
        # Cumulative regret should be monotonically increasing
        regret = result["cumulative_regret"]
        assert all(regret[i] <= regret[i + 1] for i in range(len(regret) - 1))

    def test_thompson_beats_random(self):
        """Thompson Sampling should have lower regret than pure exploration."""
        np.random.seed(42)
        arm_probs = [0.1, 0.3, 0.5]

        ts = ThompsonSampling(3)
        ts_result = run_bandit_simulation(ts, arm_probs, n_rounds=5000)

        random_bandit = EpsilonGreedy(3, epsilon=1.0)  # Pure random
        random_result = run_bandit_simulation(random_bandit, arm_probs, n_rounds=5000)

        assert ts_result["final_regret"] < random_result["final_regret"]
