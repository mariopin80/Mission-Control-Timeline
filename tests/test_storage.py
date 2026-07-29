import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_pass_timeline.models import Station
from mission_pass_timeline.storage import SettingsStore


class SettingsStoreTests(unittest.TestCase):
    def test_timeline_choice_persists_without_erasing_station(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory))
            station = Station("PU2PTU", -23.1, -47.7, 550.0, 8.0)
            store.save_station(station)
            store.save_timeline_hours(8)

            reopened = SettingsStore(Path(directory))
            self.assertEqual(reopened.load_timeline_hours(), 8)
            self.assertEqual(reopened.load_station(), station)

    def test_invalid_saved_choice_falls_back_to_six_hours(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory))
            store.config_path.write_text(
                json.dumps({"timeline_hours": 5}), encoding="utf-8"
            )
            self.assertEqual(store.load_timeline_hours(), 6)

    def test_rejects_unsupported_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory))
            with self.assertRaises(ValueError):
                store.save_timeline_hours(5)

    def test_sound_is_enabled_by_default_and_choice_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory))
            self.assertTrue(store.load_sound_enabled())
            store.save_sound_enabled(False)
            self.assertFalse(SettingsStore(Path(directory)).load_sound_enabled())

    def test_invalid_sound_choice_falls_back_to_enabled(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory))
            store.config_path.write_text(
                json.dumps({"sound_enabled": "no"}), encoding="utf-8"
            )
            self.assertTrue(store.load_sound_enabled())

    def test_language_defaults_to_english_and_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory))
            self.assertEqual(store.load_language(), "en")
            store.save_language("pt")
            self.assertEqual(SettingsStore(Path(directory)).load_language(), "pt")

    def test_invalid_language_falls_back_to_english(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory))
            store.config_path.write_text(
                json.dumps({"language": "xx"}), encoding="utf-8"
            )
            self.assertEqual(store.load_language(), "en")

    def test_catalog_list_and_orbital_cache_are_separate_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = SettingsStore(root / "settings", root / "program")
            (root / "program").mkdir()
            store.save_catalog_text("25544\n")
            store.save_orbital_cache(
                [{"NORAD_CAT_ID": "25544"}],
                datetime(2026, 7, 17, tzinfo=timezone.utc),
            )
            self.assertEqual(store.load_catalog_text(), "25544\n")
            self.assertEqual(
                store.load_orbital_cache()["satellites"],
                [{"NORAD_CAT_ID": "25544"}],
            )
            self.assertNotEqual(store.catalog_path.parent, store.cache_path.parent)

    def test_legacy_cache_is_migrated_to_application_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / "program" / "orbital_cache.json"
            legacy.parent.mkdir()
            legacy.write_text(
                json.dumps({"satellites": [{"NORAD_CAT_ID": "25544"}]}),
                encoding="utf-8",
            )
            store = SettingsStore(root / "settings", legacy_cache_path=legacy)
            self.assertEqual(
                store.load_orbital_cache()["satellites"],
                [{"NORAD_CAT_ID": "25544"}],
            )
            self.assertEqual(store.cache_path.parent, root / "settings")
            self.assertTrue(legacy.exists())


if __name__ == "__main__":
    unittest.main()
