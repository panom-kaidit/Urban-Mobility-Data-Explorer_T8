import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config.database import init_db
from etl.load.load_locations import load_locations
from etl.load.load_analytics import refresh_analytics
from etl.load.load_trips import load_trips
from etl.load.load_zone_boundaries import load_zone_boundaries


def load_all() -> None:
    """Initialize the database and execute every loader in dependency order."""
    steps = (
        ("Initializing database schema", lambda: init_db(create_indexes=False)),
        ("Loading taxi zone locations", load_locations),
        ("Loading zone boundaries", load_zone_boundaries),
        ("Loading and transforming trips", load_trips),
    )

    print("=== Urban Mobility ETL: Full Load ===")

    for number, (description, loader) in enumerate(steps, start=1):
        print(f"\nStep {number}/{len(steps)}: {description}...")
        loader()

    print("\n=== Urban Mobility ETL Complete ===")


def load_analytics_only() -> None:
    """Recover aggregate tables and deferred indexes from loaded trips."""
    print("=== Urban Mobility ETL: Analytics Recovery ===")
    refresh_analytics()
    print("=== Analytics Recovery Complete ===")


def parse_args():
    parser = argparse.ArgumentParser(description="Load Urban Mobility data.")
    parser.add_argument(
        "--analytics-only",
        action="store_true",
        help="Rebuild analytics and query indexes without reloading trip data.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    if arguments.analytics_only:
        load_analytics_only()
    else:
        load_all()
