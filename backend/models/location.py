from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class Location(Base):
    """ Represents a taxi zone in the locations table."""
    __tablename__ = "locations"

    location_id = Column(Integer, primary_key=True)

    borough = Column(String, nullable=False)
    zone = Column(String, nullable=False)
    service_zone = Column(String, nullable=True)
    pickup_trips = relationship(
        "Trip",
        back_populates="pickup_location",
        foreign_keys="Trip.pu_location_id",
    )

    dropoff_trips = relationship(
        "Trip",
        back_populates="dropoff_location",
        foreign_keys="Trip.do_location_id",
    )

    # One-to-one relationship with the zone boundary.
    zone_boundary = relationship(
        "ZoneBoundary",
        back_populates="location",
        uselist=False,
    )
