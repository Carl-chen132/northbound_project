"""Create daily calendar features for the project."""

# Import Path for building reliable file paths
from pathlib import Path

# Import the pandas library
import pandas as pd

# Import project settings
try:
    from src.config import (
        END_DATE,
        POLICY_DATES,
        START_DATE,
        SZ_AUTUMN_BREAKS,
        SZ_SPRING_BREAKS,
        SZ_SUMMER_BREAKS,
        SZ_WINTER_BREAKS,        
        HK_SCHOOL_LONG_BREAKS,
        HK_SCHOOL_SHORT_BREAKS,
    )
except ModuleNotFoundError:
    from config import (
        END_DATE,
        POLICY_DATES,
        START_DATE,
        SZ_AUTUMN_BREAKS,
        SZ_SPRING_BREAKS,
        SZ_SUMMER_BREAKS,
        SZ_WINTER_BREAKS,
        HK_SCHOOL_LONG_BREAKS,
        HK_SCHOOL_SHORT_BREAKS,
    )


# Locate the project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Define the processed Hong Kong holiday file
HK_HOLIDAY_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hk_public_holidays_2023_2027.csv"
)

# Define the processed mainland calendar file
MAINLAND_CALENDAR_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "mainland_calendar_2023_2026.csv"
)


def build_base_calendar(
    start_date=START_DATE,
    end_date=END_DATE,
):
    """Create one row for every date in the project period."""

    # Generate a continuous daily date range
    calendar = pd.DataFrame({
        "date": pd.date_range(
            start=start_date,
            end=end_date,
            freq="D",
        )
    })

    # Add the English weekday name
    calendar["day_of_week"] = (
        calendar["date"].dt.day_name()
    )

    # Mark Saturday and Sunday as weekends
    calendar["is_weekend"] = (
        calendar["date"]
        .dt.day_of_week
        .isin([5, 6])
        .astype(int)
    )

    return calendar


def add_hk_public_holiday(
    calendar,
    holiday_file=HK_HOLIDAY_FILE,
):
    """Add the Hong Kong public holiday indicator."""

    # Read processed Hong Kong holiday data
    holiday_data = pd.read_csv(
        holiday_file,
        dtype={"date": str},
    )

    # Convert YYYYMMDD text into pandas dates
    holiday_dates = pd.to_datetime(
        holiday_data["date"],
        format="%Y%m%d",
    )

    # Copy the calendar to protect the original data
    result = calendar.copy()

    # Mark Hong Kong public holidays as 1
    result["is_hk_public_holiday"] = (
        result["date"]
        .isin(holiday_dates)
        .astype(int)
    )

    return result


def add_hk_holiday_features(calendar):
    """Add holiday-eve and long-weekend indicators."""

    # Copy the calendar to protect the original data
    result = calendar.copy()

    # Check whether the next day is a public holiday
    next_day_is_holiday = (
        result["is_hk_public_holiday"]
        .shift(-1, fill_value=0)
    )

    # Mark the day before a public holiday
    result["is_holiday_eve"] = (
        (next_day_is_holiday == 1)
        & (result["is_hk_public_holiday"] == 0)
    ).astype(int)

    # Treat weekends and public holidays as non-working days
    non_working_day = (
        (result["is_weekend"] == 1)
        | (result["is_hk_public_holiday"] == 1)
    ).astype(int)

    # Identify consecutive groups of working and non-working days
    group_number = (
        non_working_day
        .ne(non_working_day.shift())
        .cumsum()
    )

    # Calculate the length of each consecutive group
    group_length = (
        non_working_day
        .groupby(group_number)
        .transform("size")
    )

    # Mark non-working periods lasting at least three days
    result["is_long_weekend"] = (
        (non_working_day == 1)
        & (group_length >= 3)
    ).astype(int)

    return result


def add_mainland_calendar(
    calendar,
    mainland_file=MAINLAND_CALENDAR_FILE,
):
    """Add mainland holiday and makeup workday features."""

    # Read processed mainland calendar data
    mainland_data = pd.read_csv(
        mainland_file,
        dtype={"date": str},
    )

    # Convert YYYYMMDD text into pandas dates
    mainland_data["date"] = pd.to_datetime(
        mainland_data["date"],
        format="%Y%m%d",
    )

    # Keep only required mainland columns
    mainland_data = mainland_data[
        [
            "date",
            "is_mainland_holiday",
            "is_mainland_makeup_workday",
            "mainland_holiday_name",
        ]
    ]

    # Merge mainland features into the daily calendar
    result = calendar.merge(
        mainland_data,
        on="date",
        how="left",
        validate="one_to_one",
    )

    # Replace missing values
    result["is_mainland_holiday"] = (
        result["is_mainland_holiday"]
        .fillna(0)
        .astype(int)
    )

    result["is_mainland_makeup_workday"] = (
        result["is_mainland_makeup_workday"]
        .fillna(0)
        .astype(int)
    )

    result["mainland_holiday_name"] = (
        result["mainland_holiday_name"]
        .fillna("")
    )

    return result


def add_policy_features(calendar):
    """Add policy implementation indicators."""

    # Copy the calendar to protect the original data
    result = calendar.copy()

    # Read policy start dates
    hzmb_start_date = pd.Timestamp(
        POLICY_DATES["hk_cars_northbound"]
    )

    multi_entry_start_date = pd.Timestamp(
        POLICY_DATES["shenzhen_multiple_entry"]
    )

    # Mark dates on or after policy implementation
    result["post_hzmb_policy"] = (
        result["date"] >= hzmb_start_date
    ).astype(int)

    result["post_multi_entry_policy"] = (
        result["date"] >= multi_entry_start_date
    ).astype(int)

    return result


def add_payday_period(calendar):
    """Mark month-end days and the first weekend of each month."""

    # Copy the calendar to protect the original data
    result = calendar.copy()

    # Mark the last three calendar days of each month
    is_month_end_period = (
        result["date"].dt.day
        >= result["date"].dt.days_in_month - 2
    )

    # Find the actual first day of each calendar month
    month_start = (
        result["date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    # Calculate the actual first Saturday of each month
    days_until_saturday = (
        5 - month_start.dt.day_of_week
    ) % 7

    first_saturday = (
        month_start
        + pd.to_timedelta(
            days_until_saturday,
            unit="D",
        )
    )

    # Mark the first Saturday and Sunday of each month
    is_first_weekend = (
        (result["date"] == first_saturday)
        | (
            result["date"]
            == first_saturday
            + pd.Timedelta(days=1)
        )
    )

    # Combine the month-end period and first weekend
    result["is_payday_period"] = (
        is_month_end_period
        | is_first_weekend
    ).astype(int)

    return result


def add_date_interval_feature(
    calendar,
    date_intervals,
    column_name,
):
    """Expand date intervals into a daily binary feature."""

    # Copy the calendar to protect the original data
    result = calendar.copy()

    # Start with zero for every date
    result[column_name] = 0

    # Mark every date inside each inclusive interval
    for start_date, end_date in date_intervals:
        is_in_interval = (
            (result["date"] >= pd.Timestamp(start_date))
            & (result["date"] <= pd.Timestamp(end_date))
        )

        result.loc[
            is_in_interval,
            column_name,
        ] = 1

    return result


def add_sz_school_break_features(calendar):
    """Add Shenzhen compulsory-education school-break indicators."""

    # Add Shenzhen winter-break days
    result = add_date_interval_feature(
        calendar,
        SZ_WINTER_BREAKS,
        "is_sz_winter_break",
    )

    # Add Shenzhen summer-break days
    result = add_date_interval_feature(
        result,
        SZ_SUMMER_BREAKS,
        "is_sz_summer_break",
    )

    # Add Shenzhen spring-break days
    result = add_date_interval_feature(
        result,
        SZ_SPRING_BREAKS,
        "is_sz_spring_break",
    )

    # Add Shenzhen autumn-break days
    result = add_date_interval_feature(
        result,
        SZ_AUTUMN_BREAKS,
        "is_sz_autumn_break",
    )

    return result


def add_hk_school_break_features(calendar):
    """Add Hong Kong school long-break and short-break features."""

    # Add Hong Kong school long-break days
    result = add_date_interval_feature(
        calendar,
        HK_SCHOOL_LONG_BREAKS,
        "is_hk_school_long_break",
    )

    # Add Hong Kong school short-break days
    result = add_date_interval_feature(
        result,
        HK_SCHOOL_SHORT_BREAKS,
        "is_hk_school_short_break",
    )

    return result



def add_day_type(calendar):
    """Assign one primary day type to every date."""

    # Copy the calendar to protect the original data
    result = calendar.copy()

    # Use zero when typhoon data has not been added yet
    if "is_typhoon" not in result.columns:
        result["is_typhoon"] = 0

    # Set weekday as the default day type
    result["day_type"] = "weekday"

    # Assign weekend to Saturday and Sunday
    result.loc[
        result["is_weekend"] == 1,
        "day_type",
    ] = "weekend"

    # Give Hong Kong school long breaks higher priority
    result.loc[
        result["is_hk_school_long_break"] == 1,
        "day_type",
    ] = "school_long_break"

    # Give Hong Kong public holidays higher priority
    result.loc[
        result["is_hk_public_holiday"] == 1,
        "day_type",
    ] = "public_holiday"

    # Give typhoon days the highest priority
    result.loc[
        result["is_typhoon"] == 1,
        "day_type",
    ] = "typhoon"

    return result


# Run checks when this file is executed
if __name__ == "__main__":

    # Build the base daily calendar
    test_calendar = build_base_calendar()

    # Add Hong Kong public holiday features
    test_calendar = add_hk_public_holiday(
        test_calendar
    )
    test_calendar = add_hk_holiday_features(
        test_calendar
    )

    # Add mainland holiday features
    test_calendar = add_mainland_calendar(
        test_calendar
    )

    # Add policy and payday features
    test_calendar = add_policy_features(
        test_calendar
    )
    test_calendar = add_payday_period(
        test_calendar
    )

    # Add Shenzhen school-break features
    test_calendar = add_sz_school_break_features(
        test_calendar
    )

    # Add Hong Kong school-break features
    test_calendar = add_hk_school_break_features(
        test_calendar
    )

        # Assign the primary day type
    test_calendar = add_day_type(
        test_calendar
    )

    print("\nDay-type counts:")
    print(
        test_calendar[
            "day_type"
        ].value_counts()
    )

    # Display feature counts
    print("Number of rows:", len(test_calendar))
    print(
        "Shenzhen winter-break days:",
        test_calendar[
            "is_sz_winter_break"
        ].sum(),
    )
    print(
        "Shenzhen summer-break days:",
        test_calendar[
            "is_sz_summer_break"
        ].sum(),
    )
    print(
        "Shenzhen spring-break days:",
        test_calendar[
            "is_sz_spring_break"
        ].sum(),
    )
    print(
        "Shenzhen autumn-break days:",
        test_calendar[
            "is_sz_autumn_break"
        ].sum(),
    )

    # Select known dates for the Shenzhen-break check
    school_break_check_dates = pd.to_datetime([
        "2024-01-20",
        "2024-01-21",
        "2024-02-19",
        "2024-02-20",
        "2023-07-13",
        "2023-07-14",
    ])

    # Display Shenzhen school-break feature checks
    print("\nShenzhen school-break feature check:")
    print(
        test_calendar.loc[
            test_calendar["date"].isin(
                school_break_check_dates
            ),
            [
                "date",
                "is_sz_winter_break",
                "is_sz_summer_break",
                "is_sz_spring_break",
                "is_sz_autumn_break",
            ],
        ]
    )

    print(
        "Hong Kong school long-break days:",
        test_calendar[
            "is_hk_school_long_break"
        ].sum(),
    )

    print(
        "Hong Kong school short-break days:",
        test_calendar[
            "is_hk_school_short_break"
        ].sum(),
    )


    # Define binary feature columns for validation
    binary_columns = [
        "is_weekend",
        "is_hk_public_holiday",
        "is_holiday_eve",
        "is_long_weekend",
        "is_mainland_holiday",
        "is_mainland_makeup_workday",
        "post_hzmb_policy",
        "post_multi_entry_policy",
        "is_payday_period",
        "is_sz_winter_break",
        "is_sz_summer_break",
        "is_sz_spring_break",
        "is_sz_autumn_break",
        "is_hk_school_long_break",
        "is_hk_school_short_break",
    ]

    # Check that the calendar has one unique row per date
    assert len(test_calendar) == 1364
    assert test_calendar["date"].is_unique

    # Check that dates are continuous
    assert (
        test_calendar["date"]
        .diff()
        .dropna()
        .eq(pd.Timedelta(days=1))
        .all()
    )

    # Check that every binary feature contains only zero or one
    for column in binary_columns:
        assert set(test_calendar[column]) <= {0, 1}

    # Check that day_type only contains valid categories
    valid_day_types = {
        "weekday",
        "weekend",
        "school_long_break",
        "public_holiday",
        "typhoon",
    }

    assert set(test_calendar["day_type"]) <= valid_day_types

    print("\nCalendar validation passed.")

    # Define the draft output file path
    output_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "calendar_features_c_draft.csv"
    )

    # Save the completed C-role calendar features
    test_calendar.to_csv(
        output_path,
        index=False,
        date_format="%Y-%m-%d",
    )

    print("Saved draft file:", output_path)
    print("Saved rows:", len(test_calendar))