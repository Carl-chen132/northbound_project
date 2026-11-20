# 港人北上出行的多因素相关性分析

主样本为 2023-02-06 至 2026-10-31。分析单位为日；口岸表为日期 × 口岸。原始和处理数据分别放在 `data/raw/`、`data/processed/`。

## 环境与运行

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
python main.py analyze
```

`analyze` 从已冻结的 `master_daily.csv` 生成多元回归（HAC 标准误、VIF、交互项、子样本、趋势稳健性）与机器学习结果，写入 `results/member_e/` 和 `figures/member_e/`。它不重新抓数、不改写冻结数据。完整重建流程为 `python main.py`。

结果表在 `results/member_e/`：`regression_main`、`regression_school_break`、`regression_interaction`、`regression_subsamples`、`regression_model_comparison`、`regression_robustness`、`vif_main`、`model_comparison`、`feature_importance`；图在 `figures/member_e/`。

## 口岸份额（H6）与月度零售（H7）

H6 正文采用描述性的月度比较，不做回归归因：

```bash
python -m src.h6_monthly
```

输出 `results/member_a/h6_monthly_shares.csv` 与 `figures/member_a/h6_monthly_share.png`。大桥份额在政策前已由 14.3% 降至 10.8%，政策当月 11.0%，之后 12 个月均值 10.4%、基本横盘，未出现预期中的上升。

局部回归与稳健性检查仅作附表，不进入正文：

```bash
python -m src.h6_port_regression   # 90/120 天局部回归与系数，写入 results/member_a
python -m src.h6_robustness        # 窗口/趋势规格敏感性与安慰剂日期
```

H7 由成员 B 的 `src/correlation_tests.py` 生成，同时产出 H1 汇率相关与相关矩阵：

```bash
python -m src.correlation_tests
```

结果见 `results/member_b/h7_retail_correlations.csv`：43 个月同月水平 r=-.097（p=.536），百分比变化 r=+.258（p=.099），未获支持。
