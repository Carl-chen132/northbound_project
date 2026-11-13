"""Member B: single-factor correlations for the economic variables.

Four outputs, all written to results/member_b/:

  fx_source_comparison.csv   Frankfurter vs FRED on the days both publish
  h1_fx_correlations.csv     exchange rate vs daily northbound trips (H1)
  h7_retail_correlations.csv monthly northbound trips vs retail sales (H7)
  correlation_matrix.csv     every continuous variable against every other

and one figure, figures/member_b/12_correlation_matrix.png.

Only correlation is reported, never causation.

Run from the repository root:

    python -m src.correlation_tests
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "results" / "member_b"
FIGURES = ROOT / "figures" / "member_b"

PASSENGERS = "Northbound_Passengers"

# Sub-samples from the design plan
WINDOWS = {
    "full": ("2023-02-06", "2026-10-31"),
    "A_recovery": ("2023-02-06", "2023-12-31"),
    "B_boom": ("2024-01-01", "2026-10-31"),
}

# Continuous variables for the correlation matrix, with short labels for the figure
MATRIX_VARIABLES = {
    "Northbound_Passengers": "Northbound trips",
    "Mainland_Arrivals": "Mainland arrivals",
    "Net_Departure": "Net departure",
    "hkd_cny": "HKD→CNY",
    "hkd_cny_30d_change": "HKD→CNY 30-day change",
    "fred_hkd_cny": "HKD→CNY (FRED)",
    "hsi_prev_return": "HSI previous return",
    "tmax_c": "Max temperature",
    "rainfall_mm": "Rainfall",
    "time_index": "Time trend",
}


def correlate(x, y):
    """Pearson and Spearman correlation of two series, ignoring missing values."""
    pair = pd.concat([x, y], axis=1, sort=True).dropna()
    r, r_p = pearsonr(pair.iloc[:, 0], pair.iloc[:, 1])
    rho, rho_p = spearmanr(pair.iloc[:, 0], pair.iloc[:, 1])
    return {"n": len(pair), "pearson_r": r, "pearson_p": r_p, "spearman_rho": rho, "spearman_p": rho_p}


def save(table, filename):
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / filename
    table.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  saved {path.relative_to(ROOT)}")


def load_master():
    master = pd.read_csv(PROCESSED / "master_daily.csv", parse_dates=["Date"])
    return master.set_index("Date").sort_index()


# ---------- 1. Frankfurter vs FRED ----------
def compare_fx_sources():
    """Compare the two exchange-rate sources on the days both publish a rate."""
    fx = pd.read_csv(RAW / "fx_frankfurter_daily.csv", parse_dates=["date"]).set_index("date")["hkd_cny"]
    fred = pd.read_csv(RAW / "fx_fred_daily.csv", parse_dates=["date"]).set_index("date")["fred_hkd_cny"]
    both = pd.concat([fx, fred], axis=1, sort=True).dropna()
    gap = (both["fred_hkd_cny"] / both["hkd_cny"] - 1).abs() * 100
    result = correlate(both["hkd_cny"], both["fred_hkd_cny"])
    result.update({"mean_abs_gap_pct": gap.mean(), "max_abs_gap_pct": gap.max()})
    return pd.DataFrame([result])


# ---------- 2. H1: exchange rate vs daily northbound trips ----------
def remove_weekday_effect(series):
    """Subtract each weekday's own average, so weekends no longer dominate."""
    return series - series.groupby(series.index.day_of_week).transform("mean")


def remove_trend(series):
    """Subtract a straight-line time trend, so two series that both drift over time do not look related."""
    t = np.arange(len(series))
    slope, intercept = np.polyfit(t, series.values, 1)
    return series - (slope * t + intercept)


def h1_correlations(master):
    """Correlate the exchange rate with northbound trips in five versions and three samples."""
    rows = []
    for window, (start, end) in WINDOWS.items():
        data = master.loc[start:end]
        trips = data[PASSENGERS]
        versions = {
            "daily (raw)": (data["hkd_cny"], trips),
            "7-day average": (data["hkd_cny"].rolling(7).mean(), trips.rolling(7).mean()),
            "weekday effect removed": (data["hkd_cny"], remove_weekday_effect(np.log(trips))),
            "weekday and trend removed": (remove_trend(data["hkd_cny"]),
                                          remove_trend(remove_weekday_effect(np.log(trips)))),
            "30-day change, weekday removed": (data["hkd_cny_30d_change"], remove_weekday_effect(np.log(trips))),
        }
        for version, (x, y) in versions.items():
            rows.append({"sample": window, "version": version, **correlate(x, y)})
    return pd.DataFrame(rows)


# ---------- 3. H7: monthly northbound trips vs retail sales ----------
def monthly_northbound(master):
    """Total northbound trips per calendar month, keeping complete months only."""
    trips = master[PASSENGERS]
    monthly = trips.resample("MS").agg(["sum", "count"])
    complete = monthly["count"] == monthly.index.days_in_month
    return monthly.loc[complete, "sum"].rename("northbound_trips")


def h7_correlations(master):
    """Same-month and one-month-lag correlations, in levels and in month-on-month changes."""
    trips = monthly_northbound(master)
    retail = pd.read_csv(RAW / "csd_retail_monthly.csv", parse_dates=["month"]).set_index("month")
    sales = retail["retail_value_hkd_mn"]
    tests = {
        "same month, levels": (trips, sales),
        "retail one month later, levels": (trips, sales.shift(-1)),
        "same month, % change": (trips.pct_change(), sales.pct_change()),
        "retail one month later, % change": (trips.pct_change(), sales.pct_change().shift(-1)),
    }
    rows = [{"test": name, **correlate(x, y)} for name, (x, y) in tests.items()]
    return pd.DataFrame(rows)


# ---------- 4. Correlation matrix ----------
def correlation_matrix(master):
    columns = list(MATRIX_VARIABLES)
    return master[columns].corr(method="pearson")


def plot_matrix(matrix):
    labels = [MATRIX_VARIABLES[c] for c in matrix.columns]
    fig, ax = plt.subplots(figsize=(9, 7.5))
    image = ax.imshow(matrix.values, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
    ax.set_yticks(range(len(labels)), labels)
    for i in range(len(labels)):
        for j in range(len(labels)):
            value = matrix.values[i, j]
            ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=8,
                    color="white" if abs(value) > 0.6 else "black")
    fig.colorbar(image, ax=ax, label="Pearson r")
    ax.set_title("Correlation matrix of continuous variables (2023-02-06 to 2026-10-31)")
    fig.tight_layout()
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / "12_correlation_matrix.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(f"  saved {path.relative_to(ROOT)}")


def run_analysis():
    master = load_master()
    print(f"  sample: {len(master):,} days")

    print("1. Frankfurter vs FRED")
    save(compare_fx_sources(), "fx_source_comparison.csv")

    print("2. H1 exchange rate vs northbound trips")
    save(h1_correlations(master), "h1_fx_correlations.csv")

    print("3. H7 northbound trips vs retail sales")
    save(h7_correlations(master), "h7_retail_correlations.csv")

    print("4. correlation matrix")
    matrix = correlation_matrix(master)
    save(matrix.reset_index().rename(columns={"index": "variable"}), "correlation_matrix.csv")
    plot_matrix(matrix)


if __name__ == "__main__":
    run_analysis()
