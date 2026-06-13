from pathlib import Path
from typing import Iterable

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


REQUIRED_TRIP_COLUMNS = {
    "VendorID",
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "RatecodeID",
    "store_and_fwd_flag",
    "PULocationID",
    "DOLocationID",
    "payment_type",
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "total_amount",
    "congestion_surcharge",
    "airport_fee",
}


class ParquetLoader:
    """Load NYC TLC trip parquet data in memory-safe batches."""

    def __init__(self, file_path: str | Path, chunk_size: int = 50_000) -> None:
        self.file_path = Path(file_path)
        self.chunk_size = chunk_size
        self._validate_inputs()

    def load_chunks(self, columns: list[str] | None = None) -> Iterable[pd.DataFrame]:
        parquet_file = pq.ParquetFile(self.file_path)
        self.validate_schema(parquet_file.schema_arrow.names)

        for batch in parquet_file.iter_batches(
            batch_size=self.chunk_size,
            columns=columns,
        ):
            yield batch.to_pandas()

    def load_sample(self, rows: int = 5) -> pd.DataFrame:
        if rows < 1:
            raise ValueError("rows must be greater than zero.")

        parquet_file = pq.ParquetFile(self.file_path)
        self.validate_schema(parquet_file.schema_arrow.names)
        batches = parquet_file.iter_batches(batch_size=rows)

        try:
            return next(batches).to_pandas().head(rows)
        except StopIteration:
            return pd.DataFrame()

    def get_schema(self) -> pa.Schema:
        return pq.ParquetFile(self.file_path).schema_arrow

    def get_row_count(self) -> int:
        return pq.ParquetFile(self.file_path).metadata.num_rows

    def validate_schema(self, columns: list[str] | None = None) -> None:
        actual_columns = set(columns or self.get_schema().names)
        missing_columns = sorted(REQUIRED_TRIP_COLUMNS - actual_columns)

        if missing_columns:
            missing = ", ".join(missing_columns)
            raise ValueError(f"Parquet file is missing required columns: {missing}")

    def _validate_inputs(self) -> None:
        if self.chunk_size < 1:
            raise ValueError("chunk_size must be greater than zero.")

        if not self.file_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {self.file_path}")

        if self.file_path.suffix.lower() != ".parquet":
            raise ValueError(f"Expected a .parquet file, got: {self.file_path}")
