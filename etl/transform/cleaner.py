from dataclasses import dataclass, field

import pandas as pd


TIME_COLUMNS = ["tpep_pickup_datetime", "tpep_dropoff_datetime"]
LOCATION_COLUMNS = ["PULocationID", "DOLocationID"]
DISTANCE_COLUMN = "trip_distance"
MONEY_COLUMNS = ["fare_amount", "total_amount"]
EXPECTED_START_DATE = pd.Timestamp("2019-01-01")
EXPECTED_END_DATE = pd.Timestamp("2019-02-01")


@dataclass
class CleaningReport:
    input_rows: int
    output_rows: int
    removed_rows: int = 0
    removed_by_reason: dict[str, int] = field(default_factory=dict)


@dataclass
class CleaningResult:
    data: pd.DataFrame
    removed_records: pd.DataFrame
    report: CleaningReport


class TripCleaner:
    """Remove clearly invalid trip records after validation."""

    def clean_trip_data(self, trips: pd.DataFrame) -> CleaningResult:
        clean_trips = trips.copy()
        removed_parts = []
        report = CleaningReport(input_rows=len(clean_trips), output_rows=len(clean_trips))

        missing_mask = self._missing_required_values(clean_trips)
        clean_trips = self._remove_rows(
            clean_trips,
            missing_mask,
            "missing_required_value",
            removed_parts,
            report,
        )

        bad_time_mask = self._invalid_timestamps(clean_trips)
        clean_trips = self._remove_rows(
            clean_trips,
            bad_time_mask,
            "invalid_timestamp",
            removed_parts,
            report,
        )

        out_of_period_mask = self._outside_expected_period(clean_trips)
        clean_trips = self._remove_rows(
            clean_trips,
            out_of_period_mask,
            "outside_expected_period",
            removed_parts,
            report,
        )

        bad_distance_mask = (clean_trips[DISTANCE_COLUMN] < 0).fillna(False)
        clean_trips = self._remove_rows(
            clean_trips,
            bad_distance_mask,
            "negative_distance",
            removed_parts,
            report,
        )

        bad_money_mask = clean_trips[MONEY_COLUMNS].lt(0).any(axis=1).fillna(False)
        clean_trips = self._remove_rows(
            clean_trips,
            bad_money_mask,
            "negative_money_value",
            removed_parts,
            report,
        )

        duplicate_mask = clean_trips.duplicated().fillna(False)
        clean_trips = self._remove_rows(
            clean_trips,
            duplicate_mask,
            "duplicate_trip",
            removed_parts,
            report,
        )

        removed_records = self._combine_removed_records(removed_parts)
        report.output_rows = len(clean_trips)
        report.removed_rows = len(removed_records)

        return CleaningResult(
            data=clean_trips.reset_index(drop=True),
            removed_records=removed_records,
            report=report,
        )

    def _missing_required_values(self, trips: pd.DataFrame) -> pd.Series:
        required_columns = TIME_COLUMNS + LOCATION_COLUMNS + [DISTANCE_COLUMN] + MONEY_COLUMNS
        return trips[required_columns].isna().any(axis=1).fillna(False)

    def _invalid_timestamps(self, trips: pd.DataFrame) -> pd.Series:
        pickup_time = trips["tpep_pickup_datetime"]
        dropoff_time = trips["tpep_dropoff_datetime"]
        return (dropoff_time <= pickup_time).fillna(False)

    def _outside_expected_period(self, trips: pd.DataFrame) -> pd.Series:
        pickup_time = trips["tpep_pickup_datetime"]
        dropoff_time = trips["tpep_dropoff_datetime"]
        return (
            (pickup_time < EXPECTED_START_DATE)
            | (pickup_time >= EXPECTED_END_DATE)
            | (dropoff_time < EXPECTED_START_DATE)
            | (dropoff_time >= EXPECTED_END_DATE)
        ).fillna(False)

    def _remove_rows(
        self,
        trips: pd.DataFrame,
        bad_rows: pd.Series,
        reason: str,
        removed_parts: list[pd.DataFrame],
        report: CleaningReport,
    ) -> pd.DataFrame:
        count = int(bad_rows.sum())
        report.removed_by_reason[reason] = count

        if count == 0:
            return trips

        removed = trips.loc[bad_rows].copy()
        removed["removal_reason"] = reason
        removed_parts.append(removed)

        return trips.loc[~bad_rows].copy()

    def _combine_removed_records(self, removed_parts: list[pd.DataFrame]) -> pd.DataFrame:
        if not removed_parts:
            return pd.DataFrame()

        return pd.concat(removed_parts, ignore_index=True)
