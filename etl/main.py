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