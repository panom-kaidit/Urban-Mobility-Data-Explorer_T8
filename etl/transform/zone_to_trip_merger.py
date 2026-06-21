from dataclasses import dataclass

import pandas as pd


@dataclass
class MergeReport:
    input_rows: int
    output_rows: int
    unmatched_pickup_locations: int = 0
    unmatched_dropoff_locations: int = 0


@dataclass
class MergeResult:
    data: pd.DataFrame
    report: MergeReport


class TripZoneMerger:
    """Add pickup and dropoff zone details to trip records."""

    def append_zone_info(
        self,
        trips: pd.DataFrame,
        lookup: pd.DataFrame,
    ) -> MergeResult:
        merged_trips = trips.copy()
        clean_lookup = self._prepare_lookup(lookup)

        pickup_lookup = clean_lookup.rename(
            columns={
                "LocationID": "PULocationID",
                "Borough": "pickup_borough",
                "Zone": "pickup_zone",
                "service_zone": "pickup_service_zone",
            }
        )
        merged_trips = merged_trips.merge(
            pickup_lookup,
            on="PULocationID",
            how="left",
        )

        dropoff_lookup = clean_lookup.rename(
            columns={
                "LocationID": "DOLocationID",
                "Borough": "dropoff_borough",
                "Zone": "dropoff_zone",
                "service_zone": "dropoff_service_zone",
            }
        )
        merged_trips = merged_trips.merge(
            dropoff_lookup,
            on="DOLocationID",
            how="left",
        )

        report = MergeReport(
            input_rows=len(trips),
            output_rows=len(merged_trips),
            unmatched_pickup_locations=int(merged_trips["pickup_zone"].isna().sum()),
            unmatched_dropoff_locations=int(merged_trips["dropoff_zone"].isna().sum()),
        )

        return MergeResult(merged_trips, report)

    def _prepare_lookup(self, lookup: pd.DataFrame) -> pd.DataFrame:
        needed_columns = ["LocationID", "Borough", "Zone", "service_zone"]
        clean_lookup = lookup[needed_columns].copy()
        clean_lookup = clean_lookup.drop_duplicates(subset=["LocationID"])
        return clean_lookup
