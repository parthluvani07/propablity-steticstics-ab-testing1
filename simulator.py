import numpy as np
import pandas as pd
from scipy.stats import norm
from statistics_utils import two_proportion_ztest

def simulate_experiment(n_per_variant=1000, rate_a=0.10, rate_b=0.14, seed=None):
    rng = np.random.default_rng(seed)
    a = rng.binomial(1, rate_a, n_per_variant)
    b = rng.binomial(1, rate_b, n_per_variant)
    return {
        "users_a": n_per_variant, "users_b": n_per_variant,
        "conversions_a": int(a.sum()), "conversions_b": int(b.sum()),
        "result": two_proportion_ztest(int(a.sum()), n_per_variant,
                                       int(b.sum()), n_per_variant)
    }

def run_aa_tests(number_of_tests=1000, n_per_variant=500, alpha=0.05, seed=42):
    rng = np.random.default_rng(seed)
    significant = 0
    p_values = []
    for _ in range(number_of_tests):
        a = rng.binomial(1, 0.10, n_per_variant)
        b = rng.binomial(1, 0.10, n_per_variant)
        result = two_proportion_ztest(int(a.sum()), n_per_variant,
                                      int(b.sum()), n_per_variant, alpha)
        p_values.append(result["p_value"])
        significant += result["p_value"] < alpha
    return {
        "tests": number_of_tests, "significant": significant,
        "false_positive_rate": significant / number_of_tests,
        "p_values": p_values
    }

def run_peeking_simulation(number_of_experiments=1000, max_days=14,
                           users_per_variant_per_day=100, alpha=0.05,
                           seed=123):
    """Compare fixed-horizon testing with daily unadjusted peeking."""
    rng = np.random.default_rng(seed)
    fixed_sig = 0
    peek_sig = 0

    for _ in range(number_of_experiments):
        a_all = rng.binomial(1, 0.10, max_days * users_per_variant_per_day)
        b_all = rng.binomial(1, 0.10, max_days * users_per_variant_per_day)
        fixed = two_proportion_ztest(
            int(a_all.sum()), len(a_all), int(b_all.sum()), len(b_all), alpha
        )
        fixed_sig += fixed["significant"]

        stopped = False
        for day in range(1, max_days + 1):
            n = day * users_per_variant_per_day
            check = two_proportion_ztest(
                int(a_all[:n].sum()), n, int(b_all[:n].sum()), n, alpha
            )
            if check["significant"]:
                peek_sig += 1
                stopped = True
                break
    return {
        "experiments": number_of_experiments,
        "fixed_rate": fixed_sig / number_of_experiments,
        "peeking_rate": peek_sig / number_of_experiments
    }

def simulate_users_to_database(experiment_id, n_users=2000,
                               rate_a=0.10, rate_b=0.14, seed=7):
    from experiment import register_user, log_event
    from database import clear_experiment
    rng = np.random.default_rng(seed)
    clear_experiment(experiment_id)
    for i in range(n_users):
        user_id = f"{experiment_id}-user-{i+1}"
        variant = register_user(user_id, experiment_id)
        rate = rate_a if variant == "A" else rate_b
        log_event(user_id, "click", experiment_id)
        if rng.random() < rate:
            log_event(user_id, "conversion", experiment_id)
    return n_users

def analyze_kaggle_csv(uploaded_file):
    """Load the common Kaggle Marketing A/B Testing CSV schema."""
    df = pd.read_csv(uploaded_file)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    required = {"test_group", "converted"}
    if not required.issubset(df.columns):
        raise ValueError(
            "CSV must contain 'test_group' and 'converted' columns. "
            f"Found: {list(df.columns)}"
        )
    group_col = "test_group"
    conversion_col = "converted"
    summary = df.groupby(group_col)[conversion_col].agg(
        users="count", conversions="sum"
    ).reset_index()
    summary["conversion_rate"] = summary["conversions"] / summary["users"]
    return df, summary
