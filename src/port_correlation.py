import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

file = BASE / "data" / "processed" / "port_daily.csv"
df = pd.read_csv(file)

df["Date"] = pd.to_datetime(df["Date"])

port_table = df.pivot(
    index="Date",
    columns="Control Point",
    values="Port_Share"
)

correlation = port_table.corr()

print("7个口岸的份额相关系数：")
print(correlation.round(3).to_string())

pairs = correlation.stack().rename("Correlation")
pairs.index = pairs.index.set_names([
    "Port_A",
    "Port_B"
])
pairs = pairs.reset_index()
pairs = pairs[
    pairs["Port_A"] < pairs["Port_B"]
].copy()
pairs = pairs.sort_values("Correlation")

print("\n负相关最强的5组口岸：")
print(pairs.head(5).to_string(index=False))


output = BASE / "data" / "processed"

correlation.to_csv(
    output / "port_correlation.csv",
    encoding="utf-8-sig"
)

print("\n相关系数矩阵已保存！")


import matplotlib.pyplot as plt
import seaborn as sns

plt.figure(figsize=(11, 8))

sns.heatmap(
    correlation,
    annot=True,
    fmt=".2f",
    cmap="coolwarm",
    vmin=-1,
    vmax=1,
    center=0,
    square=True
)

plt.title(
    "Correlation of Port Shares (2023-2026)",
    fontsize=14
)

plt.xlabel("Control Point")
plt.ylabel("Control Point")
plt.xticks(rotation=45, ha="right")
plt.yticks(rotation=0)
plt.tight_layout()

chart_folder = BASE / "outputs" / "figures"
chart_folder.mkdir(parents=True, exist_ok=True)

plt.savefig(
    chart_folder / "port_correlation_heatmap.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()
