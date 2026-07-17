from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_pass_timeline.timeline import aligned_time_ticks, grid_spec_for_hours


class TimelineLogicTests(unittest.TestCase):
    def test_grid_adapts_to_each_window(self):
        self.assertEqual(grid_spec_for_hours(3), (15, 30))
        self.assertEqual(grid_spec_for_hours(6), (30, 60))
        self.assertEqual(grid_spec_for_hours(8), (30, 60))
        self.assertEqual(grid_spec_for_hours(12), (60, 120))
        self.assertEqual(grid_spec_for_hours(24), (60, 180))

    def test_ticks_are_aligned_to_wall_clock(self):
        start = datetime(2026, 7, 17, 10, 7, tzinfo=timezone.utc)
        end = datetime(2026, 7, 17, 11, 3, tzinfo=timezone.utc)
        ticks = aligned_time_ticks(start, end, 15)
        self.assertEqual(
            [tick.strftime("%H:%M") for tick in ticks],
            ["10:15", "10:30", "10:45", "11:00"],
        )

    def test_ticks_require_aware_datetimes(self):
        start = datetime(2026, 7, 17, 10, 0)
        end = datetime(2026, 7, 17, 11, 0)
        with self.assertRaises(ValueError):
            aligned_time_ticks(start, end, 30)


if __name__ == "__main__":
    unittest.main()
