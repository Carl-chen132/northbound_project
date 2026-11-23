import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

file = BASE / "data" / "processed" / "port_daily.csv"
df = pd.read_csv(file)

df["Date"] = pd.to_datetime(df["Date"])

port_table = df.pivot(
    index="Date",
    columns="Control Point",
    values="Port_Share"
).sort_index()

port_smooth = port_table.rolling(
    window=30,
    min_periods=7
).mean() * 100

plt.figure(figsize=(14, 7))

for port in port_smooth.columns:
    plt.plot(
        port_smooth.index,
        port_smooth[port],
        label=port,
        linewidth=1.8
    )

plt.axvline(
    pd.Timestamp("2023-07-01"),
    linestyle="--",
    color="gray",
    label="HK Vehicles Northbound (2023-07-01)"
)

plt.title(
    "Hong Kong Residents' Departure Share by Control Point",
    fontsize=14
)

plt.xlabel("Date")
plt.ylabel("Share of Selected Ports (%)")

plt.legend(
    loc="upper left",
    bbox_to_anchor=(1.02, 1)
)

plt.grid(alpha=0.3)
plt.tight_layout()

output = BASE / "outputs" / "figures"
output.mkdir(parents=True, exist_ok=True)

plt.savefig(
    output / "all_ports_share_trend.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()

print("Port share trend charts for the 7 ports saved successfully!")
