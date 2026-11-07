from datetime import date

START_DATE = date(2023, 2, 6)
END_DATE = date(2026, 10, 31)

POLICY_DATES = {
    "hk_cars_northbound": date(2023, 7, 1),
    "shenzhen_multiple_entry": date(2024, 12, 1),
}


# Define Shenzhen compulsory-education winter breaks
SZ_WINTER_BREAKS = [
    (date(2024, 1, 21), date(2024, 2, 19)),
    (date(2025, 1, 16), date(2025, 2, 16)),
    (date(2026, 1, 31), date(2026, 3, 1)),
]


# Define Shenzhen compulsory-education summer breaks
SZ_SUMMER_BREAKS = [
    (date(2023, 7, 14), date(2023, 8, 31)),
    (date(2024, 7, 14), date(2024, 8, 31)),
    (date(2025, 7, 13), date(2025, 8, 31)),
    (date(2026, 7, 11), date(2026, 8, 31)),
]


# No citywide spring breaks fall within the project period
SZ_SPRING_BREAKS = []


# No citywide autumn breaks fall within the project period
SZ_AUTUMN_BREAKS = []


# Define representative Hong Kong school long breaks
HK_SCHOOL_LONG_BREAKS = [
    (date(2023, 4, 5), date(2023, 4, 14)),
    (date(2023, 7, 15), date(2023, 8, 31)),
    (date(2023, 12, 23), date(2024, 1, 2)),
    (date(2024, 2, 8), date(2024, 2, 18)),
    (date(2024, 3, 28), date(2024, 4, 7)),
    (date(2024, 7, 13), date(2024, 8, 31)),
    (date(2024, 12, 23), date(2025, 1, 1)),
    (date(2025, 1, 27), date(2025, 2, 5)),
    (date(2025, 4, 17), date(2025, 4, 27)),
    (date(2025, 7, 12), date(2025, 8, 31)),
    (date(2025, 12, 24), date(2026, 1, 3)),
    (date(2026, 2, 12), date(2026, 2, 21)),
    (date(2026, 4, 3), date(2026, 4, 11)),
    (date(2026, 7, 10), date(2026, 8, 31)),
]


# Retained for future use and excluded from the current analysis
HK_SCHOOL_SHORT_BREAKS = []