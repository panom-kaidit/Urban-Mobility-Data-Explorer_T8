from pathlib import Path

import geopandas as gpd


REQUIRED_SPATIAL_COLUMNS = {
    "LocationID",
    "zone",
    "borough",
    "geometry",
}

SUPPORTED_SPATIAL_SUFFIXES = {
    ".geojson",
    ".json",
    ".shp",
}


class SpatialLoader:
    """Load taxi zone spatial metadata from shapefile sources."""

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)
        self._validate_path()

    def load(self) -> gpd.GeoDataFrame:
        try:
            spatial_data = gpd.read_file(self.file_path)
        except Exception as exc:
            raise RuntimeError(f"Failed to load spatial file {self.file_path}: {exc}") from exc

        self.validate_schema(spatial_data)
        return spatial_data

    def validate_schema(self, spatial_data: gpd.GeoDataFrame) -> None:
        missing_columns = sorted(REQUIRED_SPATIAL_COLUMNS - set(spatial_data.columns))

        if missing_columns:
            missing = ", ".join(missing_columns)
            raise ValueError(f"Spatial file is missing required columns: {missing}")

        if spatial_data.crs is None:
            raise ValueError("Spatial file does not define a coordinate reference system.")

        if spatial_data.geometry.isna().any():
            raise ValueError("Spatial file contains missing geometry values.")

        if not spatial_data.geometry.is_valid.all():
            raise ValueError("Spatial file contains invalid geometries.")

    def _validate_path(self) -> None:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Spatial file not found: {self.file_path}")

        if self.file_path.suffix.lower() not in SUPPORTED_SPATIAL_SUFFIXES:
            supported = ", ".join(sorted(SUPPORTED_SPATIAL_SUFFIXES))
            raise ValueError(f"Expected one of {supported}, got: {self.file_path}")



