"""Build daily weather variables X11–X14 from Hong Kong Observatory records."""

import csv
from datetime import datetime
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RAW_WEATHER = ROOT / "data" / "raw" / "weather"
WEATHER_CSV = ROOT / "data" / "processed" / "weather_daily.csv"
START_DATE = "2023-02-06"
END_DATE = "2026-10-31"


def read_climate_csv(path, name):
    """Skip the bilingual title and footer. Keep incomplete readings missing."""
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = csv.reader(file)
        next(rows)
        next(rows)
        header = next(rows)
        if [field.split("/")[-1] for field in header[:4]] != ["Year", "Month", "Day", "Value"]:
            raise ValueError(f"Unexpected HKO header in {path.name}")
        records = [
            row[:5] for row in rows
            if row and row[0].isdigit() and START_DATE[:4] <= row[0] <= END_DATE[:4]
        ]

    data = pd.DataFrame(records, columns=["year", "month", "day", "value", "status"])
    dates = pd.to_datetime(data[["year", "month", "day"]])
    readings = pd.to_numeric(data["value"].replace({"Trace": "0", "***": ""}), errors="raise")
    return pd.Series(readings.where(data["status"].eq("C")).to_numpy(), index=dates, name=name)


def read_monthly_extract(path, year, month):
    """Use the first HKO station table in the monthly observations page."""
    soup = BeautifulSoup(path.read_bytes(), "html.parser")
    records = []
    for day in soup.select('td[headers="date"][axis="day"]'):
        row = day.parent
        maximum = row.select_one('td[headers~="tma"]').get_text(strip=True)
        rain = row.select_one('td[headers~="rf"]').get_text(strip=True)
        records.append((pd.Timestamp(year, month, int(day.text)), maximum, rain))
    data = pd.DataFrame(records, columns=["Date", "tmax_c", "rainfall_mm"]).set_index("Date")
    data["rainfall_mm"] = data["rainfall_mm"].replace({"-": "0", "Trace": "0", "Tr": "0"})
    return data.replace({"***": None}).astype(float)


def cyclone_time(clock, day, month, year):
    """Convert the database's HHMM and day/month/year fields to Hong Kong time."""
    return datetime.strptime(f"{year}-{month}-{day} {clock.zfill(4)}", "%Y-%m-%d %H%M")


def warning_dates(path, kind, dates):
    """Mark every local date that overlaps a qualifying warning interval."""
    active = set()
    records = 0
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip() or line.strip() == "UUUU":
            continue  # HKO separates provisional rows with UUUU.
        fields = line.split("\t")
        if kind == "cyclone":
            storm_id, signal = fields[0], fields[3]
            if not (storm_id[:4].isdigit() and signal in {"8", "9", "10"}):
                continue
            if not str(dates[0].year - 1) <= storm_id[:4] <= str(dates[-1].year):
                continue
            start, end = cyclone_time(*fields[5:9]), cyclone_time(*fields[10:14])
        else:
            colour = fields[0]
            if colour not in {"R", "B"} or not dates[0].year - 1 <= int(fields[1]) <= dates[-1].year:
                continue
            start, end = datetime(*map(int, fields[1:6])), datetime(*map(int, fields[6:11]))
        if end <= start:
            raise ValueError(f"Invalid warning interval in {path.name}: {line}")
        records += 1
        # A warning cancelled at 00:00 did not operate on the cancellation date.
        last_active = pd.Timestamp(end) - pd.Timedelta(microseconds=1)
        active.update(pd.date_range(pd.Timestamp(start).normalize(), last_active.normalize()))
    if not records:
        raise ValueError(f"No qualifying warnings parsed from {path.name}")
    return dates.isin(active).astype(int)


def build_weather_features(raw_dir=RAW_WEATHER):
    dates = pd.date_range(START_DATE, END_DATE, name="Date")
    tmax = pd.concat(
        [read_climate_csv(raw_dir / f"hko_tmax_{year}.csv", "tmax_c")
         for year in range(dates[0].year, dates[-1].year + 1)],
        verify_integrity=True,
    )
    rainfall = read_climate_csv(raw_dir / "hko_rainfall.csv", "rainfall_mm")
    daily = pd.concat([tmax.reindex(dates), rainfall.reindex(dates)], axis=1)
    if daily.isna().any().any():
        # The frozen climate CSVs stop at September 2026. The extract uses the same HKO station.
        extract = read_monthly_extract(raw_dir / "metob202610.htm", 2026, 10)
        daily = daily.fillna(extract)
    daily["is_very_hot"] = daily["tmax_c"].ge(33).where(daily["tmax_c"].notna()).astype("Int64")
    daily["is_heavy_rain"] = daily["rainfall_mm"].ge(30).where(daily["rainfall_mm"].notna()).astype("Int64")
    daily["is_typhoon"] = warning_dates(raw_dir / "tc.dat", "cyclone", dates)
    daily["is_red_black_rain"] = warning_dates(raw_dir / "rstorm.dat", "rain", dates)
    daily.index.name = "Date"
    return daily.reset_index()


def check_weather(daily):
    """Layer 2 uses real-data coverage, ranges and the two official spot checks."""
    expected = pd.date_range(START_DATE, END_DATE)
    if not pd.DatetimeIndex(daily["Date"]).equals(expected):
        raise ValueError("Weather dates are incomplete or out of order")
    if not daily["tmax_c"].between(0, 40).all() or not daily["rainfall_mm"].ge(0).all():
        raise ValueError("Missing or invalid daily temperature or rainfall")
    spot = daily.set_index("Date")
    assert spot.loc["2023-09-01", "is_typhoon"] == 1
    assert spot.loc["2023-09-08", "is_red_black_rain"] == 1


if __name__ == "__main__":
    # Layer 1. A 02:40 HKT start parsed from the raw HHMM field.
    assert cyclone_time("240", "1", "9", "2023") == datetime(2023, 9, 1, 2, 40)
    weather = build_weather_features()
    check_weather(weather)
    WEATHER_CSV.parent.mkdir(parents=True, exist_ok=True)
    weather.to_csv(WEATHER_CSV, index=False)
    # Layer 3. See the HKO September 2023 source and comparison in docs/member_d.md.
    print(f"{WEATHER_CSV.name}: {len(weather)} days")
