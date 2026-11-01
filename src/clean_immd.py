import pandas as pd
from pathlib import Path

# 项目文件夹
BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw" / "immd_daily.csv"
OUTPUT = BASE / "data" / "processed"

# 研究口岸
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
    # 读取原始数据
    df = pd.read_csv(RAW)

    # 日期转换
    df["Date"] = pd.to_datetime(
        df["Date"],
        format="%d-%m-%Y"
    )

    # 筛选研究时间和口岸
    df = df[
        df["Date"].between(
            "2023-02-06", "2026-10-31"
        ) &
        df["Control Point"].isin(PORTS)
    ].copy()
# 将原落马洲和新皇岗统一为同一个研究口岸
    df["Control Point"] = df["Control Point"].replace({
    "Lok Ma Chau": "Lok Ma Chau / Huanggang",
    "Huanggang": "Lok Ma Chau / Huanggang"
})
    
    # 按日期、口岸和方向汇总
    grouped = df.groupby(
        ["Date", "Control Point", "Arrival / Departure"],
        as_index=False
    )[["Hong Kong Residents", "Mainland Visitors"]].sum()

    # 出境数据
    departure = grouped[
        grouped["Arrival / Departure"] == "Departure"
    ].copy()

    # 入境数据
    arrival = grouped[
        grouped["Arrival / Departure"] == "Arrival"
    ].copy()

    # Y1：每日香港居民出境
    y1 = departure.groupby("Date")[
        "Hong Kong Residents"
    ].sum().rename("Northbound_Passengers")

    # Y3：每日内地访客入境
    y3 = arrival.groupby("Date")[
        "Mainland Visitors"
    ].sum().rename("Mainland_Arrivals")

    # Y4：香港居民净出境
    hk_arrival = arrival.groupby("Date")[
        "Hong Kong Residents"
    ].sum()

    y4 = (y1 - hk_arrival).rename(
        "Net_Departure"
    )

    # 合并每日数据
    daily = pd.concat([y1, y3, y4], axis=1)
    daily = daily.reset_index()

    # Y2：口岸份额
    port = departure.merge(
        y1.reset_index(),
        on="Date",
        how="left"
    )

    port["Port_Share"] = (
        port["Hong Kong Residents"] /
        port["Northbound_Passengers"]
    )

    # 保存数据
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
