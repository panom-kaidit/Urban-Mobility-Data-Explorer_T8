from dataclasses import dataclass

import pandas as pd


NEW_FEATURES = [
    "trip_duration_minutes",
    "average_speed_mph",
    "fare_per_mile",
    "pickup_hour",
    "pickup_day_of_week",
    "tip_percentage",
]


@dataclass
class FeatureReport:
    input_rows: int
    output_rows: int
    added_columns: list[str]


@dataclass
class FeatureResult:
    data: pd.DataFrame
    report: FeatureReport


class TripFeatureEngineer:
    """Create useful analysis columns from cleaned and enriched trip records."""

    def add_trip_features(self, trips: pd.DataFrame) -> FeatureResult:
        featured_trips = trips.copy()

        duration = (
            featured_trips["tpep_dropoff_datetime"]
            - featured_trips["tpep_pickup_datetime"]
        )
        featured_trips["trip_duration_minutes"] = duration.dt.total_seconds() / 60

        duration_hours = featured_trips["trip_duration_minutes"] / 60
        featured_trips["average_speed_mph"] = (
            featured_trips["trip_distance"] / duration_hours
        )

        featured_trips["fare_per_mile"] = (
            featured_trips["total_amount"] / featured_trips["trip_distance"]
        )

        featured_trips["pickup_hour"] = featured_trips["tpep_pickup_datetime"].dt.hour
        featured_trips["pickup_day_of_week"] = (
            featured_trips["tpep_pickup_datetime"].dt.day_name()
        )

        featured_trips["tip_percentage"] = (
            featured_trips["tip_amount"] / featured_trips["fare_amount"]
        ) * 100

        self._replace_bad_numbers(featured_trips)

        report = FeatureReport(
            input_rows=len(trips),
            output_rows=len(featured_trips),
            added_columns=NEW_FEATURES,
        )

        return FeatureResult(featured_trips, report)

    def _replace_bad_numbers(self, trips: pd.DataFrame) -> None:
        trips.loc[trips["trip_distance"] <= 0, "fare_per_mile"] = pd.NA
        trips.loc[trips["trip_duration_minutes"] <= 0, "average_speed_mph"] = pd.NA
        trips.loc[trips["fare_amount"] <= 0, "tip_percentage"] = pd.NA
