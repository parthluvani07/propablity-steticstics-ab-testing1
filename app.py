import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from database import create_tables, get_summary, clear_experiment
from experiment import register_user, log_event, assign_variant
from statistics_utils import (
    two_proportion_ztest, calculate_sample_size,
    chi_square_test, bonferroni_adjust
)
from simulator import (
    simulate_users_to_database, run_aa_tests,
    run_peeking_simulation, analyze_kaggle_csv
)

st.set_page_config(page_title="A/B Testing Platform", page_icon="🧪",
                   layout="wide")
create_tables()

st.title("🧪 A/B Testing Platform")
st.caption("A mini experimentation platform built with Python, SQLite and Streamlit.")

menu = st.sidebar.radio("Navigation", [
    "Overview", "Experiment & Traffic", "Statistical Analysis",
    "Sample Size Calculator", "A/A Testing & Peeking",
    "Kaggle Dataset", "Multiple Variants"
])

def show_metrics(result):
    c1, c2, c3 = st.columns(3)
    c1.metric("Variant A conversion", f"{result['rate_a']:.2%}")
    c2.metric("Variant B conversion", f"{result['rate_b']:.2%}")
    c3.metric("P-value", f"{result['p_value']:.4f}")
    st.write(f"**Absolute difference (B − A):** {result['difference']:.2%}")
    st.write(f"**95% confidence interval:** [{result['ci_low']:.2%}, {result['ci_high']:.2%}]")
    lift = result["relative_lift"]
    st.write("**Relative lift:** " + (f"{lift:.2f}%" if lift is not None else "Not defined (A rate is zero)"))
    st.write(f"**Z-score:** {result['z_score']:.3f}")
    if result["significant"]:
        st.success("Statistically significant at the selected alpha level.")
    else:
        st.info("Not statistically significant at the selected alpha level.")
    st.caption("A non-significant result does not prove the variants are identical.")

if menu == "Overview":
    st.subheader("Project overview")
    st.write("This platform assigns users consistently to A or B, records events, "
             "compares conversion rates and demonstrates common experimentation pitfalls.")
    st.markdown("""
    **Included concepts**
    - Deterministic SHA-256 hash-based bucketing
    - SQLite users, assignments and events tables
    - Conversion rate and two-proportion z-test
    - P-value, confidence interval and effect size
    - Sample-size estimation, power and significance level
    - 1,000 A/A experiments and daily peeking simulation
    - Kaggle Marketing A/B Testing CSV analysis
    - Chi-square test and Bonferroni correction
    """)
    st.warning("Use simulated or properly consented data. Do not use this demo to make "
               "production decisions without experiment design, data-quality and "
               "sequential-testing safeguards.")

elif menu == "Experiment & Traffic":
    st.subheader("Experiment and user event tracking")
    experiment_id = st.text_input("Experiment ID", "button-redesign")
    st.markdown("### Assign a user")
    user_id = st.text_input("User ID", "user-1001")
    if st.button("Assign user to a variant"):
        variant = register_user(user_id, experiment_id)
        st.success(f"{user_id} is assigned to Variant {variant}. Repeated assignment is stable.")
    st.markdown("### Log an event")
    event_user = st.text_input("Event user ID", "user-1001", key="event_user")
    event_type = st.selectbox("Event type", ["click", "conversion", "signup", "purchase"])
    if st.button("Save event"):
        variant = register_user(event_user, experiment_id)
        log_event(event_user, event_type, experiment_id)
        st.success(f"Saved {event_type} event for Variant {variant}.")
    st.markdown("### Simulate traffic")
    n_users = st.number_input("Number of simulated users", 100, 100000, 2000, step=100)
    rate_a = st.slider("True conversion rate for A", 0.01, 0.50, 0.10, 0.01)
    rate_b = st.slider("True conversion rate for B", 0.01, 0.50, 0.14, 0.01)
    if st.button("Generate simulated traffic"):
        simulate_users_to_database(experiment_id, int(n_users), rate_a, rate_b)
        st.success("Traffic generated and saved to SQLite.")
    if st.button("Clear this experiment's records"):
        clear_experiment(experiment_id)
        st.success("Experiment assignments and events cleared.")
    summary = get_summary(experiment_id)
    st.markdown("### Database conversion summary")
    if summary.empty:
        st.info("No users assigned to this experiment yet.")
    else:
        summary["conversion_rate"] = summary["conversions"] / summary["users"]
        st.dataframe(summary, use_container_width=True)

elif menu == "Statistical Analysis":
    st.subheader("Two-proportion z-test")
    st.write("Enter the number of users and conversions observed in each variant.")
    c1, c2 = st.columns(2)
    with c1:
        n_a = st.number_input("Variant A users", min_value=1, value=1000)
        x_a = st.number_input("Variant A conversions", min_value=0, value=100)
    with c2:
        n_b = st.number_input("Variant B users", min_value=1, value=1000)
        x_b = st.number_input("Variant B conversions", min_value=0, value=140)
    alpha = st.selectbox("Significance level (alpha)", [0.01, 0.05, 0.10], index=1)
    if st.button("Run z-test"):
        try:
            result = two_proportion_ztest(int(x_a), int(n_a), int(x_b), int(n_b), alpha)
            show_metrics(result)
        except ValueError as e:
            st.error(str(e))

elif menu == "Sample Size Calculator":
    st.subheader("Sample-size calculator")
    baseline = st.number_input("Baseline conversion rate (%)", 1.0, 99.0, 10.0) / 100
    mde_pct = st.number_input("Minimum detectable absolute effect (percentage points)",
                              0.1, 50.0, 2.0, 0.1)
    alpha = st.selectbox("Type I error rate (alpha)", [0.01, 0.05, 0.10], index=1)
    power = st.selectbox("Desired statistical power", [0.70, 0.80, 0.90, 0.95], index=1)
    if st.button("Calculate required sample size"):
        try:
            per_group = calculate_sample_size(baseline, mde_pct / 100, alpha, power)
            st.success(f"Required sample size: {per_group:,} users per variant "
                       f"({2*per_group:,} total).")
            st.caption("Approximate normal-theory calculation for two equally sized groups.")
        except ValueError as e:
            st.error(str(e))

elif menu == "A/A Testing & Peeking":
    st.subheader("A/A testing: calibration of the false-positive rate")
    st.write("Both groups have the same true conversion rate. About 5% of tests "
             "should be significant by chance when alpha = 0.05.")
    tests = st.number_input("Number of A/A experiments", 100, 10000, 1000, 100)
    users = st.number_input("Users per variant in each experiment", 50, 10000, 500, 50)
    if st.button("Run A/A simulations"):
        with st.spinner("Running simulations..."):
            result = run_aa_tests(int(tests), int(users))
        st.metric("Observed false-positive rate", f"{result['false_positive_rate']:.2%}")
        st.write(f"Significant tests: {result['significant']} out of {result['tests']}")
        st.write("Expected rate at alpha = 0.05: approximately 5%.")
        fig, ax = plt.subplots()
        ax.hist(result["p_values"], bins=20, edgecolor="black")
        ax.set_xlabel("P-value")
        ax.set_ylabel("Number of experiments")
        ax.set_title("A/A test p-value distribution")
        st.pyplot(fig)
    st.divider()
    st.subheader("Peeking: checking results every day")
    st.write("Repeatedly checking ordinary p-values and stopping as soon as one is "
             "significant inflates the false-positive rate.")
    reps = st.number_input("Peeking simulations", 100, 5000, 1000, 100)
    days = st.slider("Number of daily checks", 3, 30, 14)
    if st.button("Compare fixed horizon vs daily peeking"):
        with st.spinner("Simulating repeated experiments..."):
            result = run_peeking_simulation(int(reps), int(days))
        st.metric("Fixed-horizon false-positive rate", f"{result['fixed_rate']:.2%}")
        st.metric("Daily-peeking false-positive rate", f"{result['peeking_rate']:.2%}")
        st.caption("This is an illustrative simulation under equal true conversion rates. "
                   "Use a sequential-testing method or pre-specified stopping rule in practice.")

elif menu == "Kaggle Dataset":
    st.subheader("Analyze the Kaggle Marketing A/B Testing dataset")
    st.markdown("Download the **Marketing A/B Testing** CSV from Kaggle and upload it below. "
                "The common file is named `marketing_AB.csv` and contains `test_group` "
                "and `converted` columns.")
    uploaded = st.file_uploader("Upload marketing A/B testing CSV", type=["csv"])
    if uploaded:
        try:
            df, summary = analyze_kaggle_csv(uploaded)
            st.write("Dataset preview")
            st.dataframe(df.head(10), use_container_width=True)
            st.write("Group summary")
            st.dataframe(summary, use_container_width=True)
            groups = summary.iloc[:, 0].astype(str).tolist()
            if len(groups) == 2:
                st.write("Two-group statistical comparison")
                a = summary.iloc[0]
                b = summary.iloc[1]
                result = two_proportion_ztest(
                    int(a["conversions"]), int(a["users"]),
                    int(b["conversions"]), int(b["users"])
                )
                show_metrics(result)
            else:
                st.info("The uploaded dataset has more than two groups. Use the Multiple Variants page.")
        except Exception as e:
            st.error(f"Could not analyze this CSV: {e}")

elif menu == "Multiple Variants":
    st.subheader("Chi-square test for multiple variants")
    st.write("Enter conversions and non-conversions for each variant. The chi-square "
             "test checks whether conversion outcome is associated with variant.")
    count = st.number_input("Number of variants", 2, 8, 3)
    names = [chr(65+i) for i in range(int(count))]
    conversions, nonconversions = [], []
    cols = st.columns(int(count))
    for i, col in enumerate(cols):
        with col:
            st.markdown(f"**Variant {names[i]}**")
            conversions.append(st.number_input(f"Conversions {names[i]}", 0, 1000000, 100, key=f"c{i}"))
            nonconversions.append(st.number_input(f"Non-conversions {names[i]}", 0, 1000000, 900, key=f"nc{i}"))
    alpha = st.selectbox("Family-wise alpha", [0.01, 0.05, 0.10], index=1, key="multi_alpha")
    if st.button("Run chi-square test"):
        try:
            result = chi_square_test(conversions, nonconversions)
            st.write(f"Chi-square statistic: **{result['chi2']:.4f}**")
            st.write(f"Degrees of freedom: **{result['dof']}**")
            st.write(f"P-value: **{result['p_value']:.6f}**")
            st.write("**Conclusion:** " + ("Evidence of a difference among variants." if result["p_value"] < alpha else "No statistically significant evidence of a difference."))
            st.caption("An overall chi-square result does not identify which pairs differ.")
            st.markdown("### Bonferroni correction for pairwise comparisons")
            import itertools
            pairs = list(itertools.combinations(range(int(count)), 2))
            raw = []
            labels = []
            for i, j in pairs:
                pair_result = two_proportion_ztest(
                    conversions[i], conversions[i] + nonconversions[i],
                    conversions[j], conversions[j] + nonconversions[j], alpha
                )
                raw.append(pair_result["p_value"])
                labels.append(f"{names[i]} vs {names[j]}")
            adjusted = bonferroni_adjust(raw)
            st.dataframe(pd.DataFrame({
                "Comparison": labels, "Raw p-value": raw,
                "Bonferroni-adjusted p-value": adjusted,
                "Significant": [p < alpha for p in adjusted]
            }), use_container_width=True)
        except Exception as e:
            st.error(str(e))
