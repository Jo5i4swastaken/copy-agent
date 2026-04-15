"""
Statistical functions for A/B test evaluation.

Provides two-proportion z-tests (for rate metrics like open_rate,
click_rate), Welch's t-tests (for continuous metrics like time_on_page,
cost_per_click), early stopping checks using O'Brien-Fleming spending
boundaries, and z-score-based anomaly detection.

Internal module -- no @function_tool decorators. These are pure computation
functions used by ab_test_tools.py, orchestration_tools.py, and
analytics_tools.py.

Depends on scipy for production-grade statistical distributions.
"""

from __future__ import annotations

import math

from scipy import stats as sp_stats


# ---------------------------------------------------------------------------
# Two-proportion z-test (for rate metrics like open_rate, click_rate)
# ---------------------------------------------------------------------------

def two_proportion_z_test(
    successes_a: int,
    total_a: int,
    successes_b: int,
    total_b: int,
) -> tuple[float, float]:
    """Two-proportion z-test for comparing two conversion rates.

    Args:
        successes_a: Number of successes in group A (e.g. opens).
        total_a:     Total observations in group A (e.g. emails sent).
        successes_b: Number of successes in group B.
        total_b:     Total observations in group B.

    Returns:
        (z_score, p_value) -- two-tailed p-value.
    """
    if total_a <= 0 or total_b <= 0:
        return 0.0, 1.0

    if successes_a < 0 or successes_b < 0:
        return 0.0, 1.0

    p_a = successes_a / total_a
    p_b = successes_b / total_b

    # Pooled proportion under the null hypothesis (p_a == p_b)
    p_pool = (successes_a + successes_b) / (total_a + total_b)

    # Standard error of the difference
    denom = p_pool * (1 - p_pool) * (1 / total_a + 1 / total_b)
    if denom <= 0:
        return 0.0, 1.0

    se = math.sqrt(denom)

    if se == 0:
        return 0.0, 1.0

    z = (p_a - p_b) / se
    p_value = float(2 * sp_stats.norm.sf(abs(z)))

    return float(z), p_value


# ---------------------------------------------------------------------------
# Welch's t-test (for continuous metrics like time_on_page, cost_per_click)
# ---------------------------------------------------------------------------

def welch_t_test(
    values_a: list[float],
    values_b: list[float],
) -> tuple[float, float]:
    """Welch's t-test for comparing two samples with potentially unequal
    variance.

    Args:
        values_a: Observations from group A.
        values_b: Observations from group B.

    Returns:
        (t_statistic, p_value) -- two-tailed p-value.
    """
    if len(values_a) < 2 or len(values_b) < 2:
        return 0.0, 1.0

    result = sp_stats.ttest_ind(values_a, values_b, equal_var=False)
    return float(result.statistic), float(result.pvalue)


# ---------------------------------------------------------------------------
# Sequential testing / early stopping (O'Brien-Fleming boundaries)
# ---------------------------------------------------------------------------

def check_early_stopping(
    p_value: float,
    current_fraction_of_total_sample: float,
    num_looks: int,
) -> bool:
    """Check if an A/B test result is significant enough to stop early.

    Uses an O'Brien-Fleming-style alpha-spending function: the significance
    threshold is very strict at early looks and relaxes as the experiment
    approaches full sample size, controlling the overall false-positive
    rate at approximately 0.05.

    The boundary at fraction t of the total sample is:
        alpha_spend(t) = 2 * (1 - Phi(z_{alpha/2} / sqrt(t)))

    Args:
        p_value: The p-value from the latest statistical test.
        current_fraction_of_total_sample: Fraction of total planned sample
            size collected so far (0.0 to 1.0).
        num_looks: Total number of planned interim analyses. Must be >= 1.

    Returns:
        True if the result is significant enough to stop early.
    """
    if num_looks < 1 or current_fraction_of_total_sample <= 0:
        return False

    fraction = max(0.01, min(1.0, current_fraction_of_total_sample))

    # O'Brien-Fleming critical z-value at this fraction
    z_alpha_half = float(sp_stats.norm.ppf(1 - 0.05 / 2))  # ~1.96
    adjusted_z = z_alpha_half / math.sqrt(fraction)

    # Convert the adjusted z back to a spending boundary (two-tailed p)
    spending_boundary = float(2 * sp_stats.norm.sf(adjusted_z))

    return p_value <= spending_boundary


# ---------------------------------------------------------------------------
# Anomaly detection (z-score based)
# ---------------------------------------------------------------------------

def detect_anomaly(
    new_value: float,
    historical_values: list[float],
    threshold_sigma: float = 2.0,
) -> dict | None:
    """Detect if a new value is an anomaly relative to historical data.

    Returns anomaly details dict if the new value exceeds threshold_sigma
    standard deviations from the mean. Returns None if normal or if there
    is insufficient history (< 5 observations).
    """
    if len(historical_values) < 5:
        return None

    mean = sum(historical_values) / len(historical_values)
    variance = sum((x - mean) ** 2 for x in historical_values) / len(historical_values)
    std_dev = variance ** 0.5

    if std_dev == 0:
        return None

    z_score = (new_value - mean) / std_dev

    if abs(z_score) > threshold_sigma:
        direction = "spike" if z_score > 0 else "drop"
        return {
            "z_score": round(z_score, 3),
            "direction": direction,
            "value": new_value,
            "expected_range": [
                round(mean - threshold_sigma * std_dev, 4),
                round(mean + threshold_sigma * std_dev, 4),
            ],
            "historical_mean": round(mean, 4),
            "historical_std": round(std_dev, 4),
        }
    return None


# ---------------------------------------------------------------------------
# Convenience: interpret a test result
# ---------------------------------------------------------------------------

def interpret_ab_result(
    p_value: float,
    effect_size: float,
    confidence_level: float = 0.95,
) -> str:
    """Return a human-readable verdict for an A/B test comparison.

    Args:
        p_value: The p-value from the statistical test.
        effect_size: The observed effect size (positive means variant B
            outperformed variant A).
        confidence_level: The required confidence level (default 0.95).

    Returns:
        One of: "winner_b", "winner_a", "trending_b", "trending_a",
        "inconclusive".
    """
    alpha = 1 - confidence_level

    if p_value <= alpha:
        return "winner_b" if effect_size > 0 else "winner_a"

    # Trending: p < 0.10 but above the significance threshold
    if p_value <= 0.10:
        return "trending_b" if effect_size > 0 else "trending_a"

    return "inconclusive"
