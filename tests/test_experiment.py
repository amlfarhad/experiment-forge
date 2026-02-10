"""Tests for core experiment analysis."""

import pytest
import numpy as np

from core.experiment import analyze_continuous, analyze_proportion, analyze_ratio_metric


class TestAnalyzeContinuous:

    def test_significant_difference(self):
        np.random.seed(42)
        control = np.random.normal(100, 10, 10000)
        treatment = np.random.normal(102, 10, 10000)

        result = analyze_continuous(control, treatment)
        assert result.is_significant
        assert result.p_value < 0.05
        assert result.treatment_mean > result.control_mean

    def test_no_difference(self):
        np.random.seed(42)
        control = np.random.normal(100, 10, 10000)
        treatment = np.random.normal(100, 10, 10000)

        result = analyze_continuous(control, treatment)
        # Should usually not be significant (5% FPR)
        # Not guaranteed but very likely
        assert result.p_value > 0.001

    def test_ci_contains_zero_when_no_effect(self):
        np.random.seed(42)
        control = np.random.normal(50, 5, 5000)
        treatment = np.random.normal(50, 5, 5000)

        result = analyze_continuous(control, treatment)
        assert result.ci_lower < 0 < result.ci_upper

    def test_ci_excludes_zero_when_significant(self):
        np.random.seed(42)
        control = np.random.normal(100, 5, 10000)
        treatment = np.random.normal(103, 5, 10000)

        result = analyze_continuous(control, treatment)
        if result.is_significant:
            assert result.ci_lower > 0 or result.ci_upper < 0

    def test_effect_size_direction(self):
        np.random.seed(42)
        control = np.random.normal(100, 10, 5000)
        treatment = np.random.normal(105, 10, 5000)

        result = analyze_continuous(control, treatment)
        assert result.effect_size > 0
        assert result.relative_lift > 0


class TestAnalyzeProportion:

    def test_significant_proportion(self):
        result = analyze_proportion(500, 10000, 600, 10000)
        assert result.is_significant
        assert result.treatment_mean > result.control_mean

    def test_no_difference(self):
        result = analyze_proportion(500, 10000, 505, 10000)
        assert not result.is_significant

    def test_correct_proportions(self):
        result = analyze_proportion(100, 1000, 200, 1000)
        assert result.control_mean == pytest.approx(0.1)
        assert result.treatment_mean == pytest.approx(0.2)


class TestAnalyzeRatioMetric:

    def test_ratio_metric(self):
        np.random.seed(42)
        ctrl_rev = np.random.exponential(10, 5000)
        ctrl_sessions = np.random.poisson(5, 5000).astype(float) + 1
        treat_rev = np.random.exponential(11, 5000)
        treat_sessions = np.random.poisson(5, 5000).astype(float) + 1

        result = analyze_ratio_metric(ctrl_rev, ctrl_sessions, treat_rev, treat_sessions)
        assert result.treatment_mean > result.control_mean
