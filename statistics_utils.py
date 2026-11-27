import math
from scipy.stats import norm, chi2_contingency

def two_proportion_ztest(success_a, n_a, success_b, n_b, alpha=0.05):
    """Pooled two-proportion z-test and unpooled Wald confidence interval."""
    if min(n_a, n_b) <= 0:
        raise ValueError("Each variant must have at least one user.")
    if not (0 <= success_a <= n_a and 0 <= success_b <= n_b):
        raise ValueError("Conversions must be between zero and the sample size.")

    p_a = success_a / n_a
    p_b = success_b / n_b
    difference = p_b - p_a

    pooled = (success_a + success_b) / (n_a + n_b)
    se_null = math.sqrt(pooled * (1 - pooled) * (1/n_a + 1/n_b))
    if se_null == 0:
        z_score, p_value = 0.0, 1.0
    else:
        z_score = difference / se_null
        p_value = 2 * norm.sf(abs(z_score))

    se_ci = math.sqrt(
        p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b
    )
    critical = norm.ppf(1 - alpha / 2)
    ci_low = difference - critical * se_ci
    ci_high = difference + critical * se_ci

    relative_lift = (difference / p_a * 100) if p_a > 0 else None
    return {
        "rate_a": p_a, "rate_b": p_b, "difference": difference,
        "z_score": z_score, "p_value": p_value,
        "ci_low": ci_low, "ci_high": ci_high,
        "relative_lift": relative_lift,
        "significant": p_value < alpha, "alpha": alpha
    }

def calculate_sample_size(baseline_rate, minimum_detectable_effect,
                          alpha=0.05, power=0.80):
    """Approximate equal-sized groups for a two-sided two-proportion test."""
    p1 = baseline_rate
    p2 = p1 + minimum_detectable_effect
    if not (0 < p1 < 1 and 0 < p2 < 1):
        raise ValueError("Baseline and baseline + effect must be between 0 and 1.")
    if not (0 < alpha < 1 and 0 < power < 1):
        raise ValueError("Alpha and power must be between 0 and 1.")

    z_alpha = norm.ppf(1 - alpha / 2)
    z_power = norm.ppf(power)
    p_bar = (p1 + p2) / 2
    numerator = (
        z_alpha * math.sqrt(2 * p_bar * (1 - p_bar)) +
        z_power * math.sqrt(p1 * (1-p1) + p2 * (1-p2))
    ) ** 2
    return math.ceil(numerator / (minimum_detectable_effect ** 2))

def chi_square_test(conversions, non_conversions):
    table = [
        [conversions[i] for i in range(len(conversions))],
        [non_conversions[i] for i in range(len(non_conversions))]
    ]
    chi2, p_value, dof, expected = chi2_contingency(table)
    return {"chi2": chi2, "p_value": p_value, "dof": dof, "expected": expected}

def bonferroni_adjust(p_values):
    m = len(p_values)
    return [min(p * m, 1.0) for p in p_values]
