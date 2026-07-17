from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from sgp4.api import Satrec, jday

from .models import Observation, PassWindow, Satellite, Station

WGS84_A_KM = 6378.137
WGS84_F = 1.0 / 298.257223563
WGS84_E2 = WGS84_F * (2.0 - WGS84_F)
UTC = timezone.utc


class PropagationError(RuntimeError):
    """Raised when SGP4 cannot propagate a TLE at a requested instant."""


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        raise ValueError("O instante deve possuir informação de fuso horário.")
    return moment.astimezone(UTC)


def _julian(moment: datetime) -> tuple[float, float]:
    moment = _as_utc(moment)
    return jday(
        moment.year,
        moment.month,
        moment.day,
        moment.hour,
        moment.minute,
        moment.second + moment.microsecond / 1_000_000.0,
    )


def _gmst_rad(julian_date: float) -> float:
    centuries = (julian_date - 2451545.0) / 36525.0
    degrees = (
        280.46061837
        + 360.98564736629 * (julian_date - 2451545.0)
        + 0.000387933 * centuries * centuries
        - centuries * centuries * centuries / 38710000.0
    )
    return math.radians(degrees % 360.0)


def _observer_ecef(station: Station) -> tuple[float, float, float]:
    lat = math.radians(station.latitude_deg)
    lon = math.radians(station.longitude_deg)
    height_km = station.altitude_m / 1000.0
    sin_lat = math.sin(lat)
    prime_vertical = WGS84_A_KM / math.sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat)
    x = (prime_vertical + height_km) * math.cos(lat) * math.cos(lon)
    y = (prime_vertical + height_km) * math.cos(lat) * math.sin(lon)
    z = (prime_vertical * (1.0 - WGS84_E2) + height_km) * sin_lat
    return x, y, z


class Propagator:
    def __init__(self, satellite: Satellite, station: Station):
        self.satellite = satellite
        self.station = station
        self._satrec = Satrec.twoline2rv(satellite.line1, satellite.line2)
        self._observer = _observer_ecef(station)
        self._lat = math.radians(station.latitude_deg)
        self._lon = math.radians(station.longitude_deg)

    def observe(self, moment: datetime) -> Observation:
        jd, fraction = _julian(moment)
        error, position_teme, _velocity = self._satrec.sgp4(jd, fraction)
        if error:
            raise PropagationError(
                f"SGP4 retornou o código {error} para {self.satellite.name}."
            )

        theta = _gmst_rad(jd + fraction)
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        x_teme, y_teme, z_teme = position_teme

        # TEME/ECI to Earth-fixed rotation. Polar motion is intentionally not
        # applied in this planning-grade first version.
        x_ecef = cos_theta * x_teme + sin_theta * y_teme
        y_ecef = -sin_theta * x_teme + cos_theta * y_teme
        z_ecef = z_teme

        dx = x_ecef - self._observer[0]
        dy = y_ecef - self._observer[1]
        dz = z_ecef - self._observer[2]

        sin_lat, cos_lat = math.sin(self._lat), math.cos(self._lat)
        sin_lon, cos_lon = math.sin(self._lon), math.cos(self._lon)
        east = -sin_lon * dx + cos_lon * dy
        north = -sin_lat * cos_lon * dx - sin_lat * sin_lon * dy + cos_lat * dz
        up = cos_lat * cos_lon * dx + cos_lat * sin_lon * dy + sin_lat * dz
        horizontal = math.hypot(east, north)
        distance = math.sqrt(east * east + north * north + up * up)

        return Observation(
            elevation_deg=math.degrees(math.atan2(up, horizontal)),
            azimuth_deg=math.degrees(math.atan2(east, north)) % 360.0,
            range_km=distance,
        )


def _refine_crossing(
    propagator: Propagator,
    first: datetime,
    second: datetime,
    threshold_deg: float,
    rising: bool,
) -> datetime:
    low, high = first, second
    for _ in range(24):
        middle = low + (high - low) / 2
        above = propagator.observe(middle).elevation_deg >= threshold_deg
        if rising:
            if above:
                high = middle
            else:
                low = middle
        else:
            if above:
                low = middle
            else:
                high = middle
    return high if rising else low


def _maximum_observation(
    propagator: Propagator, start: datetime, end: datetime
) -> tuple[datetime, Observation]:
    low, high = start, end
    for _ in range(28):
        span = high - low
        first = low + span / 3
        second = high - span / 3
        if (
            propagator.observe(first).elevation_deg
            < propagator.observe(second).elevation_deg
        ):
            low = first
        else:
            high = second
    moment = low + (high - low) / 2
    return moment, propagator.observe(moment)


def find_passes(
    satellite: Satellite,
    station: Station,
    start_utc: datetime,
    end_utc: datetime,
    coarse_step_seconds: float = 30.0,
) -> list[PassWindow]:
    """Find visibility intervals within an aware UTC window."""

    start_utc = _as_utc(start_utc)
    end_utc = _as_utc(end_utc)
    if end_utc <= start_utc:
        raise ValueError("O fim da janela deve ser posterior ao início.")
    if coarse_step_seconds <= 0:
        raise ValueError("O passo de busca deve ser positivo.")

    propagator = Propagator(satellite, station)
    threshold = station.min_elevation_deg
    step = timedelta(seconds=coarse_step_seconds)
    passes: list[PassWindow] = []

    previous_time = start_utc
    previous_observation = propagator.observe(previous_time)
    visible = previous_observation.elevation_deg >= threshold
    aos = start_utc if visible else None
    starts_before = visible

    while previous_time < end_utc:
        current_time = min(previous_time + step, end_utc)
        current_observation = propagator.observe(current_time)
        current_visible = current_observation.elevation_deg >= threshold

        if not visible and current_visible:
            aos = _refine_crossing(
                propagator, previous_time, current_time, threshold, rising=True
            )
            starts_before = False
        elif visible and not current_visible and aos is not None:
            los = _refine_crossing(
                propagator, previous_time, current_time, threshold, rising=False
            )
            max_time, maximum = _maximum_observation(propagator, aos, los)
            aos_observation = propagator.observe(aos)
            los_observation = propagator.observe(los)
            passes.append(
                PassWindow(
                    satellite=satellite,
                    aos_utc=aos,
                    los_utc=los,
                    max_utc=max_time,
                    aos_azimuth_deg=aos_observation.azimuth_deg,
                    los_azimuth_deg=los_observation.azimuth_deg,
                    max_elevation_deg=maximum.elevation_deg,
                    max_azimuth_deg=maximum.azimuth_deg,
                    min_range_km=maximum.range_km,
                    starts_before_window=starts_before,
                )
            )
            aos = None
            starts_before = False

        previous_time = current_time
        visible = current_visible

    if visible and aos is not None:
        max_time, maximum = _maximum_observation(propagator, aos, end_utc)
        aos_observation = propagator.observe(aos)
        los_observation = propagator.observe(end_utc)
        passes.append(
            PassWindow(
                satellite=satellite,
                aos_utc=aos,
                los_utc=end_utc,
                max_utc=max_time,
                aos_azimuth_deg=aos_observation.azimuth_deg,
                los_azimuth_deg=los_observation.azimuth_deg,
                max_elevation_deg=maximum.elevation_deg,
                max_azimuth_deg=maximum.azimuth_deg,
                min_range_km=maximum.range_km,
                starts_before_window=starts_before,
                ends_after_window=True,
            )
        )

    return passes
