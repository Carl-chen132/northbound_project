"""Combine the group inputs into the daily and date-by-port tables."""

from pathlib import Path

import numpy as np
import pandas as pd

from .weather_features import END_DATE, START_DATE, WEATHER_CSV, build_weather_features, check_weather

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
DATES = pd.date_range(START_DATE, END_DATE, name="Date")
PASSENGERS = "Northbound_Passengers"


def read_daily(path):
    """Accept Member A's Date and Members B/C's date headers."""
    data = pd.read_csv(path, float_precision="round_trip").rename(columns={"date": "Date"})
    data["Date"] = pd.to_datetime(data["Date"], format="%Y-%m-%d")
    return data.sort_values("Date", kind="stable")


def build_economic_features(raw_dir=RAW, dates=DATES):
    fx = read_daily(raw_dir / "fx_frankfurter_daily.csv").set_index("Date")["hkd_cny"]
    fred = read_daily(raw_dir / "fx_fred_daily.csv").set_index("Date")["fred_hkd_cny"]
    daily_index = pd.date_range(dates[0] - pd.Timedelta(days=30), dates[-1], name="Date")

    # Align to calendar days before calculating the 30-calendar-day change.
    fx_daily = fx.reindex(fx.index.union(daily_index)).sort_index().ffill().reindex(daily_index)
    fred_daily = fred.reindex(fred.index.union(dates)).sort_index().ffill().reindex(dates)

    # The most recent trading-day return strictly before each travel date.
    close = read_daily(raw_dir / "hsi_daily.csv").set_index("Date")["Close"]
    previous_return = close.pct_change(fill_method=None)
    previous_return.index += pd.Timedelta(days=1)
    previous_return = previous_return.reindex(previous_return.index.union(dates)).sort_index().ffill()

    return pd.DataFrame({
        "hkd_cny": fx_daily.reindex(dates),
        "hkd_cny_30d_change": fx_daily.pct_change(30, fill_method=None).reindex(dates),
        "fred_hkd_cny": fred_daily,
        "hsi_prev_return": previous_return.reindex(dates),
    }).reset_index()


def build_master(passenger, calendar, weather, economic, dates=DATES):
    # C's draft was built before weather. Keep the calendar classifications
    # and apply its highest-priority branch once the real warning flags are joined.
    calendar = calendar.drop(columns="is_typhoon", errors="ignore")
    master = pd.DataFrame({"Date": dates})
    for data in (passenger, calendar, weather, economic):
        master = master.merge(data, on="Date", how="left", validate="one_to_one")
    master.loc[master["is_typhoon"].eq(1), "day_type"] = "typhoon"
    master["mainland_holiday_name"] = master["mainland_holiday_name"].fillna("")
    master["year"] = master["Date"].dt.year
    master["month"] = master["Date"].dt.month
    master["time_index"] = (master["Date"] - dates[0]).dt.days
    return master


def build_port_daily(port_passenger, master):
    # A's cleaner also writes port_daily.csv. Drop only D's joined fields
    # when the input is already enriched so that reruns give the same result.
    port_passenger = port_passenger.drop(
        columns=master.columns.difference(["Date", PASSENGERS]), errors="ignore"
    )
    return port_passenger.merge(
        master.drop(columns=PASSENGERS),
        on="Date", how="left", validate="many_to_one",
    )


def check_merged(master, ports, dates=DATES):
    if not pd.DatetimeIndex(master["Date"]).equals(dates):
        raise ValueError("master_daily has missing, duplicate or out-of-order dates")
    missing = master.isna().sum().loc[lambda counts: counts.gt(0)]
    if not missing.empty:
        raise ValueError(f"Missing inputs by column: {missing.to_dict()}")
    if master[PASSENGERS].le(0).any() or master["Mainland_Arrivals"].lt(0).any():
        raise ValueError("Invalid daily passenger count")
    if ports.duplicated(["Date", "Control Point"]).any() or ports["day_type"].isna().any():
        raise ValueError("Duplicate port-date keys or missing merged port dates")
    daily_ports = ports.groupby("Date").agg(
        passengers=("Hong Kong Residents", "sum"), share=("Port_Share", "sum")
    )
    master_counts = master.set_index("Date")[PASSENGERS]
    port_counts = ports["Date"].map(master_counts)
    if (
        not daily_ports["passengers"].equals(master_counts.rename("passengers"))
        or not np.allclose(daily_ports["share"], 1)
        or not ports[PASSENGERS].eq(port_counts).all()
        or not np.allclose(ports["Port_Share"], ports["Hong Kong Residents"] / port_counts)
    ):
        raise ValueError("Port counts or shares disagree with the daily table")


def merge_project_data():
    weather = build_weather_features()
    check_weather(weather)
    master = build_master(
        read_daily(PROCESSED / "passenger_daily.csv"),
        read_daily(PROCESSED / "calendar_features_c_draft.csv"),
        weather,
        build_economic_features(),
    )
    ports = build_port_daily(read_daily(PROCESSED / "port_daily.csv"), master)
    check_merged(master, ports)
    for data, path in (
        (weather, WEATHER_CSV),
        (master, PROCESSED / "master_daily.csv"),
        (ports, PROCESSED / "port_daily.csv"),
    ):
        data.to_csv(path, index=False, encoding="utf-8-sig")
    return master, ports


if __name__ == "__main__":
    # Layer 1. Two ports with 60 and 40 passengers get the same weather flag.
    day = pd.Timestamp("2023-09-01")
    example_ports = pd.DataFrame({"Date": [day, day], PASSENGERS: [100, 100], "Port_Share": [.6, .4]})
    example_master = pd.DataFrame({"Date": [day], PASSENGERS: [100], "is_typhoon": [1]})
    assert build_port_daily(example_ports, example_master)["is_typhoon"].tolist() == [1, 1]
    # Layer 2 runs on all dates. Layer 3 spot checks appear in docs/member_d.md.
    master, ports = merge_project_data()
    print(f"master_daily.csv: {len(master):,} dates")
    print(f"port_daily.csv: {len(ports):,} date/port rows")
