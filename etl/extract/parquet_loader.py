import pandas as pd
import pyarrow.parquet as pq
from typing import Iterator

class ParquetLoader:
    def __init__(self, file_path: str, chunk_size: int = 50_000):
        self.file_path = file_path
        self.chunk_size = chunk_size

    def load_chunks(self) -> Iterator[pd.DataFrame]:

        parquet_file = pq.ParquetFile(self.file_path)
        
        for batch in parquet_file.iter_batches(batch_size=self.chunk_size):
            yield batch.to_pandas()

    def get_schema(self):
        parquet_file = pq.ParquetFile(self.file_path)
        return parquet_file.schema
