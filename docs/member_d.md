# 成员 D｜天气、数据合并与图表

主样本为 2023-02-06 至 2026-10-31。观察单位是日期，口岸表的观察单位是日期与口岸。总趋势图额外使用 2021-01-01 至 2023-02-05 的背景数据。

## 运行顺序

从仓库根目录运行。依赖见 `requirements.txt`。在 Jupyter 中运行取数 Notebook 需要 `ipykernel`。

1. 运行 `notebooks/01_get_immd.ipynb` 的下载单元，将入境处原始文件放在仓库根目录下的 `data/raw/immd_daily.csv`。如果已有小组冻结副本，使用该副本。随后运行 `python -m src.clean_immd` 生成客流输入表。
2. 确保成员 B 的 `fx_frankfurter_daily.csv`、`fx_fred_daily.csv`、`hsi_daily.csv`、`csd_retail_monthly.csv` 在 `data/raw/`，成员 C 的 `calendar_features_c_draft.csv` 在 `data/processed/`。本次使用 B 的 `2220974` 和 C 的 `308233a`。分支尚未合并时，从各自分支取这些文件即可。
3. 在 Jupyter 运行 `notebooks/04_get_weather.ipynb`。它会补下载缺少的原始文件并生成 `weather_daily.csv`。已有完整原始快照时，也可以运行 `python -m src.weather_features`。
4. 运行 `python -m src.merge_data`，再运行 `python -m src.eda_plots`。图表和 H5 统计表写入 `figures/member_d/`。

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
2. **实际数据**：总表有 1,364 个连续日期。口岸表有 9,548 个唯一的日期与口岸组合。每日口岸人次之和与 Y1 一致，份额之和为 100%。合并时检查输入缺失及重复日期。
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
