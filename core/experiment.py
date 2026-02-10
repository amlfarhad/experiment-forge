"""Core experiment analysis — the foundation of any A/B testing platform."""

import numpy as np
from scipy import stats


class ExperimentResult:
    """Container for experiment analysis results."""

    def __init__(self, test_name, statistic, p_value, ci_lower, ci_upper,
                 control_mean, treatment_mean, effect_size, is_significant,
                 alpha=0.05):
        self.test_name = test_name
        self.statistic = statistic
        self.p_value = p_value
        self.ci_lower = ci_lower
        self.ci_upper = ci_upper
        self.control_mean = control_mean
        self.treatment_mean = treatment_mean
        self.effect_size = effect_size
        self.relative_lift = (treatment_mean - control_mean) / control_mean if control_mean != 0 else 0
        self.is_significant = is_significant
        self.alpha = alpha

    def __repr__(self):
        sig = "SIGNIFICANT" if self.is_significant else "NOT significant"
        return (
            f"ExperimentResult({self.test_name})\n"
            f"  Control mean:     {self.control_mean:.4f}\n"
            f"  Treatment mean:   {self.treatment_mean:.4f}\n"
            f"  Relative lift:    {self.relative_lift:+.2%}\n"
            f"  p-value:          {self.p_value:.6f}\n"
            f"  95% CI:           [{self.ci_lower:.4f}, {self.ci_upper:.4f}]\n"
            f"  Effect size (d):  {self.effect_size:.4f}\n"
            f"  Result:           {sig} at α={self.alpha}"
        )


def analyze_continuous(control, treatment, alpha=0.05, test="welch"):
    """Analyze a continuous metric experiment (e.g., revenue per user).

    Args:
        control: Array of metric values for control group.
        treatment: Array of metric values for treatment group.
        alpha: Significance level.
        test: 'welch' (default, unequal variance) or 'student' (equal variance).

    Returns:
        ExperimentResult.
    """
    control = np.asarray(control, dtype=float)
    treatment = np.asarray(treatment, dtype=float)

    equal_var = test == "student"
    t_stat, p_value = stats.ttest_ind(control, treatment, equal_var=equal_var)

    # Confidence interval for the difference in means
    diff = treatment.mean() - control.mean()
    se = np.sqrt(treatment.var(ddof=1) / len(treatment) + control.var(ddof=1) / len(control))
    z = stats.norm.ppf(1 - alpha / 2)
    ci_lower = diff - z * se
    ci_upper = diff + z * se

    # Cohen's d effect size
    pooled_std = np.sqrt(
        ((len(control) - 1) * control.var(ddof=1) + (len(treatment) - 1) * treatment.var(ddof=1))
        / (len(control) + len(treatment) - 2)
    )
    cohens_d = diff / pooled_std if pooled_std > 0 else 0

    return ExperimentResult(
        test_name=f"Two-sample t-test ({test})",
        statistic=t_stat,
        p_value=p_value,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        control_mean=control.mean(),
        treatment_mean=treatment.mean(),
        effect_size=cohens_d,
        is_significant=p_value < alpha,
        alpha=alpha,
    )


def analyze_proportion(control_successes, control_total,
                       treatment_successes, treatment_total, alpha=0.05):
    """Analyze a proportion/conversion rate experiment (e.g., click-through rate).

    Uses a two-proportion z-test.

    Args:
        control_successes: Number of conversions in control.
        control_total: Total users in control.
        treatment_successes: Number of conversions in treatment.
        treatment_total: Total users in treatment.
        alpha: Significance level.

    Returns:
        ExperimentResult.
    """
    p1 = control_successes / control_total
    p2 = treatment_successes / treatment_total

    # Pooled proportion under H0
    p_pool = (control_successes + treatment_successes) / (control_total + treatment_total)
    se_pool = np.sqrt(p_pool * (1 - p_pool) * (1 / control_total + 1 / treatment_total))

    z_stat = (p2 - p1) / se_pool if se_pool > 0 else 0
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

    # CI for the difference
    se_diff = np.sqrt(p1 * (1 - p1) / control_total + p2 * (1 - p2) / treatment_total)
    z_crit = stats.norm.ppf(1 - alpha / 2)
    diff = p2 - p1
    ci_lower = diff - z_crit * se_diff
    ci_upper = diff + z_crit * se_diff

    # Effect size: Cohen's h
    cohens_h = 2 * (np.arcsin(np.sqrt(p2)) - np.arcsin(np.sqrt(p1)))

    return ExperimentResult(
        test_name="Two-proportion z-test",
        statistic=z_stat,
        p_value=p_value,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        control_mean=p1,
        treatment_mean=p2,
        effect_size=cohens_h,
        is_significant=p_value < alpha,
        alpha=alpha,
    )


def analyze_ratio_metric(control_num, control_denom, treatment_num, treatment_denom,
                         alpha=0.05):
    """Analyze a ratio metric using the delta method.

    Ratio metrics (e.g., revenue per session = total_revenue / total_sessions)
    require special handling because the numerator and denominator are correlated.

    The delta method provides correct variance estimates for ratios.

    Args:
        control_num: Array of per-unit numerator values (e.g., revenue per user).
        control_denom: Array of per-unit denominator values (e.g., sessions per user).
        treatment_num: Same for treatment.
        treatment_denom: Same for treatment.
        alpha: Significance level.

    Returns:
        ExperimentResult.
    """
    control_num = np.asarray(control_num, dtype=float)
    control_denom = np.asarray(control_denom, dtype=float)
    treatment_num = np.asarray(treatment_num, dtype=float)
    treatment_denom = np.asarray(treatment_denom, dtype=float)

    # Ratio estimates
    r_c = control_num.sum() / control_denom.sum()
    r_t = treatment_num.sum() / treatment_denom.sum()

    # Delta method variance: Var(N/D) ≈ (1/D²)[Var(N) + R²Var(D) - 2R·Cov(N,D)]
    def delta_var(num, denom, ratio):
        n = len(num)
        d_mean = denom.mean()
        var_n = num.var(ddof=1)
        var_d = denom.var(ddof=1)
        cov_nd = np.cov(num, denom, ddof=1)[0, 1]
        return (var_n + ratio**2 * var_d - 2 * ratio * cov_nd) / (n * d_mean**2)

    var_c = delta_var(control_num, control_denom, r_c)
    var_t = delta_var(treatment_num, treatment_denom, r_t)

    diff = r_t - r_c
    se = np.sqrt(var_c + var_t)
    z_stat = diff / se if se > 0 else 0
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

    z_crit = stats.norm.ppf(1 - alpha / 2)
    ci_lower = diff - z_crit * se
    ci_upper = diff + z_crit * se

    return ExperimentResult(
        test_name="Delta method (ratio metric)",
        statistic=z_stat,
        p_value=p_value,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        control_mean=r_c,
        treatment_mean=r_t,
        effect_size=diff / r_c if r_c != 0 else 0,
        is_significant=p_value < alpha,
        alpha=alpha,
    )
