import pandas as pd

class LookupLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> pd.DataFrame:

        try:
            lookupData = pd.read_csv(self.file_path)
            return lookupData
        except Exception as e:
            raise RuntimeError(f"Failed to load lookup file {self.file_path}: {e}")
