from pathlib import Path

import pandas as pd


REQUIRED_LOOKUP_COLUMNS = {
    "LocationID",
    "Borough",
    "Zone",
    "service_zone",
}


class LookupLoader:
    """Load and validate the taxi zone lookup dimension table."""

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)
        self._validate_path()

    def load(self) -> pd.DataFrame:
        try:
            # Zone IDs 264/265 intentionally use the literal category "N/A".
            # Disabling pandas' default NA token conversion preserves those
            # labels through enrichment and analytics aggregation.
            lookup_data = pd.read_csv(self.file_path, keep_default_na=False)
        except Exception as exc:
            raise RuntimeError(f"Failed to load lookup file {self.file_path}: {exc}") from exc

        self.validate_schema(lookup_data)
        return lookup_data

    def validate_schema(self, lookup_data: pd.DataFrame) -> None:
        missing_columns = sorted(REQUIRED_LOOKUP_COLUMNS - set(lookup_data.columns))

        if missing_columns:
            missing = ", ".join(missing_columns)
            raise ValueError(f"Lookup file is missing required columns: {missing}")

        if lookup_data["LocationID"].isna().any():
            raise ValueError("Lookup file contains missing LocationID values.")

        duplicated_ids = lookup_data["LocationID"].duplicated()
        if duplicated_ids.any():
            duplicate_values = lookup_data.loc[duplicated_ids, "LocationID"].tolist()
            raise ValueError(f"Lookup file contains duplicate LocationID values: {duplicate_values}")

    def _validate_path(self) -> None:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Lookup file not found: {self.file_path}")

        if self.file_path.suffix.lower() != ".csv":
            raise ValueError(f"Expected a .csv lookup file, got: {self.file_path}")
