"""H6: exploratory changes in cross-border port shares near 2023-07-01.

Run from the project's root or any working directory:
    python src/h6_port_regression.py

Requires: pandas, numpy, matplotlib, statsmodels.
Reads data/processed/port_daily.csv.
Writes outputs/h6/*.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm

BASE = Path(__file__).resolve().parent.parent
INPUT = BASE / 'data' / 'processed' / 'port_daily.csv'
OUTPUT = BASE / 'outputs' / 'h6'
POLICY = pd.Timestamp('2023-07-01')
WINDOW_DAYS = 90


def get_data():
    df = pd.read_csv(INPUT, parse_dates=['Date'])
    required = {'Date', 'Control Point', 'Port_Share', 'Hong Kong Residents', 'Northbound_Passengers'}
    if not required.issubset(df.columns):
        raise ValueError(f'Missing columns: {sorted(required - set(df.columns))}')
    if df.duplicated(['Date', 'Control Point']).any():
        raise ValueError('Duplicate port/date pairs; check input.')
    if df[list(required - {'Date', 'Control Point'})].isna().any().any():
        raise ValueError('Missing numeric values; check input.')
    sums = df.groupby('Date')['Port_Share'].sum()
    if not np.allclose(sums.to_numpy(), 1, atol=1e-5):
        raise ValueError('Port shares do not sum to 1 for some dates.')
    return df.sort_values(['Control Point', 'Date'])


def estimate(df, port, days):
    start = POLICY - pd.Timedelta(days=days)
    end = POLICY + pd.Timedelta(days=days - 1)
    subset = df.loc[(df['Control Point'] == port) & (df['Date'].between(start, end))].copy()
    if len(subset) != 2 * days:
        raise ValueError(f'{port}: Expected {2 * days} daily rows, got {len(subset)}')
    subset['t'] = (subset['Date'] - POLICY).dt.days.astype(float)
    subset['post'] = (subset['Date'] >= POLICY).astype(float)
    subset['post_t'] = subset['t'].clip(lower=0)
    subset['weekend'] = (subset['Date'].dt.dayofweek >= 5).astype(float)
    # Model permits different pre/post slopes: post is discontinuity at policy date.
    X = sm.add_constant(subset[['t', 'post', 'post_t', 'weekend']], has_constant='add')
    y = subset['Port_Share'] * 100  # percentage points
    result = sm.OLS(y, X).fit(cov_type='HAC', cov_kwds={'maxlags': 7})
    ci = result.conf_int().loc['post']
    return dict(port=port, window_days=days, n=len(subset),
                pre_mean_pp=float(y[subset['post'] == 0].mean()),
                post_mean_pp=float(y[subset['post'] == 1].mean()),
                raw_difference_pp=float(y[subset['post'] == 1].mean() - y[subset['post'] == 0].mean()),
                regression_step_pp=float(result.params['post']),
                ci_lower_pp=float(ci.iloc[0]), ci_upper_pp=float(ci.iloc[1]),
                p_value=float(result.pvalues['post']),
                slope_change_pp_per_day=float(result.params['post_t']),
                r_squared=float(result.rsquared)), result


def main():
    df = get_data()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    ports = sorted(df['Control Point'].unique())
    results = []
    detail = []
    for days in (90, 120):
        for port in ports:
            record, model = estimate(df, port, days)
            results.append(record)
            if days == WINDOW_DAYS:
                table = pd.DataFrame({'variable': model.params.index,
                                      'coefficient': model.params.values,
                                      'std_error_hac': model.bse.values,
                                      'p_value': model.pvalues.values})
                table['port'] = port
                detail.append(table)
    results = pd.DataFrame(results)
    results.to_csv(OUTPUT / 'h6_regression_results.csv', index=False, encoding='utf-8-sig')
    pd.concat(detail, ignore_index=True).to_csv(OUTPUT / 'h6_model_coefficients.csv', index=False, encoding='utf-8-sig')

    # Visualization: local 90-day before/after 7-day rolling mean of each port's share.
    window = df.loc[df['Date'].between(POLICY - pd.Timedelta(days=WINDOW_DAYS),
                                       POLICY + pd.Timedelta(days=WINDOW_DAYS - 1))]
    pivot = window.pivot(index='Date', columns='Control Point', values='Port_Share') * 100
    rolling = pivot.rolling(7, min_periods=1).mean()
    fig, ax = plt.subplots(figsize=(13, 6.5))
    for port in ports:
        ax.plot(rolling.index, rolling[port], linewidth=1.4, label=port)
    ax.axvline(POLICY, linestyle='--', linewidth=1.5, label='Policy date: 2023-07-01')
    ax.set(title='Port shares around 1 July 2023 (7-day rolling mean)',
           xlabel='Date', ylabel='Share of selected ports (%)')
    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUTPUT / 'h6_regression_chart.png', dpi=200, bbox_inches='tight')
    plt.close(fig)

    print('H6 local interrupted-time-series estimates (90-day window, HAC maxlags=7)')
    print(results[results.window_days == 90][['port', 'raw_difference_pp', 'regression_step_pp',
                                             'ci_lower_pp', 'ci_upper_pp', 'p_value']].round(4).to_string(index=False))
    print(f'\nSaved to: {OUTPUT}')
    print('NOTE: descriptive associations only. Correlations and share movements do not prove substitution or causality.')


if __name__ == '__main__':
    main()
