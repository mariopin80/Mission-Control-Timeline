import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_pass_timeline.orbital_data import (
    CatalogListError,
    OrbitalSourceError,
    catalogs_to_download,
    decode_celestrak_response,
    decode_satnogs_response,
    download_catalogs,
    parse_catalog_numbers,
    satellite_from_omm,
    satellites_from_cache,
)


def omm_record(catalog: int = 5, name: str = "VANGUARD 1") -> dict[str, str]:
    return {
        "OBJECT_NAME": name,
        "OBJECT_ID": "1958-002B",
        "EPOCH": "2000-06-27T18:50:19.733568",
        "MEAN_MOTION": "10.82419157",
        "ECCENTRICITY": "0.1849677",
        "INCLINATION": "34.2682",
        "RA_OF_ASC_NODE": "331.5174",
        "ARG_OF_PERICENTER": "331.7664",
        "MEAN_ANOMALY": "19.3264",
        "EPHEMERIS_TYPE": "0",
        "CLASSIFICATION_TYPE": "U",
        "NORAD_CAT_ID": str(catalog),
        "ELEMENT_SET_NO": "475",
        "REV_AT_EPOCH": "41366",
        "BSTAR": "0.000028098",
        "MEAN_MOTION_DOT": "0.00000023",
        "MEAN_MOTION_DDOT": "0.0",
    }


class CatalogListTests(unittest.TestCase):
    def test_parses_one_catalog_per_line(self):
        self.assertEqual(
            parse_catalog_numbers("25544\n# comentário\n43786\n"), [25544, 43786]
        )

    def test_accepts_catalogs_above_five_digits(self):
        self.assertEqual(parse_catalog_numbers("100058\n"), [100058])

    def test_rejects_duplicate_catalogs(self):
        with self.assertRaises(CatalogListError):
            parse_catalog_numbers("25544\n25544\n")

    def test_rejects_names_and_tle_lines(self):
        with self.assertRaises(CatalogListError):
            parse_catalog_numbers("ISS\n")

    def test_fresh_cache_avoids_duplicate_downloads(self):
        now = datetime(2026, 7, 17, 18, tzinfo=timezone.utc)
        result = catalogs_to_download(
            [5, 6], {5, 6}, now - timedelta(hours=1), now, timedelta(hours=2)
        )
        self.assertEqual(result, [])

    def test_fresh_cache_downloads_only_missing_catalogs(self):
        now = datetime(2026, 7, 17, 18, tzinfo=timezone.utc)
        result = catalogs_to_download(
            [5, 6], {5}, now - timedelta(hours=1), now, timedelta(hours=2)
        )
        self.assertEqual(result, [6])

    def test_old_cache_refreshes_every_catalog(self):
        now = datetime(2026, 7, 17, 18, tzinfo=timezone.utc)
        result = catalogs_to_download(
            [5, 6], {5, 6}, now - timedelta(hours=3), now, timedelta(hours=2)
        )
        self.assertEqual(result, [5, 6])


class OmmDataTests(unittest.TestCase):
    def test_builds_satellite_from_omm(self):
        satellite = satellite_from_omm(omm_record())
        self.assertEqual(satellite.catalog_number, 5)
        self.assertEqual(satellite.name, "VANGUARD 1")
        self.assertEqual(satellite.epoch_utc.tzinfo, timezone.utc)
        self.assertIsNotNone(satellite.omm_fields)

    def test_omm_supports_six_digit_catalog(self):
        satellite = satellite_from_omm(omm_record(100058, "NEW OBJECT"))
        self.assertEqual(satellite.catalog_number, 100058)

    def test_decodes_single_celestrak_record(self):
        payload = json.dumps([omm_record()]).encode()
        fields = decode_celestrak_response(payload, 5)
        self.assertEqual(fields["NORAD_CAT_ID"], "5")

    def test_rejects_wrong_catalog_from_source(self):
        payload = json.dumps([omm_record(6)]).encode()
        with self.assertRaises(Exception):
            decode_celestrak_response(payload, 5)

    def test_cache_follows_requested_order_and_ignores_extra_records(self):
        document = {"satellites": [omm_record(6, "SECOND"), omm_record(5, "FIRST")]}
        satellites = satellites_from_cache(document, [5, 6, 7])
        self.assertEqual([item.catalog_number for item in satellites], [5, 6])

    def test_source_error_switches_remaining_downloads_to_fallback(self):
        primary_calls: list[int] = []
        fallback_calls: list[int] = []

        def primary(catalog: int) -> dict[str, str]:
            primary_calls.append(catalog)
            raise OrbitalSourceError("servidor indisponível")

        def fallback(catalog: int) -> dict[str, str]:
            fallback_calls.append(catalog)
            return omm_record(catalog)

        downloaded, errors = download_catalogs([5, 6, 7], primary, fallback)
        self.assertEqual(sorted(downloaded), [5, 6, 7])
        self.assertEqual(primary_calls, [5])
        self.assertEqual(fallback_calls, [5, 6, 7])
        self.assertEqual(errors, [])

    def test_decodes_satnogs_tle_as_omm_cache_record(self):
        record = {
            "tle0": "0 ISS (ZARYA)",
            "tle1": "1 25544U 98067A   26198.57280181  .00003563  00000-0  72724-4 0  9991",
            "tle2": "2 25544  51.6316 149.7201 0006795 306.9083  53.1282 15.49033131576463",
            "norad_cat_id": 25544,
        }
        fields = decode_satnogs_response(json.dumps([record]).encode(), 25544)
        self.assertEqual(fields["NORAD_CAT_ID"], "25544")
        self.assertEqual(fields["OBJECT_NAME"], "ISS (ZARYA)")
        self.assertEqual(fields["_DATA_SOURCE"], "SATNOGS")


if __name__ == "__main__":
    unittest.main()
