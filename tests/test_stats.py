"""
Tests for tools/stats.py — pure statistical functions.

No monkeypatching or file I/O needed; these are pure computation functions.
"""

import math

import pytest

from tools.stats import (
    check_early_stopping,
    detect_anomaly,
    interpret_ab_result,
    two_proportion_z_test,
    welch_t_test,
)


# =========================================================================
# two_proportion_z_test
# =========================================================================

class TestTwoProportionZTest:
    """Tests for two_proportion_z_test(successes_a, total_a, successes_b, total_b)."""

    def test_equal_rates_not_significant(self):
        """Same conversion rate should yield high p-value (not significant)."""
        z, p = two_proportion_z_test(50, 1000, 50, 1000)
        assert z == pytest.approx(0.0, abs=0.01)
        assert p > 0.5

    def test_different_rates_significant(self):
        """Large difference with big sample → significant result."""
        # 10% vs 20% with 1000 observations each
        z, p = two_proportion_z_test(100, 1000, 200, 1000)
        assert p < 0.05
        assert z < 0  # group B has higher rate, so z is negative (p_a - p_b < 0)

    def test_small_sample_not_significant(self):
        """Small samples → not enough power → high p-value."""
        z, p = two_proportion_z_test(1, 10, 2, 10)
        assert p > 0.05

    def test_zero_total_returns_fallback(self):
        """Zero denominator should return (0.0, 1.0) gracefully."""
        z, p = two_proportion_z_test(5, 0, 5, 100)
        assert z == 0.0
        assert p == 1.0

    def test_negative_successes_returns_fallback(self):
        z, p = two_proportion_z_test(-1, 100, 50, 100)
        assert z == 0.0
        assert p == 1.0

    def test_all_success_returns_fallback(self):
        """100% success in both groups → pooled p=1.0 → denom=0."""
        z, p = two_proportion_z_test(100, 100, 100, 100)
        assert z == 0.0
        assert p == 1.0

    def test_z_score_sign(self):
        """When group A outperforms group B, z should be positive."""
        z, p = two_proportion_z_test(200, 1000, 100, 1000)
        assert z > 0

    def test_symmetry(self):
        """Swapping groups should flip z sign but keep same p-value."""
        z1, p1 = two_proportion_z_test(100, 1000, 200, 1000)
        z2, p2 = two_proportion_z_test(200, 1000, 100, 1000)
        assert z1 == pytest.approx(-z2, abs=0.001)
        assert p1 == pytest.approx(p2, abs=0.001)


# =========================================================================
# welch_t_test
# =========================================================================

class TestWelchTTest:
    """Tests for welch_t_test(values_a, values_b)."""

    def test_identical_samples_not_significant(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        t, p = welch_t_test(values, values)
        assert t == pytest.approx(0.0, abs=0.01)
        assert p > 0.9

    def test_different_means_significant(self):
        group_a = [1.0, 2.0, 3.0, 4.0, 5.0] * 10  # mean ~3
        group_b = [6.0, 7.0, 8.0, 9.0, 10.0] * 10  # mean ~8
        t, p = welch_t_test(group_a, group_b)
        assert p < 0.001
        assert t < 0  # group A mean < group B mean

    def test_insufficient_samples_returns_fallback(self):
        """Less than 2 observations in either group → (0.0, 1.0)."""
        t, p = welch_t_test([1.0], [2.0, 3.0])
        assert t == 0.0
        assert p == 1.0

        t, p = welch_t_test([1.0, 2.0], [3.0])
        assert t == 0.0
        assert p == 1.0

    def test_empty_lists_returns_fallback(self):
        t, p = welch_t_test([], [])
        assert t == 0.0
        assert p == 1.0

    def test_unequal_variance(self):
        """Welch's t-test handles unequal variance without error."""
        group_a = [1.0, 1.1, 1.0, 0.9, 1.0]  # low variance
        group_b = [1.0, 5.0, 0.5, 4.0, 2.0]   # high variance
        t, p = welch_t_test(group_a, group_b)
        # Should run without error; result validity is secondary
        assert isinstance(t, float)
        assert isinstance(p, float)
        assert 0.0 <= p <= 1.0


# =========================================================================
# check_early_stopping
# =========================================================================

class TestCheckEarlyStopping:
    """Tests for check_early_stopping(p_value, fraction, num_looks)."""

    def test_very_early_look_needs_extreme_significance(self):
        """At 10% of sample, O'Brien-Fleming boundary is very strict."""
        # At fraction=0.1, the adjusted z ≈ 1.96/sqrt(0.1) ≈ 6.2
        # Corresponding two-tailed p ≈ 5.7e-10
        # A p-value of 0.001 should NOT be enough to stop
        assert check_early_stopping(0.001, 0.1, 5) is False

    def test_full_sample_uses_standard_alpha(self):
        """At fraction=1.0, boundary ≈ standard 0.05."""
        assert check_early_stopping(0.04, 1.0, 5) is True

    def test_significant_at_half_sample(self):
        """At 50%, boundary is moderately strict but very small p passes."""
        # At fraction=0.5, adjusted z ≈ 1.96/sqrt(0.5) ≈ 2.77
        # Spending boundary ≈ 0.0056
        assert check_early_stopping(0.001, 0.5, 5) is True

    def test_not_significant_at_half_sample(self):
        """At 50%, a p-value of 0.03 should not trigger early stopping."""
        assert check_early_stopping(0.03, 0.5, 5) is False

    def test_zero_fraction_returns_false(self):
        assert check_early_stopping(0.001, 0.0, 5) is False

    def test_zero_looks_returns_false(self):
        assert check_early_stopping(0.001, 0.5, 0) is False

    def test_negative_looks_returns_false(self):
        assert check_early_stopping(0.001, 0.5, -1) is False

    def test_fraction_clamped_above_one(self):
        """Fraction > 1.0 is clamped to 1.0, behaves like full sample."""
        assert check_early_stopping(0.04, 1.5, 5) is True


# =========================================================================
# detect_anomaly
# =========================================================================

class TestDetectAnomaly:
    """Tests for detect_anomaly(new_value, historical_values, threshold_sigma)."""

    def test_normal_value_returns_none(self):
        history = [10.0, 11.0, 9.5, 10.5, 10.0, 9.8, 10.2]
        result = detect_anomaly(10.3, history)
        assert result is None

    def test_spike_detected(self):
        history = [10.0, 10.5, 9.5, 10.2, 9.8, 10.1, 9.9]  # mean ~10, std ~0.3
        result = detect_anomaly(20.0, history, threshold_sigma=2.0)
        assert result is not None
        assert result["direction"] == "spike"
        assert result["z_score"] > 2.0
        assert result["value"] == 20.0

    def test_drop_detected(self):
        history = [10.0, 10.5, 9.5, 10.2, 9.8, 10.1, 9.9]
        result = detect_anomaly(0.0, history, threshold_sigma=2.0)
        assert result is not None
        assert result["direction"] == "drop"
        assert result["z_score"] < -2.0

    def test_insufficient_history_returns_none(self):
        """Fewer than 5 observations → can't detect anomalies."""
        result = detect_anomaly(100.0, [10.0, 10.0, 10.0, 10.0])
        assert result is None

    def test_zero_std_dev_returns_none(self):
        """All identical values → std_dev=0 → no anomaly detection possible."""
        history = [5.0, 5.0, 5.0, 5.0, 5.0]
        result = detect_anomaly(5.0, history)
        assert result is None
        # Even a different value can't be scored with zero std dev
        result = detect_anomaly(100.0, history)
        assert result is None

    def test_custom_threshold(self):
        """Higher threshold → fewer anomalies detected."""
        history = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        # value=13 is 3 sigma away from constant data (std=0, but let's use varied)
        history_varied = [10.0, 11.0, 9.0, 10.0, 11.0, 9.0, 10.0]
        # At threshold=2, a value of 15 should be anomalous
        result_2 = detect_anomaly(15.0, history_varied, threshold_sigma=2.0)
        # At threshold=10, it should not be
        result_10 = detect_anomaly(15.0, history_varied, threshold_sigma=10.0)
        assert result_2 is not None
        assert result_10 is None

    def test_expected_range_in_result(self):
        history = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        # All same, std=0 → returns None. Use varied data instead.
        history = [9.0, 10.0, 11.0, 10.0, 9.0, 10.0, 11.0]
        result = detect_anomaly(20.0, history, threshold_sigma=2.0)
        assert result is not None
        assert "expected_range" in result
        assert len(result["expected_range"]) == 2
        low, high = result["expected_range"]
        assert low < high


# =========================================================================
# interpret_ab_result
# =========================================================================

class TestInterpretAbResult:
    """Tests for interpret_ab_result(p_value, effect_size, confidence_level)."""

    def test_winner_b(self):
        assert interpret_ab_result(0.01, 0.15) == "winner_b"

    def test_winner_a(self):
        assert interpret_ab_result(0.01, -0.15) == "winner_a"

    def test_trending_b(self):
        """p between alpha and 0.10 with positive effect → trending_b."""
        assert interpret_ab_result(0.08, 0.10) == "trending_b"

    def test_trending_a(self):
        assert interpret_ab_result(0.08, -0.10) == "trending_a"

    def test_inconclusive(self):
        assert interpret_ab_result(0.5, 0.01) == "inconclusive"

    def test_exactly_at_alpha_is_winner(self):
        """p == alpha (0.05) → still significant."""
        assert interpret_ab_result(0.05, 0.10) == "winner_b"

    def test_exactly_at_trending_boundary(self):
        """p == 0.10 → trending."""
        assert interpret_ab_result(0.10, 0.05) == "trending_b"

    def test_custom_confidence_level(self):
        """With 99% confidence, p=0.03 is no longer significant."""
        result = interpret_ab_result(0.03, 0.10, confidence_level=0.99)
        # alpha = 0.01, p=0.03 > alpha → not winner, but p < 0.10 → trending
        assert result == "trending_b"

    def test_zero_effect_size_winner(self):
        """p < alpha with effect_size=0 → technically winner_a (not > 0)."""
        # This is an edge case — effect_size exactly 0
        result = interpret_ab_result(0.01, 0.0)
        assert result == "winner_a"  # 0.0 is not > 0
