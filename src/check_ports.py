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

print("研究口岸数量：", len(ports))
print("预期记录数：", len(expected))
print("实际记录数：", len(df))
print("缺少的组合数：", len(missing_df))

print("\n缺少的口岸日期组合：")
print(missing_df.to_string(index=False))
