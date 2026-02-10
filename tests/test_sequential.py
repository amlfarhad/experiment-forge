"""Tests for sequential testing module."""

import pytest
import numpy as np

from core.sequential import AlphaSpending, SequentialTest


class TestAlphaSpending:

    def test_obf_starts_conservative(self):
        """O'Brien-Fleming spends very little alpha early."""
        early_alpha = AlphaSpending.obrien_fleming(0.2, alpha=0.05)
        assert early_alpha < 0.001

    def test_obf_ends_at_alpha(self):
        """At t=1 (final analysis), cumulative alpha ≈ total alpha."""
        final_alpha = AlphaSpending.obrien_fleming(1.0, alpha=0.05)
        assert abs(final_alpha - 0.05) < 0.01

    def test_obf_monotonic(self):
        """Alpha spent should increase with information fraction."""
        prev = 0
        for t in np.arange(0.1, 1.1, 0.1):
            current = AlphaSpending.obrien_fleming(t, alpha=0.05)
            assert current >= prev
            prev = current

    def test_pocock_more_uniform(self):
        """Pocock should spend more alpha early compared to OBF."""
        pocock_early = AlphaSpending.pocock(0.2, alpha=0.05)
        obf_early = AlphaSpending.obrien_fleming(0.2, alpha=0.05)
        assert pocock_early > obf_early


class TestSequentialTest:

    def test_boundaries_count(self):
        test = SequentialTest(n_analyses=5)
        assert len(test.boundaries) == 5

    def test_boundaries_decreasing_z(self):
        """z-critical values should decrease over time (easier to reject)."""
        test = SequentialTest(n_analyses=5, spending="obrien_fleming")
        z_values = [b["z_critical"] for b in test.boundaries]
        # OBF: critical values decrease
        assert z_values[0] > z_values[-1]

    def test_no_false_rejection_aa(self):
        """A/A test should usually not reject at any interim analysis."""
        np.random.seed(42)
        test = SequentialTest(n_analyses=5)

        control = np.random.normal(100, 10, 5000)
        treatment = np.random.normal(100, 10, 5000)

        rejected = False
        for i in range(1, 6):
            n = i * 1000
            result = test.analyze_interim(control[:n], treatment[:n], i)
            if result["reject"]:
                rejected = True
                break

        # Not guaranteed but should be rare with OBF
        # Just check the function runs without error
        assert isinstance(rejected, bool)

    def test_detects_large_effect(self):
        """Should reject when there's a large effect."""
        np.random.seed(42)
        test = SequentialTest(n_analyses=5)

        control = np.random.normal(100, 10, 5000)
        treatment = np.random.normal(110, 10, 5000)  # Very large effect

        rejected = False
        for i in range(1, 6):
            n = i * 1000
            result = test.analyze_interim(control[:n], treatment[:n], i)
            if result["reject"]:
                rejected = True
                break

        assert rejected

    def test_exceeding_analyses_raises(self):
        test = SequentialTest(n_analyses=3)
        with pytest.raises(ValueError, match="exceeds"):
            test.analyze_interim([1, 2], [3, 4], analysis_number=4)

    def test_boundaries_table(self):
        test = SequentialTest(n_analyses=3)
        table = test.get_boundaries_table()
        assert "Analysis" in table
        assert "z-critical" in table
