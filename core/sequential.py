"""Sequential testing with valid early stopping.

The biggest trap in experimentation: peeking at results before the experiment
is done and stopping early when you see significance. This inflates your
false positive rate from 5% to ~26%.

Sequential testing provides ALWAYS-VALID p-values that let you check results
at any time without inflating error rates. This uses alpha spending functions
(O'Brien-Fleming and Pocock boundaries).

Used at: Optimizely, Netflix, Microsoft
"""

import numpy as np
from scipy import stats


class AlphaSpending:
    """Alpha spending function for group sequential testing.

    Controls how the total alpha budget is "spent" across interim analyses.
    """

    @staticmethod
    def obrien_fleming(t, alpha=0.05):
        """O'Brien-Fleming spending function.

        Very conservative early on (hard to reject early), uses most alpha
        at the final analysis. Preferred when early stopping should be rare.

        Args:
            t: Information fraction (0 to 1). t=0.5 means 50% of data collected.
            alpha: Total alpha budget.

        Returns:
            Cumulative alpha spent at information fraction t.
        """
        if t <= 0:
            return 0.0
        z = stats.norm.ppf(1 - alpha / 2) / np.sqrt(t)
        return 2 * (1 - stats.norm.cdf(z))

    @staticmethod
    def pocock(t, alpha=0.05):
        """Pocock spending function.

        Spends alpha more uniformly — easier to reject early, but less
        power at the final analysis.

        Args:
            t: Information fraction.
            alpha: Total alpha budget.

        Returns:
            Cumulative alpha spent at information fraction t.
        """
        return alpha * np.log(1 + (np.e - 1) * t)


class SequentialTest:
    """Group sequential test with alpha spending.

    Allows checking an experiment at predefined interim analyses
    while controlling the overall false positive rate.
    """

    def __init__(self, n_analyses=5, alpha=0.05, spending="obrien_fleming"):
        """
        Args:
            n_analyses: Number of planned interim analyses (including final).
            alpha: Overall significance level.
            spending: 'obrien_fleming' or 'pocock'.
        """
        self.n_analyses = n_analyses
        self.alpha = alpha
        self.spending_fn = (
            AlphaSpending.obrien_fleming if spending == "obrien_fleming"
            else AlphaSpending.pocock
        )
        self.boundaries = self._compute_boundaries()
        self.analyses_done = 0
        self.stopped_early = False
        self.final_result = None

    def _compute_boundaries(self):
        """Compute critical z-values for each interim analysis."""
        boundaries = []
        prev_alpha = 0.0

        for i in range(1, self.n_analyses + 1):
            t = i / self.n_analyses  # Information fraction
            cum_alpha = self.spending_fn(t, self.alpha)
            incremental_alpha = cum_alpha - prev_alpha

            if incremental_alpha > 0:
                z_crit = stats.norm.ppf(1 - incremental_alpha / 2)
            else:
                z_crit = float("inf")

            boundaries.append({
                "analysis": i,
                "info_fraction": t,
                "cumulative_alpha": cum_alpha,
                "incremental_alpha": incremental_alpha,
                "z_critical": z_crit,
            })
            prev_alpha = cum_alpha

        return boundaries

    def analyze_interim(self, control, treatment, analysis_number=None):
        """Run an interim analysis.

        Args:
            control: Array of control group metric values (data so far).
            treatment: Array of treatment group metric values (data so far).
            analysis_number: Which interim analysis (1-indexed). Auto-increments if None.

        Returns:
            Dict with z_stat, z_critical, p_value, reject, should_stop.
        """
        if analysis_number is None:
            self.analyses_done += 1
            analysis_number = self.analyses_done

        if analysis_number > self.n_analyses:
            raise ValueError(f"Analysis {analysis_number} exceeds planned {self.n_analyses}")

        boundary = self.boundaries[analysis_number - 1]

        control = np.asarray(control, dtype=float)
        treatment = np.asarray(treatment, dtype=float)

        diff = treatment.mean() - control.mean()
        se = np.sqrt(treatment.var(ddof=1) / len(treatment) + control.var(ddof=1) / len(control))
        z_stat = diff / se if se > 0 else 0
        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))

        reject = abs(z_stat) > boundary["z_critical"]

        result = {
            "analysis": analysis_number,
            "info_fraction": boundary["info_fraction"],
            "z_stat": z_stat,
            "z_critical": boundary["z_critical"],
            "p_value": p_value,
            "reject": reject,
            "should_stop": reject,
            "control_mean": control.mean(),
            "treatment_mean": treatment.mean(),
            "n_control": len(control),
            "n_treatment": len(treatment),
        }

        if reject:
            self.stopped_early = True
            self.final_result = result

        return result

    def get_boundaries_table(self):
        """Return boundaries as a formatted string."""
        lines = [
            f"{'Analysis':>10} {'Info%':>8} {'α spent':>10} {'z-critical':>12}",
            "-" * 45,
        ]
        for b in self.boundaries:
            lines.append(
                f"{b['analysis']:>10} {b['info_fraction']:>7.0%} "
                f"{b['cumulative_alpha']:>10.4f} {b['z_critical']:>12.4f}"
            )
        return "\n".join(lines)
