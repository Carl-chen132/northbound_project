import pandas as pd
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw" / "immd_daily.csv"
OUTPUT = BASE / "data" / "processed"


PORTS = [
    "Lo Wu",
    "Lok Ma Chau Spur Line",
    "Lok Ma Chau",
    "Huanggang",
    "Shenzhen Bay",
    "Heung Yuen Wai",
    "Hong Kong-Zhuhai-Macao Bridge",
    "Express Rail Link West Kowloon"
]

def clean_passenger_data():
    df = pd.read_csv(RAW)

    df["Date"] = pd.to_datetime(
        df["Date"],
        format="%d-%m-%Y"
    )

    df = df[
        df["Date"].between(
            "2023-02-06", "2026-10-31"
        ) &
        df["Control Point"].isin(PORTS)
    ].copy()

    df["Control Point"] = df["Control Point"].replace({
    "Lok Ma Chau": "Lok Ma Chau / Huanggang",
    "Huanggang": "Lok Ma Chau / Huanggang"
})
    
    grouped = df.groupby(
        ["Date", "Control Point", "Arrival / Departure"],
        as_index=False
    )[["Hong Kong Residents", "Mainland Visitors"]].sum()


    departure = grouped[
        grouped["Arrival / Departure"] == "Departure"
    ].copy()


    arrival = grouped[
        grouped["Arrival / Departure"] == "Arrival"
    ].copy()

    y1 = departure.groupby("Date")[
        "Hong Kong Residents"
    ].sum().rename("Northbound_Passengers")

    y3 = arrival.groupby("Date")[
        "Mainland Visitors"
    ].sum().rename("Mainland_Arrivals")

    hk_arrival = arrival.groupby("Date")[
        "Hong Kong Residents"
    ].sum()

    y4 = (y1 - hk_arrival).rename(
        "Net_Departure"
    )

    daily = pd.concat([y1, y3, y4], axis=1)
    daily = daily.reset_index()

    port = departure.merge(
        y1.reset_index(),
        on="Date",
        how="left"
    )

    port["Port_Share"] = (
        port["Hong Kong Residents"] /
        port["Northbound_Passengers"]
    )

    OUTPUT.mkdir(parents=True, exist_ok=True)

    daily.to_csv(
        OUTPUT / "passenger_daily.csv",
        index=False,
        encoding="utf-8-sig"
    )

    port.to_csv(
        OUTPUT / "port_daily.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("数据清洗完成！")
    print("每日数据：", daily.shape)
    print("口岸数据：", port.shape)


if __name__ == "__main__":
    clean_passenger_data()
