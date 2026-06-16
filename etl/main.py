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