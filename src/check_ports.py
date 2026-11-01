import pandas as pd
from pathlib import Path

# 找到项目目录
BASE = Path(__file__).resolve().parent.parent

# 读取口岸数据
file = BASE / "data" / "processed" / "port_daily.csv"
df = pd.read_csv(file)

# 将日期转换为日期格式
df["Date"] = pd.to_datetime(df["Date"])

# 创建完整日期列表
dates = pd.date_range(
    "2023-02-06",
    "2026-10-31"
)

# 获取研究涉及的7个口岸
ports = sorted(df["Control Point"].unique())

# 生成所有日期与口岸组合
expected = pd.MultiIndex.from_product(
    [dates, ports],
    names=["Date", "Control Point"]
)

# 获取实际存在的组合
actual = pd.MultiIndex.from_frame(
    df[["Date", "Control Point"]]
)

# 找出缺少的组合
missing = expected.difference(actual)

# 转换为表格
missing_df = missing.to_frame(index=False)

print("研究口岸数量：", len(ports))
print("预期记录数：", len(expected))
print("实际记录数：", len(df))
print("缺少的组合数：", len(missing_df))

print("\n缺少的口岸日期组合：")
print(missing_df.to_string(index=False))
