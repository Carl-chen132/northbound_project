"""H6 robustness: window/trend sensitivity and placebo policy dates.

Companion to ``src/h6_port_regression.py``. The primary script reports one
specification (linear trend plus a post-policy slope change) for 90- and
120-day windows. This module shows how much the HZMB estimate depends on that
choice, and whether equally large "steps" appear at dates when no policy
changed.

Run from the project root:

    python -m src.h6_robustness

Reads  data/processed/port_daily.csv
Writes results/member_a/h6_robustness.csv and h6_placebo.csv
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

BASE = Path(__file__).resolve().parent.parent
INPUT = BASE / "data" / "processed" / "port_daily.csv"
RESULT_DIR = BASE / "results" / "member_a"

POLICY = pd.Timestamp("2023-07-01")
BRIDGE = "Hong Kong-Zhuhai-Macao Bridge"
WINDOWS = (60, 90, 120, 145)  # 145 days is the longest symmetric pre-period
LAGS = 7

SPECS = {
    "level_post": ["post"],
    "trend": ["t", "post"],
    "trend_slope": ["t", "post", "post_t"],
    "quadratic": ["t", "t2", "post"],
}


def load_data() -> pd.DataFrame:
    df = pd.read_csv(INPUT, parse_dates=["Date"])
    if df.duplicated(["Date", "Control Point"]).any():
        raise ValueError("Duplicate date/port pairs; check the input table.")
    shares = df.groupby("Date")["Port_Share"].sum()
    if not np.allclose(shares.to_numpy(), 1.0, atol=1e-5):
        raise ValueError("Port shares do not sum to 1 on some dates.")
    return df.sort_values(["Control Point", "Date"]).reset_index(drop=True)


def prepare(df: pd.DataFrame, policy: pd.Timestamp, days: int) -> pd.DataFrame:
    subset = df.loc[(df["Control Point"] == BRIDGE)
                    & df["Date"].between(policy - pd.Timedelta(days=days),
                                         policy + pd.Timedelta(days=days - 1))].copy()
    if len(subset) != 2 * days:
        raise ValueError(f"{policy.date()} {days}d: expected {2 * days} rows, got {len(subset)}")
    subset["t"] = (subset["Date"] - policy).dt.days.astype(float)
    subset["t2"] = subset["t"] ** 2
    subset["post"] = (subset["Date"] >= policy).astype(float)
    subset["post_t"] = subset["t"].clip(lower=0)
    subset["weekend"] = (subset["Date"].dt.day_of_week >= 5).astype(float)
    subset["y"] = subset["Port_Share"] * 100.0
    return subset


def fit_step(subset: pd.DataFrame, spec: str) -> dict:
    X = sm.add_constant(subset[SPECS[spec] + ["weekend"]], has_constant="add")
    model = sm.OLS(subset["y"], X).fit(cov_type="HAC", cov_kwds={"maxlags": LAGS})
    lo, hi = model.conf_int().loc["post"]
    return {
        "step_pp": float(model.params["post"]),
        "ci_lower_pp": float(lo),
        "ci_upper_pp": float(hi),
        "p_value": float(model.pvalues["post"]),
        "n": int(model.nobs),
        "r_squared": float(model.rsquared),
    }


def robustness(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for days in WINDOWS:
        subset = prepare(df, POLICY, days)
        y = subset["y"]
        rows.append({"window_days": days, "specification": "raw_difference",
                     "step_pp": float(y[subset["post"] == 1].mean() - y[subset["post"] == 0].mean()),
                     "ci_lower_pp": np.nan, "ci_upper_pp": np.nan, "p_value": np.nan,
                     "n": len(subset), "r_squared": np.nan})
        for spec in SPECS:
            rows.append({"window_days": days, "specification": spec, **fit_step(subset, spec)})
    return pd.DataFrame(rows)


def placebo(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for policy in pd.date_range("2023-06-01", "2026-06-01", freq="MS"):
        try:
            subset = prepare(df, policy, 90)
        except ValueError:
            continue
        rows.append({"policy_date": policy.date().isoformat(),
                     "is_real_policy": policy == POLICY, **fit_step(subset, "trend_slope")})
    return pd.DataFrame(rows)


def main() -> None:
    df = load_data()
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    robust = robustness(df)
    robust.to_csv(RESULT_DIR / "h6_robustness.csv", index=False, encoding="utf-8-sig")
    placebo_table = placebo(df)
    placebo_table.to_csv(RESULT_DIR / "h6_placebo.csv", index=False, encoding="utf-8-sig")

    print("HZMB, window x specification (percentage points)")
    print(robust.round(3).to_string(index=False))
    significant = placebo_table[placebo_table["p_value"] < 0.05]
    print(f"\nPlacebo dates with p<.05: {len(significant)} of {len(placebo_table)}")
    print(significant[["policy_date", "step_pp", "p_value"]].round(3).to_string(index=False))
    print(f"\nSaved to {RESULT_DIR.relative_to(BASE)}")


if __name__ == "__main__":
    main()
