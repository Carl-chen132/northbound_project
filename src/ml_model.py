"""Machine-learning stage: rank the factors by predictive importance.

This is the second angle on the same question as the regression. Trees can pick
up non-linearities and interactions that a linear model cannot, but their
importance scores say nothing about direction, so the two stages are reported
side by side rather than one replacing the other.

Two feature sets are trained:

  with_history  the 18 factors plus the same weekday last week and the average
                of the previous seven days. This is the only fair way to compare
                against the naive baseline, which already knows the recent past.
  factors_only  the 18 factors alone. This is the set that ranks the factors the
                design asks about. It keeps the time trend, so it can still beat
                the baseline even without recent passenger counts.

Everything is scored with TimeSeriesSplit, so a model is always tested on days
after the ones it learned from.

Run from the repository root:

    python -m src.ml_model
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.inspection import PartialDependenceDisplay, permutation_importance
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import TimeSeriesSplit

from .stats_analysis import BINARY, CONTINUOUS, SCHOOL_BREAKS, TERMS

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "results" / "member_e"
FIGURES = ROOT / "figures" / "member_e"

TARGET = "Northbound_Passengers"
FACTORS = CONTINUOUS + BINARY + SCHOOL_BREAKS + ["month", "day_of_week"]
HISTORY = ["passengers_lag7", "passengers_mean7"]
FEATURE_SETS = {"with_history": FACTORS + HISTORY, "factors_only": FACTORS}
N_SPLITS = 5
LAG_DAYS = 7

TERMS = dict(TERMS)
TERMS.update({
    "passengers_lag7": "Passengers same weekday last week",
    "passengers_mean7": "Passengers, previous 7-day mean",
    "day_of_week": "Day of week",
    "month": "Month",
})


def load_data():
    """Return the feature frames, the log target and the raw target.

    The first seven days are dropped because a lag of seven days is undefined
    there, which keeps every row usable with every feature set.
    """
    data = pd.read_csv(PROCESSED / "master_daily.csv", parse_dates=["Date"])
    data = data.sort_values("Date").reset_index(drop=True)

    # master_daily stores the weekday as a name; the models need 0 = Monday.
    factors = data[FACTORS].copy()
    factors["day_of_week"] = data["Date"].dt.day_of_week
    factors = factors.astype(float)

    passengers = data[TARGET].astype(float)
    history = pd.DataFrame({
        "passengers_lag7": passengers.shift(LAG_DAYS),
        "passengers_mean7": passengers.shift(1).rolling(7).mean(),
    })
    combined = pd.concat([factors, history], axis=1)

    keep = combined.notna().all(axis=1).to_numpy()
    raw_target = passengers[keep].reset_index(drop=True)
    return (
        data[keep].reset_index(drop=True),
        factors[keep].reset_index(drop=True),
        combined[keep].reset_index(drop=True),
        np.log(raw_target),
        raw_target,
    )


def build_models():
    """The two learners requested in the design, with fixed random states."""
    return {
        "random_forest": RandomForestRegressor(
            n_estimators=500, min_samples_leaf=4, max_features=0.5,
            random_state=0, n_jobs=-1,
        ),
        "gradient_boosting": HistGradientBoostingRegressor(
            loss="absolute_error", max_iter=300, learning_rate=0.05,
            max_leaf_nodes=31, random_state=0,
        ),
    }


def evaluate(frames, log_target, raw_target):
    """Walk forward with TimeSeriesSplit and score each model against the baseline."""
    splitter = TimeSeriesSplit(n_splits=N_SPLITS)
    passengers = raw_target.to_numpy()
    scores, importance = {}, {}

    def record(key, value):
        scores.setdefault(key, []).append(float(value))

    for train_index, test_index in splitter.split(raw_target):
        actual = passengers[test_index]
        record("baseline_lag7", mean_absolute_error(actual, passengers[test_index - LAG_DAYS]))

        for set_name, frame in frames.items():
            for model_name, model in build_models().items():
                model.fit(frame.iloc[train_index], log_target.iloc[train_index])
                predicted = np.expm1(model.predict(frame.iloc[test_index]))
                record(f"{model_name}_{set_name}", mean_absolute_error(actual, predicted))

                if set_name == "factors_only" and model_name == "random_forest":
                    result = permutation_importance(
                        model, frame.iloc[test_index], log_target.iloc[test_index],
                        n_repeats=10, random_state=0, scoring="neg_mean_absolute_error",
                    )
                    importance.setdefault("mean", []).append(result.importances_mean)
                    importance.setdefault("std", []).append(result.importances_std)

    summary = pd.DataFrame({"model": list(scores)})
    summary["mae_passengers"] = [np.mean(values) for values in scores.values()]
    summary["mae_std_across_folds"] = [np.std(values) for values in scores.values()]
    baseline = summary.loc[summary["model"].eq("baseline_lag7"), "mae_passengers"].iloc[0]
    summary["improvement_vs_baseline_pct"] = (1 - summary["mae_passengers"] / baseline) * 100
    return summary, importance


def importance_table(importance):
    """Average permutation importance across folds and rank the factors."""
    table = pd.DataFrame({
        "feature": FACTORS,
        "label": [TERMS.get(feature, feature.replace("_", " ")) for feature in FACTORS],
        "importance_mean": np.mean(importance["mean"], axis=0),
        "importance_std": np.std(importance["mean"], axis=0),
    }).sort_values("importance_mean", ascending=False).reset_index(drop=True)
    table["rank"] = table.index + 1
    return table


def plot_importance(table, path):
    """Horizontal bar chart of the permutation importances."""
    top = table.head(12).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7.4, 5.2))
    ax.barh(top["label"], top["importance_mean"], xerr=top["importance_std"], color="#24669a")
    ax.set_xlabel("Drop in fold MAE when the factor is shuffled (log passengers)")
    ax.set_title("Permutation importance of the 18 factors")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=175, facecolor="white")
    plt.close(fig)


def plot_partial_dependence(model, frame, path):
    """Show whether the exchange rate and temperature act linearly."""
    features = ["hkd_cny", "tmax_c", "rainfall_mm"]
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6))
    PartialDependenceDisplay.from_estimator(
        model, frame, features=features, kind="average", grid_resolution=40, ax=axes,
    )
    for axis, feature in zip(axes, features):
        axis.set_title(TERMS.get(feature, feature))
        axis.set_ylabel("log passengers")
    fig.tight_layout()
    fig.savefig(path, dpi=175, facecolor="white")
    plt.close(fig)


def save(table, filename):
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / filename
    table.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  saved {path.relative_to(ROOT)}")


def run_models():
    """Train both learners on both feature sets, score them and rank the factors."""
    data, factors, combined, log_target, raw_target = load_data()
    frames = {"with_history": combined, "factors_only": factors}
    print(f"  sample: {len(factors):,} days x {len(FACTORS)} factors "
          f"({len(HISTORY)} history features added in the comparative set)")

    summary, importance = evaluate(frames, log_target, raw_target)
    save(summary, "model_comparison.csv")
    for row in summary.itertuples():
        print(f"  {row.model:<32} MAE {row.mae_passengers:>9,.0f} passengers "
              f"({row.improvement_vs_baseline_pct:+5.1f}% vs baseline)")

    table = importance_table(importance)
    save(table, "feature_importance.csv")
    print("\n  top five factors")
    for row in table.head(5).itertuples():
        print(f"    {row.rank}. {row.label:<42} {row.importance_mean:+.4f}")

    FIGURES.mkdir(parents=True, exist_ok=True)
    plot_importance(table, FIGURES / "10_feature_importance.png")
    final_model = build_models()["random_forest"].fit(factors, log_target)
    plot_partial_dependence(final_model, factors, FIGURES / "11_partial_dependence.png")
    print(f"\n  figures written to {FIGURES.relative_to(ROOT)}")
    return summary, table


if __name__ == "__main__":
    run_models()
