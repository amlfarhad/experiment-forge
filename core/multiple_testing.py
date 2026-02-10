"""Multiple testing corrections.

When you test 20 metrics in an experiment, one of them will show p < 0.05
just by chance. Multiple testing correction adjusts for this.

FAANG companies routinely test dozens of metrics per experiment —
understanding which correction to use (and when) is essential.
"""

import numpy as np


def bonferroni(p_values, alpha=0.05):
    """Bonferroni correction — the simplest and most conservative.

    Divides alpha by the number of tests. Controls Family-Wise Error Rate (FWER).
    Use when ANY false positive is unacceptable.

    Args:
        p_values: Array of p-values from multiple tests.
        alpha: Overall significance level.

    Returns:
        Dict with adjusted_alpha, significant mask, and adjusted p-values.
    """
    m = len(p_values)
    adjusted_alpha = alpha / m
    adjusted_p = np.minimum(np.array(p_values) * m, 1.0)
    significant = adjusted_p < alpha

    return {
        "method": "Bonferroni",
        "adjusted_alpha": adjusted_alpha,
        "adjusted_p_values": adjusted_p.tolist(),
        "significant": significant.tolist(),
        "n_significant": int(significant.sum()),
    }


def benjamini_hochberg(p_values, alpha=0.05):
    """Benjamini-Hochberg procedure — controls False Discovery Rate (FDR).

    Less conservative than Bonferroni. Controls the expected PROPORTION of
    false positives among rejected hypotheses. Use when some false positives
    are tolerable (common in exploratory analysis of experiment metrics).

    Args:
        p_values: Array of p-values.
        alpha: Target FDR level.

    Returns:
        Dict with adjusted p-values, significant mask.
    """
    p = np.array(p_values)
    m = len(p)
    sorted_idx = np.argsort(p)
    sorted_p = p[sorted_idx]

    # BH adjusted p-values
    adjusted = np.zeros(m)
    adjusted[sorted_idx[-1]] = sorted_p[-1]

    for i in range(m - 2, -1, -1):
        adjusted[sorted_idx[i]] = min(
            adjusted[sorted_idx[i + 1]],
            sorted_p[i] * m / (i + 1)
        )

    adjusted = np.minimum(adjusted, 1.0)
    significant = adjusted < alpha

    return {
        "method": "Benjamini-Hochberg (FDR)",
        "adjusted_p_values": adjusted.tolist(),
        "significant": significant.tolist(),
        "n_significant": int(significant.sum()),
    }


def holm_bonferroni(p_values, alpha=0.05):
    """Holm-Bonferroni — step-down procedure, less conservative than Bonferroni.

    Still controls FWER but has more power. Preferred over plain Bonferroni
    in almost all cases.

    Args:
        p_values: Array of p-values.
        alpha: Overall significance level.

    Returns:
        Dict with adjusted p-values and significant mask.
    """
    p = np.array(p_values)
    m = len(p)
    sorted_idx = np.argsort(p)
    sorted_p = p[sorted_idx]

    adjusted = np.zeros(m)
    adjusted[sorted_idx[0]] = sorted_p[0] * m

    for i in range(1, m):
        adjusted[sorted_idx[i]] = max(
            adjusted[sorted_idx[i - 1]],
            sorted_p[i] * (m - i)
        )

    adjusted = np.minimum(adjusted, 1.0)
    significant = adjusted < alpha

    return {
        "method": "Holm-Bonferroni",
        "adjusted_p_values": adjusted.tolist(),
        "significant": significant.tolist(),
        "n_significant": int(significant.sum()),
    }


def compare_corrections(p_values, alpha=0.05):
    """Run all correction methods and compare results.

    Useful for understanding the sensitivity of your conclusions to the
    choice of correction method.

    Returns:
        Dict mapping method name -> results.
    """
    return {
        "bonferroni": bonferroni(p_values, alpha),
        "holm_bonferroni": holm_bonferroni(p_values, alpha),
        "benjamini_hochberg": benjamini_hochberg(p_values, alpha),
        "uncorrected": {
            "method": "Uncorrected",
            "adjusted_p_values": list(p_values),
            "significant": [p < alpha for p in p_values],
            "n_significant": sum(1 for p in p_values if p < alpha),
        },
    }
