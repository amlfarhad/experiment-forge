"""Multi-Armed Bandit algorithms for adaptive experimentation.

A/B tests allocate traffic 50/50 regardless of early results. If treatment B
is clearly winning after day 1, you still serve the worse experience to 50%
of users for the full experiment duration.

Bandits adaptively shift traffic toward the winning variant, reducing
"regret" (the cost of showing a worse experience). The tradeoff: bandits
are harder to analyze statistically and may take longer to converge.

When to use bandits vs. A/B tests:
- A/B test: You need a rigorous causal estimate of the treatment effect
- Bandit: You need to minimize user exposure to the worse variant (e.g.,
  testing ad creatives, UI copy, recommendation algorithms)
"""

import numpy as np


class EpsilonGreedy:
    """Epsilon-greedy bandit: explore with probability ε, exploit otherwise.

    Simple but effective. The main limitation is that ε is fixed — it doesn't
    decrease as you gain confidence.
    """

    def __init__(self, n_arms, epsilon=0.1):
        self.n_arms = n_arms
        self.epsilon = epsilon
        self.counts = np.zeros(n_arms)
        self.values = np.zeros(n_arms)
        self.total_reward = 0.0
        self.history = []

    def select_arm(self):
        if np.random.random() < self.epsilon:
            return np.random.randint(self.n_arms)
        return int(np.argmax(self.values))

    def update(self, arm, reward):
        self.counts[arm] += 1
        self.total_reward += reward
        # Incremental mean update
        n = self.counts[arm]
        self.values[arm] += (reward - self.values[arm]) / n
        self.history.append({"arm": arm, "reward": reward})


class UCB1:
    """Upper Confidence Bound: balances exploitation with exploration bonus.

    Selects the arm with highest: estimated_value + confidence_bound.
    Arms that haven't been pulled much have a large confidence bound,
    ensuring they get explored.

    Regret: O(log n) — provably optimal up to constants.
    """

    def __init__(self, n_arms):
        self.n_arms = n_arms
        self.counts = np.zeros(n_arms)
        self.values = np.zeros(n_arms)
        self.total_pulls = 0
        self.total_reward = 0.0
        self.history = []

    def select_arm(self):
        # Pull each arm at least once
        for arm in range(self.n_arms):
            if self.counts[arm] == 0:
                return arm

        ucb_values = self.values + np.sqrt(
            2 * np.log(self.total_pulls) / self.counts
        )
        return int(np.argmax(ucb_values))

    def update(self, arm, reward):
        self.counts[arm] += 1
        self.total_pulls += 1
        self.total_reward += reward
        n = self.counts[arm]
        self.values[arm] += (reward - self.values[arm]) / n
        self.history.append({"arm": arm, "reward": reward})


class ThompsonSampling:
    """Thompson Sampling: Bayesian approach using posterior sampling.

    Maintains a Beta distribution for each arm's success probability.
    At each step, samples from each posterior and picks the arm with
    the highest sample. Naturally balances exploration and exploitation.

    Widely used at Google, Netflix, and Spotify for:
    - Ad creative testing
    - Content recommendation ranking
    - Feature rollout decisions
    """

    def __init__(self, n_arms):
        self.n_arms = n_arms
        # Beta(1, 1) prior = Uniform(0, 1)
        self.alpha = np.ones(n_arms)
        self.beta = np.ones(n_arms)
        self.counts = np.zeros(n_arms)
        self.total_reward = 0.0
        self.history = []

    def select_arm(self):
        samples = np.random.beta(self.alpha, self.beta)
        return int(np.argmax(samples))

    def update(self, arm, reward):
        """Update with binary reward (0 or 1)."""
        self.counts[arm] += 1
        self.total_reward += reward
        if reward > 0:
            self.alpha[arm] += 1
        else:
            self.beta[arm] += 1
        self.history.append({"arm": arm, "reward": reward})

    def get_posteriors(self):
        """Return posterior Beta parameters for each arm."""
        return [
            {"arm": i, "alpha": self.alpha[i], "beta": self.beta[i],
             "mean": self.alpha[i] / (self.alpha[i] + self.beta[i])}
            for i in range(self.n_arms)
        ]


def run_bandit_simulation(bandit, arm_probabilities, n_rounds=10000):
    """Simulate a bandit experiment.

    Args:
        bandit: Bandit instance (EpsilonGreedy, UCB1, or ThompsonSampling).
        arm_probabilities: List of true success probabilities for each arm.
        n_rounds: Number of rounds to simulate.

    Returns:
        Dict with cumulative regret, arm selection counts, reward history.
    """
    best_arm_prob = max(arm_probabilities)
    cumulative_regret = []
    total_regret = 0.0

    for _ in range(n_rounds):
        arm = bandit.select_arm()
        reward = 1.0 if np.random.random() < arm_probabilities[arm] else 0.0
        bandit.update(arm, reward)

        # Regret = best possible reward - actual reward
        total_regret += best_arm_prob - arm_probabilities[arm]
        cumulative_regret.append(total_regret)

    return {
        "cumulative_regret": cumulative_regret,
        "final_regret": total_regret,
        "arm_counts": bandit.counts.tolist(),
        "arm_values": bandit.values.tolist() if hasattr(bandit, "values") else None,
        "total_reward": bandit.total_reward,
        "best_arm": int(np.argmax(arm_probabilities)),
        "chosen_arm": int(np.argmax(bandit.counts)),
    }
