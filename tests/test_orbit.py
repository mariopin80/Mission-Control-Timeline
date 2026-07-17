from datetime import datetime, timedelta, timezone
import math
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_pass_timeline.models import Station
from mission_pass_timeline.orbit import Propagator, find_passes
from mission_pass_timeline.tle import parse_tle
from test_orbital_data import omm_record
from mission_pass_timeline.orbital_data import satellite_from_omm


VANGUARD = """VANGUARD 1
1 00005U 58002B   00179.78495062  .00000023  00000-0  28098-4 0  4753
2 00005  34.2682 331.5174 1849677 331.7664  19.3264 10.82419157413667
"""
UTC = timezone.utc


class OrbitTests(unittest.TestCase):
    def setUp(self):
        self.satellite = parse_tle(VANGUARD)[0]
        self.station = Station("SJC", -23.2089, -45.8609, 600.0, 5.0)

    def test_observation_is_finite_and_physical(self):
        observation = Propagator(self.satellite, self.station).observe(
            datetime(2000, 6, 28, 12, tzinfo=UTC)
        )
        self.assertTrue(math.isfinite(observation.elevation_deg))
        self.assertTrue(0.0 <= observation.azimuth_deg < 360.0)
        self.assertGreater(observation.range_km, 0.0)

    def test_pass_boundaries_meet_mask(self):
        start = datetime(2000, 6, 28, tzinfo=UTC)
        end = start + timedelta(days=2)
        passes = find_passes(self.satellite, self.station, start, end)
        self.assertGreater(len(passes), 0)
        propagator = Propagator(self.satellite, self.station)
        complete = [
            item
            for item in passes
            if not item.starts_before_window and not item.ends_after_window
        ]
        self.assertGreater(len(complete), 0)
        for item in complete:
            self.assertAlmostEqual(
                propagator.observe(item.aos_utc).elevation_deg,
                self.station.min_elevation_deg,
                places=3,
            )
            self.assertAlmostEqual(
                propagator.observe(item.los_utc).elevation_deg,
                self.station.min_elevation_deg,
                places=3,
            )
            self.assertGreaterEqual(
                item.max_elevation_deg, self.station.min_elevation_deg
            )
            self.assertLess(item.aos_utc, item.max_utc)
            self.assertLess(item.max_utc, item.los_utc)

    def test_omm_satellite_propagates(self):
        satellite = satellite_from_omm(omm_record())
        observation = Propagator(satellite, self.station).observe(
            datetime(2000, 6, 28, 12, tzinfo=UTC)
        )
        self.assertTrue(math.isfinite(observation.elevation_deg))
        self.assertGreater(observation.range_km, 0.0)


if __name__ == "__main__":
    unittest.main()
