from datetime import timezone
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_pass_timeline.tle import TleFormatError, parse_tle


VANGUARD = """VANGUARD 1
1 00005U 58002B   00179.78495062  .00000023  00000-0  28098-4 0  4753
2 00005  34.2682 331.5174 1849677 331.7664  19.3264 10.82419157413667
"""
UTC = timezone.utc


class ParseTleTests(unittest.TestCase):
    def test_parses_named_three_line_format(self):
        satellites = parse_tle(VANGUARD)
        self.assertEqual(len(satellites), 1)
        self.assertEqual(satellites[0].name, "VANGUARD 1")
        self.assertEqual(satellites[0].catalog_number, 5)
        self.assertEqual(satellites[0].epoch_utc.tzinfo, UTC)
        self.assertEqual(satellites[0].epoch_utc.year, 2000)

    def test_parses_two_line_format_and_generates_name(self):
        satellites = parse_tle("\n".join(VANGUARD.splitlines()[1:]))
        self.assertEqual(satellites[0].name, "SAT 5")

    def test_rejects_mismatched_catalog_numbers(self):
        bad = VANGUARD.replace("2 00005", "2 00006")
        with self.assertRaises(TleFormatError):
            parse_tle(bad)

    def test_supports_alpha5_catalog_numbers(self):
        alpha5 = VANGUARD.replace("00005", "A0005")
        satellite = parse_tle(alpha5)[0]
        self.assertEqual(satellite.catalog_number, 100005)

    def test_rejects_duplicate_catalogs(self):
        with self.assertRaises(TleFormatError):
            parse_tle(VANGUARD + VANGUARD)

    def test_station_partial_config_uses_real_defaults(self):
        from mission_pass_timeline.models import Station

        station = Station.from_dict({"name": "Teste"})
        self.assertEqual(station.name, "Teste")
        self.assertIsInstance(station.latitude_deg, float)
        self.assertEqual(station.latitude_deg, Station().latitude_deg)


if __name__ == "__main__":
    unittest.main()
