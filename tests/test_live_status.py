from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mission_pass_timeline.app import (
    AosAlertController,
    format_countdown,
    moving_window_bounds,
    next_upcoming_pass,
    pass_countdown_text,
    popup_position,
)
from mission_pass_timeline.models import PassWindow, Satellite


class LiveStatusTests(unittest.TestCase):
    @staticmethod
    def pass_window() -> PassWindow:
        aos = datetime(2026, 7, 17, 15, 0, tzinfo=timezone.utc)
        satellite = Satellite("TEST", "1 TEST", "2 TEST", 12345, aos)
        return PassWindow(
            satellite,
            aos,
            aos + timedelta(minutes=10),
            aos + timedelta(minutes=5),
            180.0,
            90.0,
            45.0,
            135.0,
            500.0,
        )

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

    def test_pass_countdown_targets_aos_before_pass(self):
        now = datetime(2026, 7, 17, 14, 58, tzinfo=timezone.utc)
        self.assertEqual(pass_countdown_text(self.pass_window(), now), "AOS EM 02:00")

    def test_pass_countdown_targets_los_during_pass(self):
        now = datetime(2026, 7, 17, 15, 6, tzinfo=timezone.utc)
        self.assertEqual(pass_countdown_text(self.pass_window(), now), "LOS EM 04:00")

    def test_pass_countdown_reports_elapsed_time_after_los(self):
        now = datetime(2026, 7, 17, 15, 11, tzinfo=timezone.utc)
        self.assertEqual(pass_countdown_text(self.pass_window(), now), "LOS HÁ 01:00")

    def test_pass_countdown_requires_aware_time(self):
        with self.assertRaises(ValueError):
            pass_countdown_text(self.pass_window(), datetime(2026, 7, 17, 15, 0))

    def test_next_upcoming_pass_selects_earliest_aos_across_satellites(self):
        first = self.pass_window()
        second = self.pass_window()
        second = PassWindow(
            Satellite(
                "LATER",
                "1 LATER",
                "2 LATER",
                54321,
                second.satellite.epoch_utc,
            ),
            second.aos_utc + timedelta(minutes=20),
            second.los_utc + timedelta(minutes=20),
            second.max_utc + timedelta(minutes=20),
            second.aos_azimuth_deg,
            second.los_azimuth_deg,
            second.max_elevation_deg,
            second.max_azimuth_deg,
            second.min_range_km,
        )
        now = first.aos_utc - timedelta(hours=1)
        selected = next_upcoming_pass({54321: [second], 12345: [first]}, now)
        self.assertIs(selected, first)

    def test_next_upcoming_pass_ignores_active_and_finished_passes(self):
        current = self.pass_window()
        now = current.aos_utc + timedelta(minutes=2)
        self.assertIsNone(next_upcoming_pass({12345: [current]}, now))

    def test_two_minute_alert_is_emitted_only_once(self):
        controller = AosAlertController()
        pass_window = self.pass_window()
        self.assertEqual(
            controller.events(
                pass_window, pass_window.aos_utc - timedelta(seconds=120)
            ),
            ["two_minute"],
        )
        self.assertEqual(
            controller.events(
                pass_window, pass_window.aos_utc - timedelta(seconds=119)
            ),
            [],
        )

    def test_final_countdown_emits_five_distinct_alerts(self):
        controller = AosAlertController()
        pass_window = self.pass_window()
        events = []
        for seconds in (5, 4, 3, 2, 1):
            events.extend(
                controller.events(
                    pass_window, pass_window.aos_utc - timedelta(seconds=seconds)
                )
            )
        self.assertEqual(events, ["countdown"] * 5)

    def test_final_countdown_does_not_repeat_within_same_second(self):
        controller = AosAlertController()
        pass_window = self.pass_window()
        now = pass_window.aos_utc - timedelta(seconds=4.8)
        self.assertEqual(controller.events(pass_window, now), ["countdown"])
        self.assertEqual(
            controller.events(pass_window, now + timedelta(milliseconds=100)), []
        )

    def test_alert_state_resets_for_the_next_pass(self):
        controller = AosAlertController()
        first = self.pass_window()
        second = PassWindow(
            first.satellite,
            first.aos_utc + timedelta(hours=1),
            first.los_utc + timedelta(hours=1),
            first.max_utc + timedelta(hours=1),
            first.aos_azimuth_deg,
            first.los_azimuth_deg,
            first.max_elevation_deg,
            first.max_azimuth_deg,
            first.min_range_km,
        )
        self.assertEqual(
            controller.events(first, first.aos_utc - timedelta(seconds=120)),
            ["two_minute"],
        )
        self.assertEqual(
            controller.events(second, second.aos_utc - timedelta(seconds=120)),
            ["two_minute"],
        )

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
