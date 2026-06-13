import geopandas as gpd

class GeoJSONLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> gpd.GeoDataFrame:

        try:
            geoData = gpd.read_file(self.file_path)
            return geoData
        except Exception as e:
            raise RuntimeError(f"Failed to load spatial file {self.file_path}: {e}")
