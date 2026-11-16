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

## 成员 E 的交付

| 文件 | 作用 |
|---|---|
| `src/fetch_utils.py` | 全组共用的 `get_json` / `get_text`，超时 30 秒、失败等 2/4/6 秒重试、最终返回 `None` |
| `src/stats_analysis.py` | 主规格、学校假期规格、交互项、子样本、VIF 与趋势稳健性 |
| `src/ml_model.py` | 随机森林 / 梯度提升，时间序列交叉验证，置换重要性与部分依赖图 |
| `main.py` | fetch → clean → merge → eda → analyze 一键流程 |
| `docs/final_results.md` | H1–H7 结论表与汇报口径 |

结果表在 `results/member_e/`：`regression_main`、`regression_school_break`、`regression_interaction`、`regression_subsamples`、`regression_model_comparison`、`regression_robustness`、`vif_main`、`model_comparison`、`feature_importance`；图在 `figures/member_e/`。

口岸份额（H6）与月度零售（H7）分别由成员 A 与成员 B 负责，不在成员 E 的交付范围内。

