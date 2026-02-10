"""Bayesian A/B testing.

Frequentist tests answer: "What's the probability of seeing this data
if there's no effect?" (p-value)

Bayesian tests answer: "What's the probability that treatment B is better
than treatment A?" — a much more intuitive and actionable question.

Bayesian approaches also naturally handle:
- Early stopping (no peeking problem)
- Incorporating prior knowledge
- Direct probability statements ("92% chance B is better")
"""

import numpy as np
from scipy import stats


def bayesian_proportion_test(control_successes, control_total,
                             treatment_successes, treatment_total,
                             prior_alpha=1, prior_beta=1,
                             n_samples=100_000):
    """Bayesian A/B test for conversion rates.

    Uses Beta-Binomial conjugate model:
    - Prior: Beta(alpha, beta) — default is Uniform(0,1)
    - Posterior: Beta(alpha + successes, beta + failures)

    Args:
        control_successes: Conversions in control.
        control_total: Total users in control.
        treatment_successes: Conversions in treatment.
        treatment_total: Total users in treatment.
        prior_alpha: Beta prior alpha (1 = uninformative).
        prior_beta: Beta prior beta.
        n_samples: Monte Carlo samples for probability estimation.

    Returns:
        Dict with posterior stats and probability of treatment being better.
    """
    # Posterior distributions
    ctrl_alpha = prior_alpha + control_successes
    ctrl_beta = prior_beta + (control_total - control_successes)
    treat_alpha = prior_alpha + treatment_successes
    treat_beta = prior_beta + (treatment_total - treatment_successes)

    # Sample from posteriors
    ctrl_samples = np.random.beta(ctrl_alpha, ctrl_beta, n_samples)
    treat_samples = np.random.beta(treat_alpha, treat_beta, n_samples)

    # P(treatment > control)
    prob_treatment_better = (treat_samples > ctrl_samples).mean()

    # Expected lift
    lift_samples = (treat_samples - ctrl_samples) / ctrl_samples
    expected_lift = lift_samples.mean()
    lift_ci = np.percentile(lift_samples, [2.5, 97.5])

    # Expected loss: if we choose treatment, how much do we lose if it's worse?
    loss_if_treatment = np.maximum(ctrl_samples - treat_samples, 0).mean()
    loss_if_control = np.maximum(treat_samples - ctrl_samples, 0).mean()

    return {
        "prob_treatment_better": prob_treatment_better,
        "prob_control_better": 1 - prob_treatment_better,
        "expected_lift": expected_lift,
        "lift_ci_95": (lift_ci[0], lift_ci[1]),
        "expected_loss_choosing_treatment": loss_if_treatment,
        "expected_loss_choosing_control": loss_if_control,
        "control_posterior": {"alpha": ctrl_alpha, "beta": ctrl_beta,
                              "mean": ctrl_alpha / (ctrl_alpha + ctrl_beta)},
        "treatment_posterior": {"alpha": treat_alpha, "beta": treat_beta,
                                "mean": treat_alpha / (treat_alpha + treat_beta)},
        "recommendation": (
            "Deploy treatment" if prob_treatment_better > 0.95
            else "Deploy control" if prob_treatment_better < 0.05
            else "Continue experiment"
        ),
    }


def bayesian_continuous_test(control_values, treatment_values,
                             n_samples=100_000):
    """Bayesian A/B test for continuous metrics (e.g., revenue).

    Uses Normal-Inverse-Gamma conjugate model with weakly informative priors.

    Args:
        control_values: Array of control metric values.
        treatment_values: Array of treatment metric values.
        n_samples: Monte Carlo samples.

    Returns:
        Dict with probability of treatment being better and credible intervals.
    """
    ctrl = np.asarray(control_values, dtype=float)
    treat = np.asarray(treatment_values, dtype=float)

    # Sufficient statistics
    n_c, mean_c, var_c = len(ctrl), ctrl.mean(), ctrl.var(ddof=1)
    n_t, mean_t, var_t = len(treat), treat.mean(), treat.var(ddof=1)

    # Sample from posterior using t-distribution approximation
    # mu | data ~ t(n-1, mean, s/sqrt(n))
    ctrl_samples = stats.t.rvs(
        df=n_c - 1, loc=mean_c, scale=np.sqrt(var_c / n_c), size=n_samples
    )
    treat_samples = stats.t.rvs(
        df=n_t - 1, loc=mean_t, scale=np.sqrt(var_t / n_t), size=n_samples
    )

    diff_samples = treat_samples - ctrl_samples
    prob_better = (diff_samples > 0).mean()

    return {
        "prob_treatment_better": prob_better,
        "expected_difference": diff_samples.mean(),
        "difference_ci_95": tuple(np.percentile(diff_samples, [2.5, 97.5])),
        "control_mean": mean_c,
        "treatment_mean": mean_t,
        "recommendation": (
            "Deploy treatment" if prob_better > 0.95
            else "Deploy control" if prob_better < 0.05
            else "Continue experiment"
        ),
    }
