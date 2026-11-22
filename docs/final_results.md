# Final Results and Reporting Narrative (Member E)

Sample: 2023-02-06 to 2026-10-31, 1,364 daily observations. Passenger flows are log-transformed; daily regressions are OLS with Newey-West (HAC, maxlags=7). All conclusions describe correlations only; no causal interpretation is made.

Hypothesis numbering and directions follow Section 2 of the design PDF (H1 exchange rate, H2 weekends and Hong Kong holidays, H3 Hong Kong school long holidays, H4 mainland holidays and the Shenzhen school calendar, H5 weather, H6 Hong Kong vehicles northbound and port share, H7 monthly retail). H7 was delivered by Member B (`results/member_b/h7_retail_correlations.csv`); the H6 port-share results are in `results/member_a/h6_monthly_shares.csv`, with notes in "H6 Supplementary Notes" below.

## H1–H7 evidence table

| No. | Hypothesis and expected direction (design PDF) | Main results | Conclusion |
|---|---|---|---|
| H1 | The cheaper the RMB is relative to the HKD, the more Hong Kong residents travel north (positive correlation) | Regression: main specification β=3.160 (HAC p<.001, elasticity about +2.87% per 1%); after removing the time trend β=-1.682 (p<.001); with a quadratic trend β=1.168 (p=.121). B's univariate correlation (no other controls) shows the same direction: raw daily r=-.128, r=+.319 after removing weekday and trend (p<.001) | **Not robustly supported**: both independent paths show the sign flips with trend controls, so it cannot be reported as "a stronger exchange rate brings more passengers" |
| H2 | Northbound trips are higher on weekends, Hong Kong public holidays, and long weekends than on ordinary weekdays (positive correlation) | Weekend +33.8%, Hong Kong public holiday +31.5%, day before holiday +39.3% (all p<.001); long weekend only +2.3% (p=.56) | **Partially supported**: weekends and holidays hold, long weekends are not significant |
| H3 | Northbound travel is higher during Hong Kong school long holidays, with a smaller effect for short holidays (positive correlation) | In the school-holiday specification, Hong Kong school long holiday +5.9% (p=.031); the Hong Kong school short-holiday field is all zeros in the frozen sample | **Partially supported**: the long-holiday direction holds but the magnitude is small; short holidays cannot be tested |
| H4 | Northbound travel falls during mainland Golden Weeks and Shenzhen school holidays (negative correlation) | Mainland public holiday -15.8% (holiday specification, p<.001); Shenzhen winter break -1.2% (p=.66), summer break -2.8% (p=.34) | **Partially supported**: the negative mainland-holiday correlation holds; Shenzhen school-calendar variables are not significant |
| H5 | Northbound travel falls on rainy, hot, T8-typhoon, or black-rain days (negative correlation) | Typhoon signal 8 or above -57.9% (p<.001); rainfall -0.19% per mm (p=.016); maximum temperature, red/black rain, and heavy rain are not significant | **Partially supported**, consistent in direction with D's univariate results |
| H6 | After the Hong Kong vehicles northbound scheme, the Hong Kong resident share at the HZMB port rises (positive correlation) | 90-day before/after means 11.9%→10.7% (**-1.2pp**); the share had already fallen from 14.3% to 10.8% in the five months before the policy, was 11.0% in the policy month, and averaged 10.4% over the following 12 months, essentially flat; quarterly means 13.5%→9.5%. Monthly trend in `figures/member_a/h6_monthly_share.png` | **Not supported**: no post-policy rise as expected; the decline occurred mainly before the policy; descriptive judgment only, no causal interpretation |
| H7 | The higher monthly northbound trips are, the lower Hong Kong retail sales value is (negative correlation) | Delivered by Member B (`results/member_b/h7_retail_correlations.csv`): same-month levels, 43 months r=-.097 (p=.536); retail leading by one month, 42 months r=-.093 (p=.559); using percentage changes, same month r=+.258 (p=.099), leading by one month r=-.059 (p=.714) | **Not supported**: neither levels nor change rates are significant, and the direction is unstable |

### H6 Supplementary Notes (Hong Kong vehicles northbound and port share)

- **Definition**: `Port_Share` is the Hong Kong resident outbound trips at a port as a share of the daily total across the 7 ports; the new Huanggang is merged into `Lok Ma Chau / Huanggang`. Sample 2023-02-06 to 2026-10-31.
- **Observation**: 90-day before/after means 11.9%→10.7% (**-1.2pp**). The share had already fallen from 14.3% to 10.8% in the five months before the policy; it was 11.0% in the policy month and averaged 10.4% over the following 12 months (9.2%–11.7%), essentially flat. Quarterly means fell from 13.5% in 2023Q1 to 9.5% in 2026Q4. Monthly trend in `figures/member_a/h6_monthly_share.png`, data in `results/member_a/h6_monthly_shares.csv`.
- **Conclusion**: H6 is not supported—no post-policy rise as expected, and the decline occurred mainly before the policy; the policy date overlaps with the post-pandemic recovery trend, so this is a descriptive judgment only, not a causal interpretation.
- **Note**: A local regression controlling for a linear trend produces a positive break of +1.6pp, but it is not robust to the window or to placebo dates (`results/member_a/h6_robustness.csv`, `results/member_a/h6_placebo.csv`), so the regression conclusion is not used in the main text.

## Supplementary analysis: machine learning

Under 5-fold time-series validation, gradient boosting + historical passenger flow has MAE 33,708 (10.4% lower than the "same weekday last week" baseline), and random forest + historical passenger flow is 7.4% lower; using only the 18 factors, gradient boosting is 9.1% lower while random forest is 1.1% higher. Top five permutation importances: day of week (0.064), weekend (0.0076), daily rainfall (0.0042), day before holiday (0.0032), typhoon signal 8 (0.0016). Predictive power is not explanatory effect, and permutation importance does not indicate direction.

Note: day of week and weekend are highly redundant; permutation importance assigns almost all the score to the more granular day of week, so the weekend value of 0.0076 cannot be read as "weekends do not matter"; the calendar cycle totals about 0.072 and is the model's most important information.

## Regression and robustness highlights

- Main specification R²=0.695, n=1,364. R² is sample fit, not predictive accuracy.
- In the main specification the time trend has VIF=17.57 (because it moves together with the exchange rate and policy dummies); under the no-trend or quadratic-trend specifications the exchange-rate coefficient is unstable, so H1 can only be written as "not robustly supported". The exchange-rate coefficients under all three specifications are in `results/member_e/regression_robustness.csv`.
- The VIFs of the quadratic and linear trends are about 111.2 and 69.5 respectively; the quadratic-trend specification is itself severely collinear and cannot be treated as the "correct model". The robustness results are meant to show that conclusions are sensitive, not to pick one as correct.
- The school-holiday specification retains the Shenzhen winter/summer breaks and Hong Kong long holidays; the Shenzhen spring/autumn breaks and Hong Kong short-holiday fields are constant in the frozen sample and are automatically dropped by the regression. The ML model uses 23 non-historical features: 18 core factors, 3 available school-holiday flags, month, and day of week.
- VIF applies only to the main specification; the interaction, subsample, and school-holiday specifications do not have their own VIF summaries, so do not imply that all specifications passed collinearity checks.
- Subsamples automatically drop constants and perfectly collinear columns; in window A the June and December dummies are perfectly collinear with the remaining controls, so they are not estimated separately and the coefficient table contains only identifiable parameters.

## Reporting suggestions

1. State the method and definitions: log passenger flow OLS + HAC, controlling for calendar, weather, market, and trend; machine learning uses time-series cross-validation and is compared with the "same weekday last week" baseline.
2. Report the robust conclusions first: H2 weekends/Hong Kong holidays/day before holiday higher, mainland holidays lower; H5 severe typhoons significantly depress passenger flow; ML with historical passenger flow beats the baseline.
3. Proactively state the limitations: H1's exchange rate is sensitive to trend specifications, and B's univariate correlation also reproduces the sign flip; H7 was delivered by B and is not supported; H6 shows no post-policy rise in share as expected, so it can only be written as "not supported", not "the bridge's share rose". No result supports causal wording.
4. Describe each hypothesis using the four-level scale "supported / partially supported / not supported / opposite direction", and keep "no significant evidence" separate from "proven to have no effect".

## Reproduction

```bash
python main.py analyze            # regression + machine learning, writes all CSVs under results/member_e/
python -m src.stats_analysis      # regression only (with hand-calculation checks and robustness tables)
python -m src.ml_model            # machine learning and the two figures only
python -m src.h6_monthly          # H6 monthly shares and descriptive comparison (used in the main text)
python -m src.h6_port_regression  # appendix: H6 local regression and coefficients
python -m src.h6_robustness       # appendix: H6 window/specification sensitivity and placebo
```

Three-layer checks: `stats_analysis.check_fit()` and `ml_model.check_history()` are hand-calculation examples; `check_sample()` in both modules validates the frozen data by row count, date continuity, and value ranges; the manual check is that the 2023-09-01 raw CSV and the master table both show 26,311 passenger trips.
