from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.models.location import Base


class ZoneBoundary(Base):
    """Represents a taxi zone boundary in the zone_boundaries table. Each boundary is associated with one location in the locations table."""

    __tablename__ = "zone_boundaries"

    location_id = Column(
        Integer,
        ForeignKey("locations.location_id"),
        primary_key=True,
    )

    # The following fields are nullable because the ETL may not have been able to extract them from the shapefile for some boundaries.
    zone = Column(String, nullable=True)
    borough = Column(String, nullable=True)

    # Shape measurements from the shapefile.
    shape_area = Column(Float, nullable=True)
    shape_length = Column(Float, nullable=True)

    # GeoJSON text created by the ETL after reprojecting to WGS84 latitude and longitude coordinates.
    geometry = Column(Text, nullable=True)

    # Relationship to the location row in locations.
    location = relationship(
        "Location",
        back_populates="zone_boundary",
    )
