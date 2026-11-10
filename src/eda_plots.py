"""Member D's exploratory figures and H5 summaries."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter, StrMethodFormatter
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr, ttest_ind

from .clean_immd import PORTS
from .merge_data import PROCESSED, RAW, PASSENGERS, read_daily

FIGURES = Path(__file__).resolve().parents[1] / "figures" / "member_d"
BLUE = "#24669a"
TEAL = "#137d77"
AMBER = "#c56a24"
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_TYPES = {
    "weekday": "Weekday", "weekend": "Weekend", "school_long_break": "School long break",
    "public_holiday": "Public holiday", "typhoon": "No. 8+ typhoon",
}
WEATHER_GROUPS = {
    "is_rainy": "Measurable rain",
    "is_heavy_rain": "Rain ≥ 30 mm",
    "is_very_hot": "Max temp ≥ 33 °C",
    "is_typhoon": "Typhoon signal No. 8+",
    "is_red_black_rain": "Red/black rain warning",
}


def northbound_history(path=RAW / "immd_daily.csv"):
    raw = pd.read_csv(path, usecols=["Date", "Control Point", "Arrival / Departure", "Hong Kong Residents"])
    raw["Date"] = pd.to_datetime(raw["Date"], format="%d-%m-%Y")
    selected = raw["Control Point"].isin(PORTS) & raw["Arrival / Departure"].eq("Departure")
    return raw.loc[selected].groupby("Date")["Hong Kong Residents"].sum().sort_index()


def plot_trend(history, end):
    fig, ax = plt.subplots(figsize=(11, 4.5))
    history = history.loc["2021-01-01":end]
    ax.plot(history.index, history.rolling(7, min_periods=1).mean() / 1000, color=BLUE)
    markers = {
        "2023-02-06": ("Full reopening", 0.94),
        "2023-07-01": ("Northbound Travel\nfor Hong Kong Vehicles", 0.72),
        "2024-12-01": ("Multiple-entry permit\nfor Shenzhen residents", 0.94),
    }
    for date, (label, height) in markers.items():
        date = pd.Timestamp(date)
        ax.axvline(date, color=AMBER, lw=1, ls="--")
        ax.annotate(label, (date, height), xycoords=("data", "axes fraction"),
                    xytext=(5, 0), textcoords="offset points", va="top", fontsize=9)
    ax.set(title="Hong Kong residents’ northbound departures",
           ylabel="Daily departures (thousands)\n7-day rolling mean")
    return fig


def plot_heatmap(master):
    means = master.pivot_table(index=master["Date"].dt.dayofweek, columns="month", values=PASSENGERS)
    values = means.reindex(index=range(7), columns=range(1, 13)).to_numpy() / 1000
    fig, ax = plt.subplots(figsize=(10, 4.5))
    image = ax.imshow(values, cmap="Blues", aspect="auto")
    for (y, x), value in np.ndenumerate(values):
        color = "white" if image.norm(value) > .62 else "#173751"
        ax.text(x, y, f"{value:.0f}", ha="center", va="center", color=color, fontsize=9)
    ax.set(xticks=range(12), xticklabels=range(1, 13), yticks=range(7), yticklabels=WEEKDAYS,
           xlabel="Month", title="Average northbound departures by weekday and month")
    fig.colorbar(image, ax=ax, label="Daily departures (thousands)")
    return fig


def plot_day_type(master):
    fig, ax = plt.subplots(figsize=(10, 4.5))
    groups = [master.loc[master["day_type"].eq(key), PASSENGERS] / 1000 for key in DAY_TYPES]
    ax.boxplot(groups, patch_artist=True,
               boxprops={"facecolor": "#cfe4f4", "edgecolor": BLUE},
               medianprops={"color": AMBER, "linewidth": 2},
               flierprops={"marker": ".", "alpha": .4})
    ax.set(xticks=range(1, len(groups) + 1),
           xticklabels=[f"{label}\nn = {len(group):,}" for label, group in zip(DAY_TYPES.values(), groups)],
           title="Northbound departures by primary day type", ylabel="Daily departures (thousands)")
    return fig


def plot_golden_week(master):
    # C's official holiday labels cover the entire National Day holiday interval.
    golden = master["mainland_holiday_name"].str.contains("National Day|国庆", case=False, regex=True, na=False)
    autumn = master["month"].isin([9, 10])
    groups = [master.loc[autumn & golden, PASSENGERS], master.loc[autumn & ~golden, PASSENGERS]]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    bars = ax.bar([0, 1], [group.mean() / 1000 for group in groups], color=[TEAL, BLUE], width=.55)
    ax.bar_label(bars, fmt="%.1f", padding=4)
    ax.set(xticks=[0, 1], xticklabels=[f"National Day break\nn = {len(groups[0])}", f"Other Sep–Oct dates\nn = {len(groups[1])}"],
           ylabel="Average daily departures (thousands)", title="National Day holiday comparison")
    ax.margins(y=.16)
    return fig


def plot_port_shares(ports):
    monthly = ports.pivot_table(
        index=ports["Date"].dt.to_period("M"), columns="Control Point",
        values="Hong Kong Residents", aggfunc="sum", fill_value=0,
    )
    shares = monthly.div(monthly.sum(axis=1), axis=0)
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.stackplot(shares.index.to_timestamp(), shares.to_numpy().T, labels=shares.columns,
                 colors=["#143e61", "#24669a", "#4f94bc", "#84b9d3", "#137d77", "#5da796", "#c56a24"])
    ax.set(ylim=(0, 1), ylabel="Share of monthly departures", title="Share of northbound departures by control point")
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.legend(loc="center left", bbox_to_anchor=(1, .5), frameon=False, fontsize=8)
    return fig


def plot_fx(master):
    daily = master.set_index("Date")[[PASSENGERS, "hkd_cny"]].rolling(7).mean().dropna()
    fig, ax = plt.subplots(figsize=(10, 4.5))
    twin = ax.twinx()
    left = ax.plot(daily.index, daily[PASSENGERS] / 1000, color=BLUE, label="Northbound")
    right = twin.plot(daily.index, daily["hkd_cny"], color=AMBER, label="CNY per HKD")
    ax.set(title="Exchange rate and northbound departures (7-day means)", ylabel="Daily departures (thousands)")
    twin.set_ylabel("CNY per HKD", color=AMBER)
    ax.legend(left + right, ["Northbound", "CNY per HKD"], frameon=False, loc="upper left")

    scatter, ax2 = plt.subplots(figsize=(7.5, 4.5))
    ax2.scatter(daily["hkd_cny"], daily[PASSENGERS] / 1000, s=12, alpha=.25, color=BLUE, edgecolors="none")
    ax2.set(title="Exchange rate versus northbound departures (7-day means)",
            xlabel="CNY per HKD", ylabel="Daily departures (thousands)")
    return fig, scatter


def plot_retail(master, path=RAW / "csd_retail_monthly.csv"):
    by_month = master.groupby(master["Date"].dt.to_period("M"))[PASSENGERS].agg(["sum", "size"])
    by_month = by_month.loc[by_month["size"].eq(by_month.index.days_in_month)]
    retail = pd.read_csv(path).set_index("month")
    retail.index = pd.PeriodIndex(retail.index, freq="M")
    joined = by_month.join(retail, how="inner")
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.scatter(joined["sum"] / 1e6, joined["retail_value_hkd_mn"] / 1000, color=TEAL, alpha=.75)
    ax.set(title="Monthly retail sales versus northbound departures",
           xlabel="Monthly departures (millions)", ylabel="Retail sales (HKD billions)")
    return fig


def weather_summary(master):
    """Bivariate H5 checks. Test p-values are nominal and unadjusted."""
    daily = master.assign(is_rainy=master["rainfall_mm"].gt(0).astype(int))
    groups = []
    for column, label in WEATHER_GROUPS.items():
        exposed = daily.loc[daily[column].eq(1), PASSENGERS]
        comparison = daily.loc[daily[column].eq(0), PASSENGERS]
        groups.append({
            "variable": column, "condition": label,
            "n_yes": len(exposed), "n_no": len(comparison),
            "mean_yes": exposed.mean(), "mean_no": comparison.mean(),
            "difference_pct": 100 * (exposed.mean() / comparison.mean() - 1),
            "welch_p": ttest_ind(exposed, comparison, equal_var=False).pvalue,
        })
    correlations = []
    for column in ["tmax_c", "rainfall_mm"]:
        x, y = daily[column], daily[PASSENGERS]
        pearson, pearson_p = pearsonr(x, y)
        spearman, spearman_p = spearmanr(x, y)
        correlations.append({
            "variable": column, "n": len(x), "pearson_r": pearson, "pearson_p": pearson_p,
            "spearman_rho": spearman, "spearman_p": spearman_p,
        })
    return pd.DataFrame(groups), pd.DataFrame(correlations)


def plot_weather(groups):
    chosen = groups.set_index("variable").loc[["is_typhoon", "is_red_black_rain", "is_heavy_rain"]].iloc[::-1]
    fig, ax = plt.subplots(figsize=(8.4, 4.0))
    index = np.arange(len(chosen))
    for suffix, offset, color, label in [("no", -.18, "#9bb1c1", "Other days"), ("yes", .18, TEAL, "Condition present")]:
        values = chosen[f"mean_{suffix}"] / 1000
        bars = ax.barh(index + offset, values, height=.34, color=color, label=label)
        ax.bar_label(bars, labels=[f"{mean:.0f}k" for mean in values], padding=4, fontsize=10)
    ax.set(yticks=index, yticklabels=[f"{name}\nn = {n} days" for name, n in zip(chosen["condition"], chosen["n_yes"])],
           xlabel="Average daily northbound departures", xlim=(0, max(chosen["mean_no"].max(), chosen["mean_yes"].max()) / 1000 * 1.12))
    ax.xaxis.set_major_formatter(StrMethodFormatter("{x:.0f}k"))
    ax.legend(loc="upper center", bbox_to_anchor=(.55, 1.17), frameon=False, ncols=2)
    return fig


def make_figures(master, ports, out=FIGURES, raw_dir=RAW):
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 11, "axes.titlesize": 14, "axes.titleweight": "bold",
        "axes.spines.top": False, "axes.spines.right": False, "axes.labelcolor": "#26384a",
        "axes.edgecolor": "#bbc7d2", "xtick.color": "#26384a", "ytick.color": "#26384a",
    })
    groups, correlations = weather_summary(master)
    fx, fx_scatter = plot_fx(master)
    figures = {
        "01_northbound_trend": plot_trend(northbound_history(raw_dir / "immd_daily.csv"), master["Date"].max()),
        "02_weekday_month_heatmap": plot_heatmap(master),
        "03_day_type_boxplot": plot_day_type(master),
        "04_golden_week": plot_golden_week(master),
        "05_port_share": plot_port_shares(ports),
        "06_fx_dual_axis": fx,
        "07_fx_scatter": fx_scatter,
        "08_retail_scatter": plot_retail(master, raw_dir / "csd_retail_monthly.csv"),
        "09_weather_comparison": plot_weather(groups),
    }
    out.mkdir(parents=True, exist_ok=True)
    for name, fig in figures.items():
        fig.tight_layout()
        fig.savefig(out / f"{name}.png", dpi=175, facecolor="white")
        plt.close(fig)
    groups.to_csv(out / "h5_group_comparison.csv", index=False)
    correlations.to_csv(out / "h5_correlations.csv", index=False)
    return groups, correlations


if __name__ == "__main__":
    # Layer 1. For two exposed days averaging 60 and two comparison days
    # averaging 80, the difference is (60 / 80 - 1) × 100 = -25%.
    sample = pd.DataFrame({PASSENGERS: [50, 70, 70, 90], "tmax_c": [35, 34, 30, 32],
                           "rainfall_mm": [50, 60, 0, 0]})
    for column in list(WEATHER_GROUPS)[1:]:
        sample[column] = [1, 1, 0, 0]
    assert weather_summary(sample)[0].iloc[0]["difference_pct"] == -25
    # Layer 2. Generate all figures on the full sample. Layer 3 is in docs/member_d.md.
    make_figures(read_daily(PROCESSED / "master_daily.csv"), read_daily(PROCESSED / "port_daily.csv"))
    print(f"Saved figures and H5 summaries to {FIGURES}")
