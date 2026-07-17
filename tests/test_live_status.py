from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_pass_timeline.app import (
    format_countdown,
    moving_window_bounds,
    popup_position,
)


class LiveStatusTests(unittest.TestCase):
    def test_window_keeps_only_thirty_minutes_of_history(self):
        now = datetime(2026, 7, 17, 15, 30, tzinfo=timezone.utc)
        start, end = moving_window_bounds(now, 6)
        self.assertEqual(now - start, timedelta(minutes=30))
        self.assertEqual(end - start, timedelta(hours=6))
        self.assertEqual(end - now, timedelta(hours=5, minutes=30))

    def test_los_countdown_formats_minutes_and_hours(self):
        self.assertEqual(format_countdown(timedelta(minutes=5, seconds=31.2)), "05:32")
        self.assertEqual(
            format_countdown(timedelta(hours=1, minutes=2, seconds=3)), "01:02:03"
        )

    def test_los_countdown_never_becomes_negative(self):
        self.assertEqual(format_countdown(timedelta(seconds=-1)), "00:00")

    def test_popup_opens_to_the_right_when_there_is_room(self):
        position = popup_position((100, 200, 160, 230), (240, 150), (1200, 800))
        self.assertEqual(position[0], 169)

    def test_popup_moves_to_the_left_near_screen_edge(self):
        position = popup_position((1040, 200, 1100, 230), (240, 150), (1200, 800))
        self.assertEqual(position[0], 791)

    def test_popup_is_fully_contained_in_compact_application(self):
        x, y = popup_position((850, 230, 880, 250), (340, 170), (900, 260))
        self.assertGreaterEqual(x, 8)
        self.assertGreaterEqual(y, 8)
        self.assertLessEqual(x + 340, 892)
        self.assertLessEqual(y + 170, 252)


if __name__ == "__main__":
    unittest.main()
