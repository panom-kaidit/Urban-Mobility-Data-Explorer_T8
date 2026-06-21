import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from etl.extract.spatial_data_loader import SpatialLoader
from etl.extract.lookup_loader import LookupLoader
from etl.extract.parquet_loader import ParquetLoader
from etl.transform import (
    CleaningReport,
    DataValidator,
    FeatureReport,
    MergeReport,
    OutlierReport,
    TripCleaner,
    TripFeatureEngineer,
    TripOutlierDetector,
    TripZoneMerger,
    ValidationReport,
)
from etl.utils.audit_logger import AuditLogger
from etl.utils.config import CHUNK_SIZE, LOG_DIR, LOOKUP_FILE, SPATIAL_FILE, TRIP_DATA_FILE


def print_validation_report(report: ValidationReport) -> None:
    print(f" -> Validation passed: {report.passed}")
    if report.missing_columns:
        print(f" -> Missing columns: {', '.join(report.missing_columns)}")
    if report.missing_values:
        print(f" -> Missing values: {report.missing_values}")
    if report.coerced_values:
        coerced = {key: value for key, value in report.coerced_values.items() if value}
        print(f" -> Coerced invalid values: {coerced or {}}")
    if report.warnings:
        print(f" -> Warnings: {report.warnings}")


def print_cleaning_report(report: CleaningReport) -> None:
    print(f" -> Rows before cleaning: {report.input_rows}")
    print(f" -> Rows after cleaning: {report.output_rows}")
    print(f" -> Removed rows: {report.removed_rows}")
    print(f" -> Removed by reason: {report.removed_by_reason}")


def print_outlier_report(report: OutlierReport) -> None:
    print(f" -> Rows checked for outliers: {report.input_rows}")
    print(f" -> Suspicious rows: {report.suspicious_rows}")
    print(f" -> Suspicious by reason: {report.suspicious_by_reason}")


def print_merge_report(report: MergeReport) -> None:
    print(f" -> Rows before enrichment: {report.input_rows}")
    print(f" -> Rows after enrichment: {report.output_rows}")
    print(f" -> Unmatched pickup locations: {report.unmatched_pickup_locations}")
    print(f" -> Unmatched dropoff locations: {report.unmatched_dropoff_locations}")


def print_feature_report(report: FeatureReport) -> None:
    print(f" -> Rows before feature engineering: {report.input_rows}")
    print(f" -> Rows after feature engineering: {report.output_rows}")
    print(f" -> Added features: {', '.join(report.added_columns)}")


def print_audit_outputs(paths: dict[str, Path]) -> None:
    print(f" -> Summary log: {paths['summary']}")
    print(f" -> Removed records log: {paths['removed_records']}")
    print(f" -> Suspicious records log: {paths['suspicious_records']}")

def test_etl_layers() -> None:
    print("=== Testing ETL Extraction + Validation + Cleaning + Outlier + Enrichment + Feature + Audit Layers ===\n")
    validator = DataValidator()
    cleaner = TripCleaner()
    outlier_detector = TripOutlierDetector()
    zone_merger = TripZoneMerger()
    feature_engineer = TripFeatureEngineer()
    audit_logger = AuditLogger(LOG_DIR)
    lookup_result = None

    print(f"1. Loading and validating lookup data from {LOOKUP_FILE.name}...")
    lookup_loader = LookupLoader(LOOKUP_FILE)
    try:
        lookup_df = lookup_loader.load()
        lookup_result = validator.validate_lookup_data(lookup_df)
        print(f" -> Success! Loaded {len(lookup_df)} lookup records.")
        print_validation_report(lookup_result.report)
        print(" -> Sample:")
        print(lookup_result.data.head(2).to_string(), "\n")
    except Exception as exc:
        print(f" -> Error loading lookup: {exc}\n")

    print(f"2. Loading and validating spatial data from {SPATIAL_FILE.name}...")
    spatial_loader = SpatialLoader(SPATIAL_FILE)
    try:
        spatial_gdf = spatial_loader.load()
        spatial_result = validator.validate_spatial_data(spatial_gdf)
        print(f" -> Success! Loaded {len(spatial_gdf)} spatial records.")
        print(f" -> CRS: {spatial_gdf.crs}")
        print_validation_report(spatial_result.report)
        print(" -> Sample:")
        spatial_sample = spatial_result.data[['LocationID', 'borough', 'zone']].copy()
        spatial_sample["geometry_type"] = spatial_result.data.geometry.geom_type
        print(spatial_sample.head(2).to_string(), "\n")
    except Exception as exc:
        print(f" -> Error loading spatial data: {exc}\n")

    print(f"3. Loading and validating parquet data from {TRIP_DATA_FILE.name} in chunks...")
    parquet_loader = ParquetLoader(TRIP_DATA_FILE, chunk_size=CHUNK_SIZE)
    try:
        schema = parquet_loader.get_schema()
        parquet_loader.validate_schema()
        print(f" -> Row count: {parquet_loader.get_row_count():,}")
        print(f" -> Schema has {len(schema.names)} columns.")

        # Load only the first chunk to test
        first_chunk = next(iter(parquet_loader.load_chunks()))
        print(f" -> Success! Loaded first chunk with {len(first_chunk)} records.")
        trip_result = validator.validate_trip_data(first_chunk)
        print_validation_report(trip_result.report)
        cleaning_result = cleaner.clean_trip_data(trip_result.data)
        print_cleaning_report(cleaning_result.report)
        outlier_result = outlier_detector.flag_trip_outliers(cleaning_result.data)
        print_outlier_report(outlier_result.report)

        if lookup_result is None:
            raise RuntimeError("Lookup data must load before trip enrichment.")

        merge_result = zone_merger.append_zone_info(
            outlier_result.data,
            lookup_result.data,
        )
        print_merge_report(merge_result.report)
        feature_result = feature_engineer.add_trip_features(merge_result.data)
        print_feature_report(feature_result.report)
        audit_summary = {
            "lookup_validation": lookup_result.report,
            "trip_validation": trip_result.report,
            "cleaning": cleaning_result.report,
            "outliers": outlier_result.report,
            "zone_merge": merge_result.report,
            "feature_engineering": feature_result.report,
        }
        audit_paths = {
            "summary": audit_logger.write_summary(audit_summary),
            "removed_records": audit_logger.write_removed_records(
                cleaning_result.removed_records
            ),
            "suspicious_records": audit_logger.write_suspicious_records(
                outlier_result.suspicious_records
            ),
        }
        print_audit_outputs(audit_paths)
        print(" -> Types:\n", trip_result.data[['VendorID', 'tpep_pickup_datetime', 'trip_distance']].dtypes)
        print(" -> Sample:")
        trip_columns = ['VendorID', 'tpep_pickup_datetime', 'trip_distance', 'total_amount']
        enriched_columns = [
            'VendorID',
            'tpep_pickup_datetime',
            'trip_distance',
            'total_amount',
            'pickup_zone',
            'dropoff_zone',
            'trip_duration_minutes',
            'average_speed_mph',
            'fare_per_mile',
            'pickup_hour',
            'pickup_day_of_week',
            'tip_percentage',
        ]
        print(feature_result.data[enriched_columns + ["is_outlier"]].head(2).to_string(), "\n")

        if not cleaning_result.removed_records.empty:
            removed_columns = trip_columns + ["removal_reason"]
            print(" -> Removed sample:")
            print(cleaning_result.removed_records[removed_columns].head(3).to_string(), "\n")

        if not outlier_result.suspicious_records.empty:
            suspicious_columns = trip_columns + ["outlier_reasons"]
            print(" -> Suspicious sample:")
            print(outlier_result.suspicious_records[suspicious_columns].head(3).to_string(), "\n")
    except StopIteration:
        print(" -> Parquet file is empty.")
    except Exception as exc:
        print(f" -> Error loading parquet data: {exc}\n")

def run_full_etl() -> None:
    """
    Full ETL pipeline: schema init : locations :zone boundaries : trips.

    Load order is required by FK constraints:
      locations must exist before zone_boundaries (FK: location_id)
      locations must exist before trips           (FK: pu/do_location_id)
    """
    from backend.config.database import init_db
    from etl.load import load_locations, load_zone_boundaries, load_trips

    print("=== Urban Mobility ETL — Full Run ===\n")

    print("Step 1: Initialising database schema...")
    init_db()
    print(" -> Schema ready.\n")

    print("Step 2: Loading taxi zone lookup data (265 locations)...")
    load_locations()
    print()

    print("Step 3: Loading zone boundary polygons...")
    load_zone_boundaries()
    print()

    print("Step 4: Running full trip ETL pipeline (7.7M rows)...")
    load_trips()
    print()

    print("=== ETL Complete ===")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_etl_layers()
    else:
        run_full_etl()