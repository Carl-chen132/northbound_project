import pandas as pd
from pathlib import Path

# 定位项目文件
BASE = Path(__file__).resolve().parent.parent
FILE = BASE / "data" / "processed" / "port_daily.csv"

# 读取口岸数据
df = pd.read_csv(FILE)
df["Date"] = pd.to_datetime(df["Date"])

# 筛选港珠澳大桥口岸
bridge = df[
    df["Control Point"] ==
    "Hong Kong-Zhuhai-Macao Bridge"
].copy()

# 政策实施日期
policy_date = pd.Timestamp("2023-07-01")

# 分为政策前和政策后
before = bridge[
    bridge["Date"] < policy_date
]

after = bridge[
    bridge["Date"] >= policy_date
]

# 计算平均份额
before_share = before["Port_Share"].mean()
after_share = after["Port_Share"].mean()

print("港车北上政策实施前平均份额：")
print(f"{before_share:.2%}")

print("\n政策实施后平均份额：")
print(f"{after_share:.2%}")

print("\n份额变化（百分点）：")
print(f"{(after_share - before_share) * 100:.2f}")

# 比较港珠澳大桥政策前后的绝对客流量

before_count = before["Hong Kong Residents"].mean()
after_count = after["Hong Kong Residents"].mean()

print("\n政策前每日平均出境人次：")
print(f"{before_count:,.0f}")

print("\n政策后每日平均出境人次：")
print(f"{after_count:,.0f}")

# 计算人次变化比例
change_rate = (
    (after_count - before_count) /
    before_count
) * 100

print("\n平均每日出境人次变化：")
print(f"{change_rate:.2f}%")


import matplotlib.pyplot as plt

# 按时间排序
bridge = bridge.sort_values("Date")

# 计算30日移动平均，减少每日波动
bridge["Share_30D"] = (
    bridge["Port_Share"]
    .rolling(window=30, min_periods=7)
    .mean() * 100
)

# 绘图
plt.figure(figsize=(12, 5))

plt.plot(
    bridge["Date"],
    bridge["Share_30D"],
    label="30-day Average Port Share"
)

# 标记政策日期
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

# 保存图表
chart_folder = BASE / "outputs" / "figures"
chart_folder.mkdir(parents=True, exist_ok=True)

plt.savefig(
    chart_folder / "bridge_share_trend.png",
    dpi=300
)

plt.show()
