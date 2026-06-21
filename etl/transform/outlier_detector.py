from dataclasses import dataclass, field

import pandas as pd

# Startter flagging thresholds for suspicious trips.
MAX_DISTANCE_MILES = 100
MAX_TOTAL_AMOUNT = 500
MAX_FARE_AMOUNT = 500
MAX_SPEED_MPH = 120
MAX_DURATION_HOURS = 8


@dataclass
class OutlierReport:
    input_rows: int
    suspicious_rows: int = 0
    suspicious_by_reason: dict[str, int] = field(default_factory=dict)


@dataclass
class OutlierResult:
    data: pd.DataFrame
    suspicious_records: pd.DataFrame
    report: OutlierReport


class TripOutlierDetector:
    """Flag suspicious trip records without removing them."""

    def flag_trip_outliers(self, trips: pd.DataFrame) -> OutlierResult:
        checked_trips = trips.copy()
        report = OutlierReport(input_rows=len(checked_trips))

        checked_trips["is_outlier"] = False
        checked_trips["outlier_reasons"] = ""

        duration_minutes = self._trip_duration_minutes(checked_trips)
        average_speed = self._average_speed_mph(checked_trips, duration_minutes)

        self._flag_rows(
            checked_trips,
            (checked_trips["trip_distance"] > MAX_DISTANCE_MILES).fillna(False),
            "extreme_distance",
            report,
        )
        self._flag_rows(
            checked_trips,
            (checked_trips["total_amount"] > MAX_TOTAL_AMOUNT).fillna(False),
            "extreme_total_amount",
            report,
        )
        self._flag_rows(
            checked_trips,
            (checked_trips["fare_amount"] > MAX_FARE_AMOUNT).fillna(False),
            "extreme_fare_amount",
            report,
        )
        self._flag_rows(
            checked_trips,
            (average_speed > MAX_SPEED_MPH).fillna(False),
            "unrealistic_speed",
            report,
        )
        self._flag_rows(
            checked_trips,
            (duration_minutes > MAX_DURATION_HOURS * 60).fillna(False),
            "very_long_duration",
            report,
        )

        checked_trips["outlier_reasons"] = checked_trips["outlier_reasons"].str.strip(";")
        suspicious_records = checked_trips[checked_trips["is_outlier"]].copy()
        report.suspicious_rows = len(suspicious_records)

        return OutlierResult(
            data=checked_trips,
            suspicious_records=suspicious_records.reset_index(drop=True),
            report=report,
        )

    def _trip_duration_minutes(self, trips: pd.DataFrame) -> pd.Series:
        duration = trips["tpep_dropoff_datetime"] - trips["tpep_pickup_datetime"]
        return duration.dt.total_seconds() / 60

    def _average_speed_mph(
        self,
        trips: pd.DataFrame,
        duration_minutes: pd.Series,
    ) -> pd.Series:
        duration_hours = duration_minutes / 60
        return trips["trip_distance"] / duration_hours

    def _flag_rows(
        self,
        trips: pd.DataFrame,
        outlier_mask: pd.Series,
        reason: str,
        report: OutlierReport,
    ) -> None:
        count = int(outlier_mask.sum())
        report.suspicious_by_reason[reason] = count

        if count == 0:
            return

        trips.loc[outlier_mask, "is_outlier"] = True
        trips.loc[outlier_mask, "outlier_reasons"] += reason + ";"
