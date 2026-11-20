"""H6 descriptive view: monthly HZMB share around the 2023-07-01 policy.

This is the simple version used in the final report: one monthly series, the
pre/post averages, and no regression. The regression and robustness checks
live in ``h6_port_regression.py`` / ``h6_robustness.py`` and are appendix
material only.

Run from the project root:

    python -m src.h6_monthly

Writes results/member_a/h6_monthly_shares.csv
       figures/member_a/h6_monthly_share.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
INPUT = BASE / "data" / "processed" / "port_daily.csv"
RESULT = BASE / "results" / "member_a" / "h6_monthly_shares.csv"
FIGURE = BASE / "figures" / "member_a" / "h6_monthly_share.png"

POLICY = pd.Timestamp("2023-07-01")
BRIDGE = "Hong Kong-Zhuhai-Macao Bridge"


def monthly_share() -> pd.Series:
    df = pd.read_csv(INPUT, parse_dates=["Date"])
    bridge = df[df["Control Point"] == BRIDGE].set_index("Date")["Port_Share"] * 100
    if bridge.empty:
        raise ValueError(f"{BRIDGE} not found in {INPUT}")
    if not bridge.index.is_monotonic_increasing:
        bridge = bridge.sort_index()
    return bridge.resample("MS").mean()


def main() -> None:
    monthly = monthly_share()
    table = monthly.rename("share_pct").rename_axis("month").reset_index()
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(RESULT, index=False, encoding="utf-8-sig")

    pre = monthly[monthly.index < POLICY]
    post = monthly[(monthly.index >= POLICY) & (monthly.index < POLICY + pd.DateOffset(months=12))]
    pre_label = f"{pre.iloc[0]:.1f}% → {pre.iloc[-1]:.1f}%"
    post_label = f"post 12m mean {post.mean():.1f}% ({post.min():.1f}–{post.max():.1f})"

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(monthly.index, monthly.to_numpy(), marker="o", markersize=3.5,
            linewidth=1.8, color="#1f4e79")
    ax.axvline(POLICY, color="#c00000", linestyle="--", linewidth=1.5,
               label="Policy: 2023-07-01 (HK cars northbound)")
    ax.set(title="HZMB share of Hong Kong Resident departures (monthly mean)",
           xlabel="Month", ylabel="Share of the seven ports (%)")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right")
    ax.annotate(pre_label, xy=(pre.index[0], pre.iloc[0]), xytext=(8, 12),
                textcoords="offset points", fontsize=9, color="#1f4e79")
    ax.annotate(post_label, xy=(POLICY, post.mean()), xytext=(8, -18),
                textcoords="offset points", fontsize=9, color="#c00000")
    fig.tight_layout()
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"Monthly means saved to {RESULT.relative_to(BASE)}")
    print(f"Pre-policy 2023-02..06: {pre_label} (mean {pre.mean():.2f}%)")
    print(f"Policy month 2023-07: {monthly.loc[pd.Timestamp('2023-07-01')]:.2f}%")
    print(f"Post-policy 12 months: {post_label}")
    print(f"Figure saved to {FIGURE.relative_to(BASE)}")


if __name__ == "__main__":
    main()
