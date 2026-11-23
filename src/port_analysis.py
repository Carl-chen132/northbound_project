import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
FILE = BASE / "data" / "processed" / "port_daily.csv"

df = pd.read_csv(FILE)
df["Date"] = pd.to_datetime(df["Date"])

bridge = df[
    df["Control Point"] ==
    "Hong Kong-Zhuhai-Macao Bridge"
].copy()

policy_date = pd.Timestamp("2023-07-01")

before = bridge[
    bridge["Date"] < policy_date
]

after = bridge[
    bridge["Date"] >= policy_date
]

before_share = before["Port_Share"].mean()
after_share = after["Port_Share"].mean()

print("Average share before the Northbound Travel Policy:")
print(f"{before_share:.2%}")

print("\nAverage share after policy implementation:")
print(f"{after_share:.2%}")

print("\nChange in share (percentage points):")
print(f"{(after_share - before_share) * 100:.2f}")

before_count = before["Hong Kong Residents"].mean()
after_count = after["Hong Kong Residents"].mean()

print("\nAverage daily passenger count before the policy:")
print(f"{before_count:,.0f}")

print("\nAverage daily passenger count after the policy:")
print(f"{after_count:,.0f}")

change_rate = (
    (after_count - before_count) /
    before_count
) * 100

print("\nChange in average daily outbound passenger count:")
print(f"{change_rate:.2f}%")

import matplotlib.pyplot as plt

bridge = bridge.sort_values("Date")

bridge["Share_30D"] = (
    bridge["Port_Share"]
    .rolling(window=30, min_periods=7)
    .mean() * 100
)

plt.figure(figsize=(12, 5))

plt.plot(
    bridge["Date"],
    bridge["Share_30D"],
    label="30-day Average Port Share"
)

plt.axvline(
    policy_date,
    linestyle="--",
    label="Northbound Travel for HK Vehicles (2023-07-01)"
)

plt.title("HK-Zhuhai-Macao Bridge: Port Share Over Time")
plt.xlabel("Date")
plt.ylabel("Share of Selected Ports (%)")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()

chart_folder = BASE / "outputs" / "figures"
chart_folder.mkdir(parents=True, exist_ok=True)

plt.savefig(
    chart_folder / "bridge_share_trend.png",
    dpi=300
)

plt.show()
