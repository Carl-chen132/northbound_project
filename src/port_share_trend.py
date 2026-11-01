import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# 1. 找到项目目录
BASE = Path(__file__).resolve().parent.parent

# 2. 读取口岸数据
file = BASE / "data" / "processed" / "port_daily.csv"
df = pd.read_csv(file)

df["Date"] = pd.to_datetime(df["Date"])

# 3. 将7个口岸整理成7列
port_table = df.pivot(
    index="Date",
    columns="Control Point",
    values="Port_Share"
).sort_index()

# 4. 计算30日移动平均，减少每日波动
port_smooth = port_table.rolling(
    window=30,
    min_periods=7
).mean() * 100

# 5. 绘制7个口岸份额趋势
plt.figure(figsize=(14, 7))

for port in port_smooth.columns:
    plt.plot(
        port_smooth.index,
        port_smooth[port],
        label=port,
        linewidth=1.8
    )

# 6. 添加政策日期参考线
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

# 7. 保存图片
output = BASE / "outputs" / "figures"
output.mkdir(parents=True, exist_ok=True)

plt.savefig(
    output / "all_ports_share_trend.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()

print("7个口岸份额趋势图已保存！")
