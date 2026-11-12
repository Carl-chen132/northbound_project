"""Regression stage: which factors stay correlated after the other controls.

The dependent variable is log(Northbound_Passengers). Every model uses ordinary
least squares with Newey-West (HAC) standard errors, because daily passenger
counts are serially correlated and the plain OLS standard errors would be too
small.

Three specifications are estimated:

  main          month dummies control for seasonality
  school_break  Hong Kong school breaks replace the month dummies
  interaction   main specification plus hkd_cny x is_weekend

School long breaks and the July/August month dummies describe almost the same
days, so only one of the two is kept in each specification and the VIF table is
written out to show the remaining collinearity.

Run from the repository root:

    python -m src.stats_analysis
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "results" / "member_e"

HAC_MAXLAGS = 7  # one week, matching the weekly cycle in the daily counts
VIF_LIMIT = 10.0

CONTINUOUS = [
    "hkd_cny",
    "tmax_c",
    "rainfall_mm",
    "hsi_prev_return",
    "time_index",
]

BINARY = [
    "is_weekend",
    "is_hk_public_holiday",
    "is_holiday_eve",
    "is_long_weekend",
    "is_mainland_holiday",
    "is_mainland_makeup_workday",
    "is_payday_period",
    "is_very_hot",
    "is_heavy_rain",
    "is_typhoon",
    "is_red_black_rain",
    "post_hzmb_policy",
    "post_multi_entry_policy",
]

SCHOOL_BREAKS = ["is_sz_winter_break", "is_sz_summer_break", "is_hk_school_long_break"]

TERMS = {
    "hkd_cny": "1 HKD in CNY",
    "tmax_c": "Daily maximum temperature",
    "rainfall_mm": "Daily total rainfall",
    "hsi_prev_return": "Previous trading day HSI return",
    "time_index": "Days since 2023-02-06",
    "is_weekend": "Weekend",
    "is_hk_public_holiday": "Hong Kong public holiday",
    "is_holiday_eve": "Day before a Hong Kong holiday",
    "is_long_weekend": "Long weekend",
    "is_mainland_holiday": "Mainland public holiday",
    "is_mainland_makeup_workday": "Mainland make-up workday",
    "is_payday_period": "Payday period",
    "is_very_hot": "Maximum temperature >= 33 C",
    "is_heavy_rain": "Rainfall >= 30 mm",
    "is_typhoon": "Signal No. 8 or above",
    "is_red_black_rain": "Red or black rain warning",
    "post_hzmb_policy": "After HK cars northbound policy",
    "post_multi_entry_policy": "After multiple-entry permit resumed",
    "is_sz_winter_break": "Shenzhen winter break",
    "is_sz_summer_break": "Shenzhen summer break",
    "is_hk_school_long_break": "Hong Kong school long break",
}


def load_master():
    """Read the merged analysis table."""
    return pd.read_csv(PROCESSED / "master_daily.csv", parse_dates=["Date"])


def build_design(data, month_dummies=True, school_breaks=False):
    """Return log passengers and the matching design matrix.

    The design matrix is always built from the full sample so that a subsample
    keeps the same columns, including month dummies with no observations.
    """
    features = CONTINUOUS + BINARY
    if school_breaks:
        features = features + SCHOOL_BREAKS

    frame = data[features].astype(float)
    if month_dummies:
        months = pd.get_dummies(data["month"], prefix="month", drop_first=True, dtype=float)
        frame = pd.concat([frame, months], axis=1)

    passengers = data["Northbound_Passengers"].astype(float)
    return np.log(passengers), frame


def drop_constant(frame):
    """Remove columns that never change; they would be collinear with the intercept."""
    keep = frame.columns[frame.nunique() > 1]
    dropped = [column for column in frame.columns if column not in keep]
    if dropped:
        print(f"  dropped constant column(s): {', '.join(dropped)}")
    return frame[keep], dropped


def vif_table(frame):
    """Variance inflation factors for the design matrix including the intercept."""
    with_constant = sm.add_constant(frame, has_constant="add")
    values = [
        variance_inflation_factor(with_constant.to_numpy(dtype=float), index)
        for index in range(1, with_constant.shape[1])
    ]
    table = pd.DataFrame({"term": frame.columns, "vif": values})
    return table.sort_values("vif", ascending=False).reset_index(drop=True)


def fit_ols(y, frame):
    """OLS with Newey-West standard errors, dropping perfectly collinear columns."""
    frame, _ = drop_constant(frame)
    model = sm.OLS(y, sm.add_constant(frame, has_constant="add"))
    return model.fit(cov_type="HAC", cov_kwds={"maxlags": HAC_MAXLAGS})


def coefficient_table(result, means=None):
    """Coefficients, HAC standard errors, p values and a readability label.

    ``means`` holds the sample mean of each continuous variable so that a
    coefficient can be read as an elasticity at the mean.
    """
    means = means if means is not None else {}
    table = pd.DataFrame({
        "term": result.params.index,
        "label": [TERMS.get(term, term.replace("month_", "Month dummy ")) for term in result.params.index],
        "coef": result.params.to_numpy(),
        "std_error": result.bse.to_numpy(),
        "t_value": result.tvalues.to_numpy(),
        "p_value": result.pvalues.to_numpy(),
        "ci_low": result.conf_int()[0].to_numpy(),
        "ci_high": result.conf_int()[1].to_numpy(),
    })
    table["significant_5pct"] = table["p_value"] < 0.05
    table["stars"] = np.select(
        [table["p_value"] < 0.01, table["p_value"] < 0.05, table["p_value"] < 0.10],
        ["***", "**", "*"],
        default="",
    )
    # A dummy's effect is exp(coef) - 1. A continuous variable's effect depends on
    # the size of the change, so it gets an elasticity at the sample mean instead.
    table["pct_effect"] = np.where(
        table["term"].isin(CONTINUOUS), np.nan, (np.exp(table["coef"]) - 1) * 100
    )
    table["elasticity_at_mean"] = [
        means.get(term, np.nan) * coef if term in CONTINUOUS else np.nan
        for term, coef in zip(table["term"], table["coef"])
    ]
    return table


def model_summary(name, result, table):
    """One row per model for the side-by-side comparison table."""
    return {
        "model": name,
        "n": int(result.nobs),
        "r_squared": result.rsquared,
        "adj_r_squared": result.rsquared_adj,
        "aic": result.aic,
        "significant_terms": int(table["significant_5pct"].sum()),
    }


def save(table, filename):
    """Write one result table next to the other Member E outputs."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / filename
    table.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  saved {path.relative_to(ROOT)}")
    return path


def run_analysis():
    """Estimate every specification and write the result tables."""
    data = load_master()
    print(f"  sample: {len(data):,} days, {data['Date'].min():%Y-%m-%d} to {data['Date'].max():%Y-%m-%d}")

    means = data[CONTINUOUS].mean().to_dict()
    y_main, x_main = build_design(data, month_dummies=True, school_breaks=False)
    y_school, x_school = build_design(data, month_dummies=False, school_breaks=True)

    print("main specification")
    main_result = fit_ols(y_main, x_main)
    main_table = coefficient_table(main_result, means)
    save(main_table, "regression_main.csv")
    save(vif_table(x_main), "vif_main.csv")

    print("school-break specification")
    school_result = fit_ols(y_school, x_school)
    school_table = coefficient_table(school_result, means)
    save(school_table, "regression_school_break.csv")

    print("subsamples")
    windows = {
        "A_recovery": ("2023-02-06", "2023-12-31"),
        "B_boom": ("2024-01-01", "2026-10-31"),
    }
    rows, subsample_tables = [], []
    for name, (start, end) in windows.items():
        mask = data["Date"].between(start, end).to_numpy()
        result = fit_ols(y_main[mask], x_main.loc[mask])
        table = coefficient_table(result, means)
        table.insert(0, "subsample", name)
        rows.append(model_summary(name, result, table))
        subsample_tables.append(table)
        print(f"  {name}: {int(result.nobs):,} days, R2 = {result.rsquared:.3f}")
    save(pd.concat(subsample_tables, ignore_index=True), "regression_subsamples.csv")

    print("interaction: exchange rate x weekend")
    y_int, x_int = build_design(data, month_dummies=True, school_breaks=False)
    x_int = x_int.copy()
    x_int["hkd_cny_x_weekend"] = x_int["hkd_cny"] * x_int["is_weekend"]
    interaction_result = fit_ols(y_int, x_int)
    interaction_table = coefficient_table(interaction_result, means)
    save(interaction_table, "regression_interaction.csv")

    rows.insert(0, model_summary("main", main_result, main_table))
    rows.insert(1, model_summary("school_break", school_result, school_table))
    rows.append(model_summary("interaction", interaction_result, interaction_table))
    save(pd.DataFrame(rows), "model_comparison.csv")

    print("\nTop coefficients in the main specification (p < 0.05)")
    shown = main_table[main_table["significant_5pct"] & main_table["term"].ne("const")].copy()
    shown["abs_coef"] = shown["coef"].abs()
    for _, row in shown.sort_values("abs_coef", ascending=False).head(8).iterrows():
        if row["term"] in CONTINUOUS:
            effect = f"{row['elasticity_at_mean']:+.2f}% per +1%"
        else:
            effect = f"{row['pct_effect']:+.1f}%"
        print(f"  {row['label']:<42} {row['coef']:+.4f}  ({effect}, p={row['p_value']:.3f})")

    vif = vif_table(x_main)
    flagged = vif[vif["vif"] > VIF_LIMIT]
    if not flagged.empty:
        print(f"\nVIF above {VIF_LIMIT}: " + ", ".join(f"{row.term} ({row.vif:.1f})" for row in flagged.itertuples()))

    print(f"\n  main model: R2 = {main_result.rsquared:.3f}, n = {int(main_result.nobs):,}")
    return main_result, main_table


if __name__ == "__main__":
    run_analysis()
