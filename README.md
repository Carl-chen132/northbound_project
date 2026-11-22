# Multivariate Correlation Analysis of Hong Kong Residents' Northbound Travel

The main sample runs from 2023-02-06 to 2026-10-31. The unit of analysis is the day; the port tables are date × port. Raw and processed data live in `data/raw/` and `data/processed/` respectively.

## Environment and running

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
python main.py analyze
```
`analyze` builds the multiple regression (HAC standard errors, VIF, interaction terms, subsamples, trend robustness) and machine-learning results from the frozen `master_daily.csv`, writing to `results/member_e/` and `figures/member_e/`.
It does not re-scrape data or rewrite the frozen dataset. The full rebuild pipeline is `python main.py`.
Result tables are in `results/member_e/`: `regression_main`, `regression_school_break`, `regression_interaction`, `regression_subsamples`, `regression_model_comparison`, `regression_robustness`, `vif_main`, `model_comparison`, `feature_importance`;
figures are in `figures/member_e/`.
