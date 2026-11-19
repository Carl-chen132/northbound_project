# 成员 D｜天气、数据合并与图表

主样本为 2023-02-06 至 2026-10-31。观察单位是日期，口岸表的观察单位是日期与口岸。总趋势图额外使用 2021-01-01 至 2023-02-05 的背景数据。

## 运行顺序

`member-d-weather` 分支包含 `main.py`、日历生成代码、日历源表和重建所需的冻结原始数据。日历使用 C 在 `ba250ba` 中删除 X8 后的版本，已同步至 `feature/c-calendar` 的 `c65543b`。共同输入与运行入口同步自 `main` 的 `cb339b1`，其中 B 的汇率和市场数据来自 `2220974`。

从新克隆的分支根目录运行以下命令即可重建。依赖见 `requirements.txt`。

```bash
git clone --branch member-d-weather --single-branch https://github.com/Carl-chen132/northbound_project.git
cd northbound_project
python -m pip install -r requirements.txt
python main.py clean
python main.py merge
```

`clean` 使用分支中保存的入境处、日历和天气源文件，重新生成客流、日历和天气输入。`merge` 随后生成 `data/processed/master_daily.csv` 和 `data/processed/port_daily.csv`。这两个步骤使用已冻结的文件，在正常重建时均可离线运行。

总表应为 1,364 行 × 34 列，口岸表应为 9,548 行 × 39 列。两张表都已移除 `is_hk_school_short_break`。`is_hk_school_long_break` 继续按 C 的长假区间生成。日期范围为 2023-02-06 至 2026-10-31，口岸表每天有 7 个口岸。

图表和 H5 统计表可用 `python main.py eda` 生成，写入 `figures/member_d/`。需要重新抓取源数据时可分别运行 `notebooks/01_get_immd.ipynb`、`notebooks/02_get_fx_market.ipynb`、`notebooks/03_get_calendar.ipynb` 和 `notebooks/04_get_weather.ipynb`，Jupyter 运行需要 `ipykernel`。

`merge_data.py` 会把 A 生成的 `port_daily.csv` 加上每日特征。即使该文件已合并过，也可以重新运行。月度零售数据留在月度分析中。恒指使用出行日前最近一个交易日的回报，汇率的 30 日变化按自然日计算。

## 天气变量

| 变量 | CSV 字段 | 计算方法 |
|---|---|---|
| X11 | `tmax_c`、`is_very_hot` | HKO 站日最高气温（°C）。达到 33°C 标记为 1。 |
| X12 | `rainfall_mm`、`is_heavy_rain` | HKO 站日总雨量（mm）。达到 30 mm 标记为 1，微量雨记 0。 |
| X13 | `is_typhoon` | 当天任意时段生效的 8、9、10 号热带气旋信号。 |
| X14 | `is_red_black_rain` | 当天任意时段生效的红色或黑色暴雨警告。 |

警告数据库的初始页面只有查询表单。网页从后台请求两个记录档案，再用 JavaScript 生成结果表。程序读取档案中的开始和结束时间，按香港时间展开。若警告在午夜取消，则取消日期不计入。日历分类以 8 号或以上风球为最高优先级，其余分类沿用 C 的表。

冻结的气温 API 和全年雨量 CSV 只到 2026 年 9 月。2026 年 10 月的 31 天用天文台同站逐日观测表中的最高气温和日总雨量补齐。10 月逐日雨量合计 81.0 mm，与官方月报一致。

## 三层检查

1. **手算样例**：原始风球时间 `240` 应解析为香港时间 02:40。两个口岸在同一天应得到相同的天气标记。示例两组均值为 60 和 80 时，差幅应为 −25%。
2. **实际数据**：总表为 1,364 行 × 34 列，口岸表为 9,548 行 × 39 列，日期与口岸组合唯一。两张表均不含已删除的 X8。每日口岸人次之和与 Y1 一致，份额之和为 100%。合并时检查输入缺失、重复日期及过期的 X8 字段。已从仅包含分支已跟踪文件的干净目录运行 `python main.py clean` 和 `python main.py merge`，逐列对比后两张表的其余数据与修订前一致，重复合并也得到相同文件。
3. **官网核对**：天文台 2023 年 9 月月报表 1.1 记录苏拉 10 号信号在 9 月 1 日 20:15 至 9 月 2 日 03:40 生效。同表的暴雨警告部分记录黑雨从 9 月 7 日 23:05 持续至 9 月 8 日 15:40。天气表将对应跨午夜日期标记为 1。[天文台 2023 年 9 月月报](https://www.weather.gov.hk/en/publica/mws/files/mws202309.pdf)

## H5 单因素结果

| 天气条件 | 符合条件天数 | 符合条件日均北上人次 | 其余日均北上人次 | 差幅 | Welch p 值 |
|---|---:|---:|---:|---:|---:|
| 可测量降雨 | 548 | 246,033 | 256,637 | −4.1% | .022 |
| 雨量 ≥30 mm | 107 | 229,293 | 254,341 | −9.8% | .005 |
| 最高气温 ≥33°C | 196 | 251,270 | 252,562 | −0.5% | .827 |
| 8 号或以上风球 | 16 | 123,721 | 253,903 | −51.3% | <.001 |
| 红雨或黑雨 | 33 | 227,608 | 252,990 | −10.0% | .101 |

**答案**：H5 获得部分支持。日总雨量和北上人次弱负相关（Pearson r = −.134，Spearman ρ = −.074）。8 号或以上风球日的客流差距最大。最高气温与北上人次的 Pearson r = .008，33°C 分组也没有明显差距。红雨或黑雨日均值较低，常用 5% 水平下证据不足。

**未证明**：天气对北上出行的因果效应。上述比较按日直接分组，未控制周末、节假日、季节或长期趋势。风球与红黑雨可出现在同一天，相邻警告日也可能属于同一个天气系统。p 值是未经多重比较和序列相关校正的单因素参考值。多因素模型由成员 E 负责。

## 数据来源

天气源由香港天文台发布。香港特别行政区政府及相关机构保有源材料的知识产权。

- [最高气温开放数据](https://data.gov.hk/en-data/dataset/hk-hko-rss-daily-temperature-info-hko)
- [每日雨量开放数据](https://data.gov.hk/en-data/dataset/hk-hko-rss-daily-total-rainfall)
- [2026 年 10 月逐日观测](https://www.weather.gov.hk/wxinfo/pastwx/metob202610.htm) · [月报](https://my.weather.gov.hk/en/wxinfo/pastwx/mws2026/mws202610.htm)
- [热带气旋信号数据库](https://www.weather.gov.hk/en/wxinfo/climat/warndb/warndb1.shtml) · [暴雨警告数据库](https://www.weather.gov.hk/en/wxinfo/climat/warndb/warndb3.shtml)
- [入境事务处每日出入境统计](https://www.immd.gov.hk/eng/stat_2026.html)
- [DATA.GOV.HK 使用条款](https://data.gov.hk/en/terms-and-conditions) · [天文台网站材料使用条件](https://www.hko.gov.hk/en/appweb/applink.htm)
