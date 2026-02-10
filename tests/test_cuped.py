"""Tests for CUPED variance reduction."""

import pytest
import numpy as np

from variance_reduction.cuped import cuped_adjust, cuped_experiment


class TestCUPEDAdjust:

    def test_reduces_variance(self):
        """CUPED should reduce variance when pre/post are correlated."""
        np.random.seed(42)
        n = 5000
        pre = np.random.normal(100, 10, n)
        post = 0.7 * pre + 0.3 * np.random.normal(100, 10, n)  # Correlated

        result = cuped_adjust(post, pre)
        assert result["variance_reduction"] > 0.3  # Should reduce by >30%
        assert result["adjusted_variance"] < result["original_variance"]

    def test_no_reduction_when_uncorrelated(self):
        """CUPED should have negligible effect when pre/post are independent."""
        np.random.seed(42)
        n = 5000
        pre = np.random.normal(100, 10, n)
        post = np.random.normal(100, 10, n)  # Independent

        result = cuped_adjust(post, pre)
        assert abs(result["variance_reduction"]) < 0.05

    def test_theta_sign(self):
        """Theta should be positive when pre/post are positively correlated."""
        np.random.seed(42)
        pre = np.random.normal(100, 10, 1000)
        post = pre + np.random.normal(0, 5, 1000)

        result = cuped_adjust(post, pre)
        assert result["theta"] > 0

    def test_same_mean(self):
        """CUPED should preserve the mean of the metric."""
        np.random.seed(42)
        pre = np.random.normal(100, 10, 5000)
        post = 0.8 * pre + np.random.normal(20, 5, 5000)

        result = cuped_adjust(post, pre)
        np.testing.assert_almost_equal(
            result["adjusted_values"].mean(), post.mean(), decimal=10
        )

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError, match="same length"):
            cuped_adjust([1, 2, 3], [1, 2])

    def test_zero_variance_pre(self):
        """Edge case: if pre-experiment values are constant, no adjustment."""
        post = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        pre = np.array([1.0, 1.0, 1.0, 1.0, 1.0])

        result = cuped_adjust(post, pre)
        assert result["theta"] == 0.0
        assert result["variance_reduction"] == 0.0


class TestCUPEDExperiment:

    def test_cuped_detects_when_standard_doesnt(self):
        """CUPED should detect effects that standard analysis misses."""
        np.random.seed(42)
        n = 2000

        # Create correlated pre/post data
        ctrl_pre = np.random.normal(100, 30, n)
        ctrl_post = 0.7 * ctrl_pre + 0.3 * np.random.normal(100, 30, n)

        treat_pre = np.random.normal(100, 30, n)
        treat_post = 0.7 * treat_pre + 0.3 * np.random.normal(101, 30, n)  # Small effect

        result = cuped_experiment(ctrl_post, ctrl_pre, treat_post, treat_pre)

        # CUPED should have smaller standard error
        assert result["cuped"]["standard_error"] < result["standard"]["standard_error"]
        assert result["improvement"]["se_reduction"] > 0

    def test_effective_sample_multiplier(self):
        """Effective multiplier should be > 1 with correlated data."""
        np.random.seed(42)
        n = 3000
        ctrl_pre = np.random.normal(50, 10, n)
        ctrl_post = 0.8 * ctrl_pre + np.random.normal(10, 5, n)
        treat_pre = np.random.normal(50, 10, n)
        treat_post = 0.8 * treat_pre + np.random.normal(11, 5, n)

        result = cuped_experiment(ctrl_post, ctrl_pre, treat_post, treat_pre)
        assert result["improvement"]["effective_sample_multiplier"] > 1.0
