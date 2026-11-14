import pandas as pd
from pathlib import Path

# 找到项目路径
BASE = Path(__file__).resolve().parent.parent

# 读取口岸份额数据
file = BASE / "data" / "processed" / "port_daily.csv"
df = pd.read_csv(file)

# 把日期转换为日期类型
df["Date"] = pd.to_datetime(df["Date"])

# 把7个口岸变成7列
port_table = df.pivot(
    index="Date",
    columns="Control Point",
    values="Port_Share"
)

# 计算各口岸份额之间的相关系数
correlation = port_table.corr()

print("7个口岸的份额相关系数：")
print(correlation.round(3).to_string())

# 找出不同口岸之间的相关性
# 将相关矩阵转换成长表
# stack() 将列转换成第二层索引
pairs = correlation.stack().rename("Correlation")

# 给两层索引重新命名，避免重复列名
pairs.index = pairs.index.set_names([
    "Port_A",
    "Port_B"
])

# 转换成普通表格
pairs = pairs.reset_index()

# 删除同一个口岸与自身的相关系数
pairs = pairs[
    pairs["Port_A"] < pairs["Port_B"]
].copy()

# 按相关系数从小到大排序
pairs = pairs.sort_values("Correlation")

print("\n负相关最强的5组口岸：")
print(pairs.head(5).to_string(index=False))

# 保存相关矩阵
output = BASE / "data" / "processed"

correlation.to_csv(
    output / "port_correlation.csv",
    encoding="utf-8-sig"
)

print("\n相关系数矩阵已保存！")


import matplotlib.pyplot as plt
import seaborn as sns

# 1. 设置图片大小
plt.figure(figsize=(11, 8))

# 2. 绘制相关系数热力图
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

# 3. 设置标题
plt.title(
    "Correlation of Port Shares (2023-2026)",
    fontsize=14
)

plt.xlabel("Control Point")
plt.ylabel("Control Point")

# 4. 调整标签
plt.xticks(rotation=45, ha="right")
plt.yticks(rotation=0)

plt.tight_layout()

# 5. 保存图表
chart_folder = BASE / "outputs" / "figures"
chart_folder.mkdir(parents=True, exist_ok=True)

plt.savefig(
    chart_folder / "port_correlation_heatmap.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()
