from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Station:
    name: str = "SJC (provisória)"
    latitude_deg: float = -23.2089
    longitude_deg: float = -45.8609
    altitude_m: float = 600.0
    min_elevation_deg: float = 10.0

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("Informe um nome para a estação.")
        if not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("A latitude deve estar entre -90° e +90°.")
        if not -180.0 <= self.longitude_deg <= 180.0:
            raise ValueError("A longitude deve estar entre -180° e +180°.")
        if not -500.0 <= self.altitude_m <= 10_000.0:
            raise ValueError("A altitude deve estar entre -500 m e 10.000 m.")
        if not 0.0 <= self.min_elevation_deg < 90.0:
            raise ValueError("A elevação mínima deve estar entre 0° e 89,9°.")

    def to_dict(self) -> dict[str, str | float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, values: dict[str, object]) -> "Station":
        defaults = cls()
        station = cls(
            name=str(values.get("name", defaults.name)),
            latitude_deg=float(values.get("latitude_deg", defaults.latitude_deg)),
            longitude_deg=float(values.get("longitude_deg", defaults.longitude_deg)),
            altitude_m=float(values.get("altitude_m", defaults.altitude_m)),
            min_elevation_deg=float(
                values.get("min_elevation_deg", defaults.min_elevation_deg)
            ),
        )
        station.validate()
        return station


@dataclass(frozen=True, slots=True)
class Satellite:
    name: str
    line1: str
    line2: str
    catalog_number: int
    epoch_utc: datetime
    omm_fields: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class Observation:
    elevation_deg: float
    azimuth_deg: float
    range_km: float


@dataclass(frozen=True, slots=True)
class PassWindow:
    satellite: Satellite
    aos_utc: datetime
    los_utc: datetime
    max_utc: datetime
    aos_azimuth_deg: float
    los_azimuth_deg: float
    max_elevation_deg: float
    max_azimuth_deg: float
    min_range_km: float
    starts_before_window: bool = False
    ends_after_window: bool = False

    @property
    def duration_seconds(self) -> float:
        return (self.los_utc - self.aos_utc).total_seconds()
