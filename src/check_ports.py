import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

file = BASE / "data" / "processed" / "port_daily.csv"
df = pd.read_csv(file)

df["Date"] = pd.to_datetime(df["Date"])

dates = pd.date_range(
    "2023-02-06",
    "2026-10-31"
)

ports = sorted(df["Control Point"].unique())

expected = pd.MultiIndex.from_product(
    [dates, ports],
    names=["Date", "Control Point"]
)

actual = pd.MultiIndex.from_frame(
    df[["Date", "Control Point"]]
)

missing = expected.difference(actual)

missing_df = missing.to_frame(index=False)


print("Number of ports:", len(ports))
print("Expected number of records:", len(expected))
print("Actual number of records:", len(df))
print("Number of missing combinations:", len(missing_df))

print("\nMissing port-date combinations:")
print(missing_df.to_string(index=False))
