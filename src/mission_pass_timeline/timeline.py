from __future__ import annotations

import hashlib
import tkinter as tk
from collections.abc import Callable
from datetime import datetime, timedelta

from .i18n import translate
from .models import PassWindow, Satellite

PassAnchor = tuple[int, int, int, int]
PassSelectionHandler = Callable[[PassWindow | None, PassAnchor | None], None]


def grid_spec_for_hours(window_hours: float) -> tuple[int, int]:
    """Return minor-grid and labeled-grid spacing in minutes."""

    if window_hours <= 3:
        return 15, 30
    if window_hours <= 8:
        return 30, 60
    if window_hours <= 12:
        return 60, 120
    return 60, 180


def aligned_time_ticks(
    start: datetime, end: datetime, spacing_minutes: int
) -> list[datetime]:
    """Build wall-clock-aligned ticks inside an aware time window."""

    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("Os limites da linha do tempo devem possuir fuso horário.")
    if end <= start:
        raise ValueError("O fim da linha do tempo deve ser posterior ao início.")
    if spacing_minutes <= 0:
        raise ValueError("O espaçamento da grade deve ser positivo.")

    tick = start.replace(second=0, microsecond=0)
    minutes_since_midnight = tick.hour * 60 + tick.minute
    tick -= timedelta(minutes=minutes_since_midnight % spacing_minutes)
    if tick < start:
        tick += timedelta(minutes=spacing_minutes)

    ticks: list[datetime] = []
    step = timedelta(minutes=spacing_minutes)
    while tick <= end:
        ticks.append(tick)
        tick += step
    return ticks


class TimelineView(tk.Frame):
    BACKGROUND = "#071019"
    PANEL = "#0d1822"
    GRID_MINOR = "#18303f"
    GRID_MAJOR = "#29495b"
    TEXT = "#dce8ef"
    MUTED = "#78909c"
    NOW = "#ff334f"
    ROW_HEIGHT = 43
    HEADER_HEIGHT = 58
    LABEL_WIDTH = 205
    PALETTE = (
        "#26c6da",
        "#42a5f5",
        "#7e57c2",
        "#ec407a",
        "#ff7043",
        "#ffca28",
        "#66bb6a",
        "#26a69a",
    )

    def __init__(
        self,
        parent: tk.Misc,
        on_pass_selected: PassSelectionHandler | None = None,
        language: str = "en",
    ):
        super().__init__(parent, bg=self.BACKGROUND)
        self.on_pass_selected = on_pass_selected
        self.language = language
        self.satellites: list[Satellite] = []
        self.passes: dict[int, list[PassWindow]] = {}
        self.window_start_local: datetime | None = None
        self.window_end_local: datetime | None = None
        self._pass_items: dict[int, PassWindow] = {}
        self._live_details: dict[int, str] = {}
        self._message: tuple[str, str] | None = None

        self.header = tk.Canvas(
            self,
            height=self.HEADER_HEIGHT,
            bg=self.PANEL,
            highlightthickness=0,
        )
        self.header.grid(row=0, column=0, sticky="ew")
        self.body = tk.Canvas(
            self,
            bg=self.BACKGROUND,
            highlightthickness=0,
            yscrollincrement=self.ROW_HEIGHT,
        )
        self.scrollbar = tk.Scrollbar(
            self, orient="vertical", command=self.body.yview, width=12
        )
        self.body.configure(yscrollcommand=self.scrollbar.set)
        self.body.grid(row=1, column=0, sticky="nsew")
        self.scrollbar.grid(row=1, column=1, sticky="ns")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.body.bind("<Button-1>", self._click)
        self.header.bind("<Button-1>", self._clear_selection)
        self.body.bind("<MouseWheel>", self._wheel)
        self.body.bind("<Button-4>", lambda _event: self.body.yview_scroll(-1, "units"))
        self.body.bind("<Button-5>", lambda _event: self.body.yview_scroll(1, "units"))
        self.bind("<Configure>", lambda _event: self.render())

    def set_language(self, language: str) -> None:
        self.language = language
        self.render()

    def set_data(
        self,
        satellites: list[Satellite],
        passes: dict[int, list[PassWindow]],
        window_start_local: datetime,
        window_end_local: datetime,
    ) -> None:
        self._message = None
        self.satellites = satellites
        self.passes = passes
        self.window_start_local = window_start_local
        self.window_end_local = window_end_local
        self.render()

    def set_window(
        self, window_start_local: datetime, window_end_local: datetime
    ) -> None:
        if self._message is not None:
            return
        self.window_start_local = window_start_local
        self.window_end_local = window_end_local
        self.render()

    def set_live_details(self, details: dict[int, str]) -> None:
        """Store compact live observations rendered beside active pass bars."""

        self._live_details = details

    def _window_hours(self) -> float:
        assert self.window_start_local is not None
        assert self.window_end_local is not None
        return (
            self.window_end_local - self.window_start_local
        ).total_seconds() / 3600.0

    def _time_x(self, moment: datetime) -> float:
        assert self.window_start_local is not None
        assert self.window_end_local is not None
        width = max(self.body.winfo_width() - self.LABEL_WIDTH, 100)
        ratio = (moment - self.window_start_local).total_seconds() / (
            self.window_end_local - self.window_start_local
        ).total_seconds()
        return self.LABEL_WIDTH + max(0.0, min(1.0, ratio)) * width

    @classmethod
    def _satellite_color(cls, satellite: Satellite) -> str:
        digest = hashlib.sha1(str(satellite.catalog_number).encode("ascii")).digest()
        return cls.PALETTE[digest[0] % len(cls.PALETTE)]

    @staticmethod
    def _is_labeled_tick(tick: datetime, label_spacing_minutes: int) -> bool:
        minutes_since_midnight = tick.hour * 60 + tick.minute
        return minutes_since_midnight % label_spacing_minutes == 0

    @staticmethod
    def _tick_label(tick: datetime) -> str:
        if tick.hour == 0 and tick.minute == 0:
            return tick.strftime("%d/%m  %H:%M")
        return tick.strftime("%H:%M")

    def render(self) -> None:
        if self.body.winfo_width() <= 2:
            return
        if self._message is not None:
            self._render_message(*self._message)
            return
        if self.window_start_local is None or self.window_end_local is None:
            return

        vertical_position = self.body.yview()[0] if self.satellites else 0.0
        self.header.delete("all")
        self.body.delete("all")
        self._pass_items.clear()

        width = self.body.winfo_width()
        total_height = max(
            len(self.satellites) * self.ROW_HEIGHT, self.body.winfo_height()
        )
        self.body.configure(scrollregion=(0, 0, width, total_height))

        self.header.create_rectangle(
            0, 0, self.LABEL_WIDTH, self.HEADER_HEIGHT, fill="#101d27", outline=""
        )
        self.header.create_text(
            16,
            35,
            text=translate(self.language, "satellite"),
            anchor="w",
            fill=self.MUTED,
            font=("Segoe UI Semibold", 9),
        )

        minor_minutes, label_minutes = grid_spec_for_hours(self._window_hours())
        ticks = aligned_time_ticks(
            self.window_start_local, self.window_end_local, minor_minutes
        )
        for tick in ticks:
            x = self._time_x(tick)
            labeled = self._is_labeled_tick(tick, label_minutes)
            color = self.GRID_MAJOR if labeled else self.GRID_MINOR
            self.header.create_line(x, 31, x, self.HEADER_HEIGHT, fill=color)
            if labeled:
                self.header.create_text(
                    x + 4,
                    17,
                    text=self._tick_label(tick),
                    anchor="w",
                    fill=self.TEXT,
                    font=("Consolas", 9, "bold"),
                )

        # Row backgrounds are painted first so the time grid remains visible.
        for index, satellite in enumerate(self.satellites):
            y0 = index * self.ROW_HEIGHT
            y1 = y0 + self.ROW_HEIGHT
            row_fill = "#09141d" if index % 2 == 0 else "#071019"
            self.body.create_rectangle(0, y0, width, y1, fill=row_fill, outline="")
            self.body.create_rectangle(
                0, y0, self.LABEL_WIDTH, y1, fill="#0c1821", outline=""
            )
            self.body.create_line(0, y1, width, y1, fill="#152a37")
            self.body.create_text(
                15,
                y0 + 16,
                text=satellite.name,
                anchor="w",
                fill=self.TEXT,
                font=("Segoe UI Semibold", 10),
            )
            self.body.create_text(
                15,
                y0 + 31,
                text=f"NORAD {satellite.catalog_number}",
                anchor="w",
                fill=self.MUTED,
                font=("Segoe UI", 8),
            )

        for tick in ticks:
            x = self._time_x(tick)
            labeled = self._is_labeled_tick(tick, label_minutes)
            color = self.GRID_MAJOR if labeled else self.GRID_MINOR
            self.body.create_line(x, 0, x, total_height, fill=color)

        # Pass bars are clipped to the moving window and painted above the grid.
        for index, satellite in enumerate(self.satellites):
            y0 = index * self.ROW_HEIGHT
            y1 = y0 + self.ROW_HEIGHT
            for pass_window in self.passes.get(satellite.catalog_number, []):
                local_aos = pass_window.aos_utc.astimezone(
                    self.window_start_local.tzinfo
                )
                local_los = pass_window.los_utc.astimezone(
                    self.window_start_local.tzinfo
                )
                if (
                    local_los <= self.window_start_local
                    or local_aos >= self.window_end_local
                ):
                    continue
                visible_aos = max(local_aos, self.window_start_local)
                visible_los = min(local_los, self.window_end_local)
                x0 = self._time_x(visible_aos)
                x1 = self._time_x(visible_los)
                if x1 - x0 < 3:
                    x1 = x0 + 3
                color = self._satellite_color(satellite)
                item = self.body.create_rectangle(
                    x0,
                    y0 + 8,
                    x1,
                    y1 - 8,
                    fill=color,
                    outline="#e9f7fb",
                    width=1,
                    tags=("pass",),
                )
                self._pass_items[item] = pass_window
                if x1 - x0 >= 37:
                    self.body.create_text(
                        (x0 + x1) / 2,
                        (y0 + y1) / 2,
                        text=f"{pass_window.max_elevation_deg:.0f}°",
                        fill="#041017",
                        font=("Segoe UI Semibold", 9),
                    )
                live_detail = self._live_details.get(satellite.catalog_number)
                now_local = datetime.now().astimezone(self.window_start_local.tzinfo)
                if live_detail and local_aos <= now_local < local_los:
                    self.body.create_text(
                        x1 + 8,
                        (y0 + y1) / 2,
                        text=live_detail,
                        anchor="w",
                        fill="#7be3aa",
                        font=("Consolas", 9, "bold"),
                    )

        if self.satellites:
            self.body.yview_moveto(vertical_position)
        self.update_now_marker()

    def update_now_marker(self, now: datetime | None = None) -> None:
        self.header.delete("now_marker")
        self.body.delete("now_marker")
        if self.window_start_local is None or self.window_end_local is None:
            return
        now = now or datetime.now().astimezone()
        if not self.window_start_local <= now < self.window_end_local:
            return
        x = self._time_x(now)
        total_height = max(
            len(self.satellites) * self.ROW_HEIGHT, self.body.winfo_height()
        )
        self.body.create_line(
            x, 0, x, total_height, fill=self.NOW, width=2, tags=("now_marker",)
        )
        self.header.create_polygon(
            x - 6,
            self.HEADER_HEIGHT - 12,
            x + 6,
            self.HEADER_HEIGHT - 12,
            x,
            self.HEADER_HEIGHT - 3,
            fill=self.NOW,
            outline="",
            tags=("now_marker",),
        )
        label_center = x
        timeline_left = self.LABEL_WIDTH
        timeline_right = self.body.winfo_width()
        if x - 32 < timeline_left:
            label_center = x + 34
        elif x + 32 > timeline_right:
            label_center = x - 34
        self.header.create_rectangle(
            label_center - 32,
            27,
            label_center + 32,
            43,
            fill=self.PANEL,
            outline="",
            tags=("now_marker",),
        )
        self.header.create_text(
            label_center,
            41,
            text=now.strftime("%H:%M:%S"),
            anchor="s",
            fill=self.NOW,
            font=("Consolas", 9, "bold"),
            tags=("now_marker",),
        )

    def show_message(self, title: str, message: str) -> None:
        self.satellites = []
        self.passes = {}
        self.window_start_local = None
        self.window_end_local = None
        self._message = (title, message)
        self.render()

    def _render_message(self, title: str, message: str) -> None:
        self.header.delete("all")
        self.body.delete("all")
        self._pass_items.clear()
        width = max(self.body.winfo_width(), 500)
        height = max(self.body.winfo_height(), 300)
        self.body.configure(scrollregion=(0, 0, width, height))
        self.body.yview_moveto(0)
        self.header.create_text(
            16,
            35,
            text=translate(self.language, "timeline"),
            anchor="w",
            fill=self.MUTED,
            font=("Segoe UI Semibold", 9),
        )
        self.body.create_text(
            width / 2,
            height / 2 - 18,
            text=title,
            fill=self.TEXT,
            font=("Segoe UI Semibold", 17),
        )
        self.body.create_text(
            width / 2,
            height / 2 + 18,
            text=message,
            fill=self.MUTED,
            font=("Segoe UI", 10),
            justify="center",
        )

    def pass_at(self, x: int, y: int) -> tuple[PassWindow, int] | None:
        """Return the pass and canvas item at visible canvas coordinates."""

        canvas_y = self.body.canvasy(y)
        items = self.body.find_overlapping(x, canvas_y, x, canvas_y)
        for item in reversed(items):
            pass_window = self._pass_items.get(item)
            if pass_window is not None:
                return pass_window, item
        return None

    def _click(self, event: tk.Event) -> None:
        if self.on_pass_selected is None:
            return
        selected = self.pass_at(event.x, event.y)
        if selected is None:
            self.on_pass_selected(None, None)
            return

        pass_window, item = selected
        bounds = self.body.bbox(item)
        if bounds is None:
            self.on_pass_selected(pass_window, None)
            return
        visible_top = self.body.canvasy(0)
        root_x = self.body.winfo_rootx()
        root_y = self.body.winfo_rooty()
        anchor = (
            root_x + int(bounds[0]),
            root_y + int(bounds[1] - visible_top),
            root_x + int(bounds[2]),
            root_y + int(bounds[3] - visible_top),
        )
        self.on_pass_selected(pass_window, anchor)

    def _clear_selection(self, _event: tk.Event) -> None:
        if self.on_pass_selected is not None:
            self.on_pass_selected(None, None)

    def _wheel(self, event: tk.Event) -> None:
        if self.on_pass_selected is not None:
            self.on_pass_selected(None, None)
        self.body.yview_scroll(int(-event.delta / 120), "units")
