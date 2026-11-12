"""Run the whole northbound project pipeline from the repository root.

    python main.py            # run every stage in order
    python main.py fetch      # download the raw snapshots main.py owns
    python main.py clean      # rebuild passenger, calendar and weather tables
    python main.py merge      # rebuild master_daily.csv and port_daily.csv
    python main.py eda        # redraw the figures and H5 summary tables
    python main.py analyze    # regression and machine-learning stages

Only the plain file downloads live here. Frankfurter, FRED, Yahoo Finance and
the 1823 holiday JSON are fetched by notebooks 02 and 03, which need API keys or
extra parsing; run those notebooks first if their outputs are missing.

The analyze stage expects `src.stats_analysis.run_analysis()` and
`src.ml_model.run_models()`. A module that is not written yet is reported and
skipped, so the rest of the pipeline still runs.

Stage order matters: clean writes the raw passenger and port tables, merge
enriches the port table in place, and eda only reads the merged results.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
WEATHER_RAW = RAW / "weather"

IMMD_URL = (
    "https://www.immd.gov.hk/opendata/eng/transport/immigration_clearance/"
    "statistics_on_daily_passenger_traffic.csv"
)
CLIMATE_API = "https://data.weather.gov.hk/weatherAPI"
WARNING_DB = "https://www.weather.gov.hk/dps/wxinfo/climat/warndb"

# Raw snapshots whose source is a single GET.
SNAPSHOTS = {
    RAW / "immd_daily.csv": IMMD_URL,
    WEATHER_RAW / "hko_rainfall.csv": f"{CLIMATE_API}/cis/csvfile/HKO/ALL/daily_HKO_RF_ALL.csv",
    WEATHER_RAW / "metob202610.htm": "https://www.weather.gov.hk/wxinfo/pastwx/metob202610.htm",
    WEATHER_RAW / "tc.dat": f"{WARNING_DB}/tc.dat",
    WEATHER_RAW / "rstorm.dat": f"{WARNING_DB}/rstorm.dat",
}
for year in range(2023, 2027):
    SNAPSHOTS[WEATHER_RAW / f"hko_tmax_{year}.csv"] = (
        f"{CLIMATE_API}/opendata/opendata.php"
        f"?dataType=CLMMAXT&year={year}&rformat=csv&station=HKO"
    )

# Snapshots owned by Members B and C; main.py never writes them.
EXTERNAL_INPUTS = (
    RAW / "fx_frankfurter_daily.csv",
    RAW / "fx_fred_daily.csv",
    RAW / "hsi_daily.csv",
    RAW / "csd_retail_monthly.csv",
    PROCESSED / "hk_public_holidays_2023_2027.csv",
    PROCESSED / "mainland_calendar_2023_2026.csv",
)

CALENDAR_STEPS = (
    "add_hk_public_holiday",
    "add_hk_holiday_features",
    "add_mainland_calendar",
    "add_policy_features",
    "add_payday_period",
    "add_sz_school_break_features",
    "add_hk_school_break_features",
    "add_day_type",
)

CALENDAR_CSV = PROCESSED / "calendar_features_c_draft.csv"


def require(*paths):
    """Stop with a readable message when an input is missing."""
    missing = [path for path in paths if not path.exists()]
    if not missing:
        return
    for path in missing:
        print(f"  missing {path.relative_to(ROOT)}")
    raise SystemExit(
        "Required input missing. Run the stage that produces it, or the notebook "
        "listed in the module docstring."
    )


def download(path, url, force=False):
    """Write one snapshot to disk; keep an existing copy unless forced."""
    if path.exists() and not force:
        print(f"  skip  {path.relative_to(ROOT)}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    path.write_bytes(response.content)
    print(f"  saved {path.relative_to(ROOT)} ({len(response.content) / 1024:,.0f} KB)")
    return True


def fetch(force=False):
    """Download the snapshots whose source is a plain file."""
    saved = sum(download(path, url, force=force) for path, url in SNAPSHOTS.items())
    print(f"fetch done: {saved} downloaded, {len(SNAPSHOTS) - saved} reused")
    return saved


def clean():
    """Rebuild the three cleaned inputs that merge_data.py expects."""
    from src import calendar_features, clean_immd, weather_features

    require(RAW / "immd_daily.csv", *EXTERNAL_INPUTS,
            *[p for p in SNAPSHOTS if p.parent == WEATHER_RAW])

    print("passenger table (Member A)")
    clean_immd.clean_passenger_data()

    print("calendar table (Member C)")
    calendar = calendar_features.build_base_calendar()
    for name in CALENDAR_STEPS:
        calendar = getattr(calendar_features, name)(calendar)
    CALENDAR_CSV.parent.mkdir(parents=True, exist_ok=True)
    calendar.to_csv(CALENDAR_CSV, index=False, encoding="utf-8")
    print(f"  saved {CALENDAR_CSV.relative_to(ROOT)}: {len(calendar):,} dates")

    print("weather table (Member D)")
    weather = weather_features.build_weather_features()
    weather_features.check_weather(weather)
    weather_features.WEATHER_CSV.parent.mkdir(parents=True, exist_ok=True)
    weather.to_csv(weather_features.WEATHER_CSV, index=False)
    print(f"  saved {weather_features.WEATHER_CSV.relative_to(ROOT)}: {len(weather):,} days")


def merge():
    """Combine every cleaned input into the two analysis tables."""
    from src.merge_data import merge_project_data

    require(PROCESSED / "passenger_daily.csv", CALENDAR_CSV,
            PROCESSED / "weather_daily.csv",
            RAW / "fx_frankfurter_daily.csv", RAW / "fx_fred_daily.csv", RAW / "hsi_daily.csv")

    master, ports = merge_project_data()
    print(f"  master_daily.csv: {len(master):,} dates x {master.shape[1]} columns")
    print(f"  port_daily.csv:   {len(ports):,} date/port rows")
    return master, ports


def eda():
    """Redraw every figure and the H5 summary tables."""
    import pandas as pd

    from src import eda_plots

    require(PROCESSED / "master_daily.csv", PROCESSED / "port_daily.csv",
            RAW / "immd_daily.csv", RAW / "csd_retail_monthly.csv")

    master = pd.read_csv(PROCESSED / "master_daily.csv", parse_dates=["Date"])
    ports = pd.read_csv(PROCESSED / "port_daily.csv", parse_dates=["Date"])
    groups, correlations = eda_plots.make_figures(master, ports)
    print(f"  figures and H5 tables written to {eda_plots.FIGURES.relative_to(ROOT)}")
    return groups, correlations


def analyze():
    """Run the regression and machine-learning stages when their modules exist."""
    skipped = []
    for module_name, function_name in (
        ("src.stats_analysis", "run_analysis"),
        ("src.ml_model", "run_models"),
    ):
        require(PROCESSED / "master_daily.csv", PROCESSED / "port_daily.csv")
        try:
            module = __import__(module_name, fromlist=[function_name])
        except ImportError:
            skipped.append(module_name)
            print(f"  skipped {module_name}: module not written yet")
            continue
        getattr(module, function_name)()
    if skipped:
        print(f"  finished with {len(skipped)} stage(s) skipped: {', '.join(skipped)}")
    else:
        print("  regression and ML stages finished")


STAGES = {
    "fetch": fetch,
    "clean": clean,
    "merge": merge,
    "eda": eda,
    "analyze": analyze,
}

PIPELINE = ("fetch", "clean", "merge", "eda", "analyze")


def run(names):
    """Run the requested stages in pipeline order and time each one."""
    started = time.perf_counter()
    for name in names:
        stage_started = time.perf_counter()
        print(f"\n[{name}]")
        STAGES[name]()
        print(f"[{name}] finished in {time.perf_counter() - stage_started:.1f}s")
    print(f"\nAll done in {time.perf_counter() - started:.1f}s")


def main(argv):
    if len(argv) > 2:
        print(__doc__)
        return 2
    command = argv[1] if len(argv) == 2 else "all"
    if command == "all":
        run(PIPELINE)
    elif command in STAGES:
        run([command])
    else:
        print(f"Unknown stage: {command}\n")
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
