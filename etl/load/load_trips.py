import sys
from etl.extract import ParquetLoader
from etl.transform.validator import DataValidator
from etl.transform.cleaner import TripCleaner
from etl.transform.outlier_detector import TripOutlierDetector
from etl.transform.zone_to_trip_merger import TripZoneMerger
from etl.transform.feature_engineer import TripFeatureEngineer
from etl.extract import LookupLoader
from etl.utils.config import TRIP_DATA_FILE, LOOKUP_FILE, CHUNK_SIZE


def build_pipeline():
    """Load the lookup table and initialise all pipeline stages."""
    lookup_loader = LookupLoader(LOOKUP_FILE)
    lookup_data = lookup_loader.load()

    validator   = DataValidator()
    cleaner     = TripCleaner()
    detector    = TripOutlierDetector()
    merger      = TripZoneMerger()
    engineer    = TripFeatureEngineer()

    return lookup_data, validator, cleaner, detector, merger, engineer


def process_chunk(chunk, lookup_data, validator, cleaner, detector, merger, engineer):
    """
    Run one chunk of raw trip data through the full pipeline.

    Returns:
        cleaned_trips      — DataFrame ready to insert into trips table
        suspicious_records — DataFrame ready to insert into suspicious_records table
    """
    # 1. validate and coerce types
    validated = validator.validate_trip_data(chunk)
    trips = validated.data

    # 2. clean — remove invalid rows, capture removed records
    cleaned = cleaner.clean_trip_data(trips)
    suspicious = cleaned.removed_records

    # 3. flag outliers (rows are kept, just marked)
    outlier_result = detector.flag_trip_outliers(cleaned.data)

    # 4. merge pickup/dropoff zone names into trip rows
    merged = merger.append_zone_info(outlier_result.data, lookup_data)

    # 5. add derived features
    featured = engineer.add_trip_features(merged.data)

    return featured.data, suspicious
