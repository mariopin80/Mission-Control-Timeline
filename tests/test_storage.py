import json
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


if __name__ == "__main__":
    unittest.main()
