from dataclasses import dataclass, field

import geopandas as gpd
import pandas as pd


TRIP_DATE_COLUMNS = ["tpep_pickup_datetime", "tpep_dropoff_datetime"]

TRIP_ID_COLUMNS = [
    "VendorID",
    "passenger_count",
    "RatecodeID",
    "PULocationID",
    "DOLocationID",
    "payment_type",
]

TRIP_AMOUNT_COLUMNS = [
    "trip_distance",
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "total_amount",
    "congestion_surcharge",
    "airport_fee",
]

TRIP_TEXT_COLUMNS = ["store_and_fwd_flag"]

EXPECTED_TRIP_COLUMNS = (
    TRIP_DATE_COLUMNS
    + TRIP_ID_COLUMNS
    + TRIP_AMOUNT_COLUMNS
    + TRIP_TEXT_COLUMNS
)

EXPECTED_LOOKUP_COLUMNS = ["LocationID", "Borough", "Zone", "service_zone"]
EXPECTED_SPATIAL_COLUMNS = ["LocationID", "zone", "borough", "geometry"]


@dataclass
class ValidationReport:
    dataset_name: str
    input_rows: int
    output_rows: int
    missing_columns: list[str] = field(default_factory=list)
    missing_values: dict[str, int] = field(default_factory=dict)
    coerced_values: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.missing_columns) == 0


@dataclass
class ValidationResult:
    data: pd.DataFrame | gpd.GeoDataFrame
    report: ValidationReport


class DataValidator:
    """Validate raw data before cleaning starts."""

    def validate_trip_data(self, trips: pd.DataFrame) -> ValidationResult:
        report = self._make_report("yellow_tripdata", trips)
        report.missing_columns = self._find_missing_columns(trips, EXPECTED_TRIP_COLUMNS)

        if report.missing_columns:
            return ValidationResult(trips.copy(), report)

        clean_trips = trips.copy()

        for col in TRIP_DATE_COLUMNS:
            old_missing = clean_trips[col].isna()
            clean_trips[col] = pd.to_datetime(clean_trips[col], errors="coerce")
            report.coerced_values[col] = int((clean_trips[col].isna() & ~old_missing).sum())

        for col in TRIP_ID_COLUMNS:
            old_missing = clean_trips[col].isna()
            clean_trips[col] = self._to_nullable_int(clean_trips[col])
            report.coerced_values[col] = int((clean_trips[col].isna() & ~old_missing).sum())

        for col in TRIP_AMOUNT_COLUMNS:
            old_missing = clean_trips[col].isna()
            clean_trips[col] = pd.to_numeric(clean_trips[col], errors="coerce").astype("Float64")
            report.coerced_values[col] = int((clean_trips[col].isna() & ~old_missing).sum())

        for col in TRIP_TEXT_COLUMNS:
            clean_trips[col] = clean_trips[col].astype("string")

        report.missing_values = self._count_missing_values(clean_trips)
        self._add_basic_trip_warnings(clean_trips, report)
        report.output_rows = len(clean_trips)

        return ValidationResult(clean_trips, report)

    def validate_lookup_data(self, lookup: pd.DataFrame) -> ValidationResult:
        report = self._make_report("taxi_zone_lookup", lookup)
        report.missing_columns = self._find_missing_columns(lookup, EXPECTED_LOOKUP_COLUMNS)

        if report.missing_columns:
            return ValidationResult(lookup.copy(), report)

        clean_lookup = lookup.copy()

        old_missing = clean_lookup["LocationID"].isna()
        clean_lookup["LocationID"] = self._to_nullable_int(clean_lookup["LocationID"])
        report.coerced_values["LocationID"] = int(
            (clean_lookup["LocationID"].isna() & ~old_missing).sum()
        )

        for col in ["Borough", "Zone", "service_zone"]:
            clean_lookup[col] = clean_lookup[col].astype("string").str.strip()

        duplicates = int(clean_lookup["LocationID"].duplicated().sum())
        if duplicates > 0:
            report.warnings.append(f"Found {duplicates} duplicate LocationID values.")

        report.missing_values = self._count_missing_values(clean_lookup)
        report.output_rows = len(clean_lookup)

        return ValidationResult(clean_lookup, report)

    def validate_spatial_data(self, zones: gpd.GeoDataFrame) -> ValidationResult:
        report = self._make_report("taxi_zones_spatial", zones)
        report.missing_columns = self._find_missing_columns(zones, EXPECTED_SPATIAL_COLUMNS)

        if report.missing_columns:
            return ValidationResult(zones.copy(), report)

        clean_zones = zones.copy()

        old_missing = clean_zones["LocationID"].isna()
        clean_zones["LocationID"] = self._to_nullable_int(clean_zones["LocationID"])
        report.coerced_values["LocationID"] = int(
            (clean_zones["LocationID"].isna() & ~old_missing).sum()
        )

        for col in ["zone", "borough"]:
            clean_zones[col] = clean_zones[col].astype("string").str.strip()

        if clean_zones.crs is None:
            report.warnings.append("Spatial data has no CRS.")

        invalid_shapes = int((~clean_zones.geometry.is_valid).sum())
        if invalid_shapes > 0:
            report.warnings.append(f"Found {invalid_shapes} invalid geometries.")

        report.missing_values = self._count_missing_values(
            clean_zones.drop(columns=["geometry"])
        )
        report.output_rows = len(clean_zones)

        return ValidationResult(clean_zones, report)

    def _make_report(
        self,
        name: str,
        data: pd.DataFrame | gpd.GeoDataFrame,
    ) -> ValidationReport:
        return ValidationReport(
            dataset_name=name,
            input_rows=len(data),
            output_rows=len(data),
        )

    def _find_missing_columns(
        self,
        data: pd.DataFrame | gpd.GeoDataFrame,
        expected_columns: list[str],
    ) -> list[str]:
        return [col for col in expected_columns if col not in data.columns]

    def _count_missing_values(
        self,
        data: pd.DataFrame | gpd.GeoDataFrame,
    ) -> dict[str, int]:
        missing_counts = data.isna().sum()
        return {
            col: int(count)
            for col, count in missing_counts.items()
            if int(count) > 0
        }

    def _to_nullable_int(self, values: pd.Series) -> pd.Series:
        numbers = pd.to_numeric(values, errors="coerce")
        whole_numbers = numbers.isna() | (numbers % 1 == 0)
        return numbers.where(whole_numbers).astype("Int64")

    def _add_basic_trip_warnings(
        self,
        trips: pd.DataFrame,
        report: ValidationReport,
    ) -> None:
        missing_locations = int(
            trips[["PULocationID", "DOLocationID"]].isna().any(axis=1).sum()
        )
        if missing_locations > 0:
            report.warnings.append(
                f"Found {missing_locations} rows with missing pickup/dropoff locations."
            )

        missing_times = int(trips[TRIP_DATE_COLUMNS].isna().any(axis=1).sum())
        if missing_times > 0:
            report.warnings.append(
                f"Found {missing_times} rows with missing or invalid timestamps."
            )
