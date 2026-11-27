# A/B Testing Platform

A beginner-friendly mini experimentation platform using Python, SQLite and Streamlit.

## Features
- Deterministic SHA-256 assignment to Variant A or B
- SQLite tables: users, assignments and events
- Event logging and SQL conversion summaries
- Two-proportion z-test, p-value, confidence interval and effect size
- Sample-size calculator with alpha and power
- 1,000 A/A tests to estimate Type I error
- Daily-peeking simulation to demonstrate false-positive inflation
- Kaggle Marketing A/B Testing CSV upload and analysis
- Chi-square test and Bonferroni-adjusted pairwise comparisons

## 1. Setup

Open this folder in VS Code and run:

```bash
python -m venv venv
```

Windows:
```bash
venv\Scripts\activate
```

macOS/Linux:
```bash
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

## 2. Run the app

```bash
streamlit run app.py
```

Streamlit opens the dashboard in your browser. The SQLite database is created automatically at `database/ab_testing.db`.

## 3. Recommended demo

1. Open **Experiment & Traffic**.
2. Keep experiment ID `button-redesign`.
3. Generate 2,000 users, with A conversion rate 10% and B conversion rate 14%.
4. Open **Statistical Analysis** to inspect the z-test, p-value, confidence interval and effect size.
5. Open **A/A Testing & Peeking** and run 1,000 A/A experiments.
6. Compare fixed-horizon testing with daily peeking.
7. Upload the Kaggle Marketing A/B Testing CSV in **Kaggle Dataset**.
8. Open **Multiple Variants** to test a multi-arm example.

## 4. Kaggle dataset

Search Kaggle for **Marketing A/B Testing** and download the CSV. Upload it through the dashboard. The common dataset has `test_group` and `converted` columns. The app checks for those columns and calculates group conversion rates.

## Statistical notes

- Null hypothesis: conversion rates are equal.
- Alternative hypothesis: conversion rates differ.
- Type I error: rejecting a true null hypothesis.
- Type II error: not rejecting a false null hypothesis.
- Power: probability of detecting a specified real effect.
- Alpha: chosen Type I error threshold.
- Confidence interval: this app uses a standard unpooled Wald interval for the difference (B − A).
- P-value: calculated using a pooled two-proportion z-test.
- Effect size: absolute percentage-point difference and relative lift.
- Sample size: approximate equal-sized groups using a normal approximation.
- A/A tests: under a correctly calibrated test and null hypothesis, around alpha of tests are expected to be significant in the long run. A particular run of 1,000 need not be exactly 50.
- Peeking: repeated unadjusted significance checks inflate false-positive risk. The simulator illustrates this problem; it is not a production sequential-testing method.
- Chi-square: the overall test checks association across multiple variants. Pairwise comparisons use Bonferroni-adjusted p-values.

## Database design

- `users`: one row per user.
- `assignments`: one assignment per user per experiment.
- `events`: records clicks, conversions, signups and purchases.

The hash is based on both experiment ID and user ID, so a user may be assigned differently in separate experiments but consistently within the same experiment.

## Limitations

This is an educational prototype. It does not yet implement authentication, bot filtering, exposure deduplication, experiment pre-registration, stratification, robust sequential testing, or production monitoring. The sample-size and confidence-interval calculations are approximations and should be reviewed before real business use.
