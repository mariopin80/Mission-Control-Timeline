from __future__ import annotations

import ctypes
import math
import queue
import sys
import threading
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tkinter import ttk

from . import __version__
from .dialogs import SetupDialog
from .i18n import translate
from .models import PassWindow, Satellite, Station
from .orbital_data import (
    CatalogListError,
    OrbitalDataError,
    catalogs_to_download,
    download_catalogs,
    parse_catalog_numbers,
    satellites_from_cache,
)
from .orbit import Propagator, find_passes
from .storage import SettingsStore
from .timeline import PassAnchor, TimelineView

UTC = timezone.utc
WINDOW_OPTIONS = (3, 6, 8, 12, 24)
CALCULATION_REFRESH = timedelta(minutes=5)
CALCULATION_MARGIN = timedelta(minutes=30)
HISTORY_DURATION = timedelta(minutes=15)
NEXT_PASS_LOOKAHEAD = timedelta(hours=24)
ORBITAL_UPDATE_INTERVAL = timedelta(hours=24)
CELESTRAK_MIN_REFRESH = timedelta(hours=2)
TWO_MINUTE_ALERT_SECONDS = 120
FINAL_COUNTDOWN_SECONDS = 5


def bundled_asset(relative_path: str) -> Path:
    """Return an asset path in source runs and PyInstaller builds."""

    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return bundle_root / relative_path


def format_countdown(duration: timedelta) -> str:
    """Format a non-negative LOS countdown as MM:SS or HH:MM:SS."""

    total_seconds = max(0, math.ceil(duration.total_seconds()))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def pass_countdown_text(
    pass_window: PassWindow, now_utc: datetime, language: str = "en"
) -> str:
    """Describe the next boundary of a pass, or how long ago LOS occurred."""

    if now_utc.tzinfo is None:
        raise ValueError("O instante do contador deve possuir fuso horário.")
    now_utc = now_utc.astimezone(UTC)
    if now_utc < pass_window.aos_utc:
        return translate(
            language,
            "aos_in",
            countdown=format_countdown(pass_window.aos_utc - now_utc),
        )
    if now_utc < pass_window.los_utc:
        return translate(
            language,
            "los_in",
            countdown=format_countdown(pass_window.los_utc - now_utc),
        )
    return translate(
        language,
        "los_ago",
        countdown=format_countdown(now_utc - pass_window.los_utc),
    )


def next_upcoming_pass(
    results: dict[int, list[PassWindow]], now_utc: datetime
) -> PassWindow | None:
    """Return the pass with the earliest future AOS across all satellites."""

    if now_utc.tzinfo is None:
        raise ValueError("O instante da próxima passagem deve possuir fuso horário.")
    now_utc = now_utc.astimezone(UTC)
    return min(
        (
            pass_window
            for passes in results.values()
            for pass_window in passes
            if pass_window.aos_utc > now_utc
        ),
        key=lambda pass_window: pass_window.aos_utc,
        default=None,
    )


class AosAlertController:
    """Emit each alert at most once for the currently upcoming pass."""

    def __init__(self) -> None:
        self._pass_key: tuple[int, datetime] | None = None
        self._two_minute_sent = False
        self._countdown_sent: set[int] = set()

    def events(self, pass_window: PassWindow | None, now_utc: datetime) -> list[str]:
        if now_utc.tzinfo is None:
            raise ValueError("O instante dos alertas deve possuir fuso horário.")
        if pass_window is None:
            self._reset(None)
            return []

        key = (pass_window.satellite.catalog_number, pass_window.aos_utc)
        if key != self._pass_key:
            self._reset(key)

        seconds_until_aos = (
            pass_window.aos_utc - now_utc.astimezone(UTC)
        ).total_seconds()
        if seconds_until_aos <= 0:
            return []

        events: list[str] = []
        if (
            FINAL_COUNTDOWN_SECONDS < seconds_until_aos <= TWO_MINUTE_ALERT_SECONDS
            and not self._two_minute_sent
        ):
            self._two_minute_sent = True
            events.append("two_minute")

        countdown_second = math.ceil(seconds_until_aos)
        if (
            1 <= countdown_second <= FINAL_COUNTDOWN_SECONDS
            and countdown_second not in self._countdown_sent
        ):
            self._countdown_sent.add(countdown_second)
            events.append("countdown")
        return events

    def _reset(self, key: tuple[int, datetime] | None) -> None:
        self._pass_key = key
        self._two_minute_sent = False
        self._countdown_sent.clear()


def moving_window_bounds(center: datetime, hours: int) -> tuple[datetime, datetime]:
    """Place the current instant 15 minutes after the start of a fixed span."""

    if center.tzinfo is None:
        raise ValueError("O centro da janela deve possuir fuso horário.")
    if hours <= 0:
        raise ValueError("A duração da janela deve ser positiva.")
    start = center - HISTORY_DURATION
    return start, start + timedelta(hours=hours)


def popup_position(
    anchor: PassAnchor | None,
    popup_size: tuple[int, int],
    screen_size: tuple[int, int],
) -> tuple[int, int]:
    """Place a card inside the application, right of a pass when possible."""

    width, height = popup_size
    screen_width, screen_height = screen_size
    if anchor is None:
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
    else:
        left, top, right, bottom = anchor
        x = right + 9
        y = top + (bottom - top - height) // 2
        if x + width > screen_width - 8:
            x = left - width - 9
    return (
        max(8, min(x, screen_width - width - 8)),
        max(8, min(y, screen_height - height - 8)),
    )


class MissionPassApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.store = SettingsStore()
        self.station = self.store.load_station()
        self.timeline_hours = self.store.load_timeline_hours()
        self.sound_enabled = self.store.load_sound_enabled()
        self.language = self.store.load_language()
        self.satellites: list[Satellite] = []
        self.catalogs: list[int] = []
        self._pass_results: dict[int, list[PassWindow]] = {}
        self._live_propagators: dict[int, Propagator] = {}
        self._pass_popup: tk.Frame | None = None
        self._selected_pass: PassWindow | None = None
        self._pass_countdown_label: tk.Label | None = None
        self._visible_pass_total = 0
        self._calculation_error_count = 0
        self._display_ready = False
        self._calculation_id = 0
        self._calculation_in_progress = False
        self._last_calculation_center: datetime | None = None
        self._orbital_update_in_progress = False
        self._last_orbital_update_attempt: datetime | None = None
        self._last_orbital_cache_update: datetime | None = None
        self._orbital_status = self._t("no_orbital_data")
        self._aos_alerts = AosAlertController()
        self._result_queue: queue.Queue[
            tuple[
                int,
                list[Satellite],
                datetime,
                dict[int, list[PassWindow]],
                list[str],
            ]
        ] = queue.Queue()
        self._orbital_result_queue: queue.Queue[
            tuple[datetime, list[int], dict[int, dict[str, str]], list[str]]
        ] = queue.Queue()

        self._configure_root()
        self._configure_styles()
        self._build_ui()
        self._load_saved_catalogs()
        self._poll_calculation_results()
        self._poll_orbital_results()
        self._tick()

    def _t(self, key: str, **values: object) -> str:
        return translate(self.language, key, **values)

    def _configure_root(self) -> None:
        self.root.title(f"Mission Control Timeline {__version__}")
        self.root.geometry("1280x720")
        self.root.minsize(900, 260)
        self.root.configure(bg="#071019")

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background="#111b24", foreground="#dce8ef")
        style.configure("TFrame", background="#111b24")
        style.configure(
            "TLabel", background="#111b24", foreground="#dce8ef", font=("Segoe UI", 10)
        )
        style.configure(
            "Title.TLabel",
            background="#111b24",
            foreground="#ffffff",
            font=("Segoe UI Semibold", 16),
        )
        style.configure(
            "Hint.TLabel",
            background="#111b24",
            foreground="#78909c",
            font=("Segoe UI", 9),
        )
        style.configure(
            "Station.TLabel",
            background="#111b24",
            foreground="#9fb3bd",
            font=("Segoe UI", 10),
        )
        style.configure(
            "TButton",
            background="#1d303d",
            foreground="#e8f1f5",
            borderwidth=0,
            padding=(13, 8),
            font=("Segoe UI Semibold", 9),
        )
        style.map("TButton", background=[("active", "#29495b")])
        style.configure("Accent.TButton", background="#d62b45", foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#f03a54")])
        style.configure(
            "TEntry",
            fieldbackground="#09141d",
            foreground="#e8f1f5",
            insertcolor="#ffffff",
            bordercolor="#29495b",
            padding=7,
        )
        style.configure(
            "Timeline.TCombobox",
            fieldbackground="#09141d",
            background="#1d303d",
            foreground="#e8f1f5",
            arrowcolor="#e8f1f5",
            bordercolor="#29495b",
            lightcolor="#29495b",
            darkcolor="#29495b",
            padding=6,
        )
        style.map(
            "Timeline.TCombobox",
            fieldbackground=[("readonly", "#09141d")],
            foreground=[("readonly", "#e8f1f5")],
        )
        style.configure(
            "Setup.TNotebook",
            background="#111b24",
            borderwidth=0,
            tabmargins=(0, 0, 0, 0),
        )
        style.configure(
            "Setup.TNotebook.Tab",
            background="#1d303d",
            foreground="#dce8ef",
            borderwidth=0,
            padding=(16, 9),
            font=("Segoe UI Semibold", 9),
        )
        style.map(
            "Setup.TNotebook.Tab",
            background=[
                ("selected", "#29495b"),
                ("active", "#233b4a"),
            ],
            foreground=[
                ("selected", "#ffffff"),
                ("active", "#ffffff"),
            ],
        )

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=(18, 13))
        top.pack(fill="x")
        title_group = ttk.Frame(top)
        title_group.pack(side="left")
        ttk.Label(
            title_group, text="MISSION CONTROL TIMELINE", style="Title.TLabel"
        ).pack(
            anchor="w"
        )
        self.station_label = ttk.Label(title_group, style="Station.TLabel")
        self.station_label.pack(anchor="w", pady=(2, 0))

        controls = ttk.Frame(top)
        controls.pack(side="right")
        self.setup_button = ttk.Button(controls, command=self.open_setup)
        self.setup_button.pack(side="left", padx=4)
        self.update_button = ttk.Button(controls, command=self.update_orbital_data)
        self.update_button.pack(side="left", padx=4)
        self.sound_button = ttk.Button(controls, text="", command=self._toggle_sound)
        self.sound_button.pack(side="left", padx=4)
        self._refresh_sound_button()
        self.window_caption = ttk.Label(controls, style="Hint.TLabel")
        self.window_caption.pack(
            side="left", padx=(18, 7)
        )
        self.window_variable = tk.StringVar(value=f"{self.timeline_hours} h")
        self.window_selector = ttk.Combobox(
            controls,
            width=6,
            state="readonly",
            style="Timeline.TCombobox",
            textvariable=self.window_variable,
            values=tuple(f"{hours} h" for hours in WINDOW_OPTIONS),
        )
        self.window_selector.pack(side="left")
        self.window_selector.bind("<<ComboboxSelected>>", self._window_changed)

        self.window_bar = tk.Frame(self.root, bg="#0c1720", height=44)
        self.window_bar.pack(fill="x")
        self.window_bar.pack_propagate(False)
        self.window_label = tk.Label(
            self.window_bar,
            bg="#0c1720",
            fg="#e6f0f5",
            font=("Segoe UI Semibold", 11),
        )
        self.window_label.pack(side="left", padx=18)
        self.tle_label = tk.Label(
            self.window_bar,
            bg="#0c1720",
            fg="#78909c",
            font=("Segoe UI", 9),
        )
        self.tle_label.pack(side="right", padx=18)

        self.timeline = TimelineView(
            self.root,
            on_pass_selected=self.show_pass_details,
            language=self.language,
        )
        self.timeline.pack(fill="both", expand=True)
        self.root.bind_all("<Button-1>", self._global_click, add="+")
        self._refresh_labels()
        self._apply_language()

    def _window_bounds(
        self, center: datetime | None = None
    ) -> tuple[datetime, datetime]:
        center = center or datetime.now().astimezone()
        if center.tzinfo is None:
            center = center.astimezone()
        return moving_window_bounds(center, self.timeline_hours)

    def _refresh_window_label(self, now: datetime | None = None) -> None:
        now = now or datetime.now().astimezone()
        next_pass = (
            next_upcoming_pass(self._pass_results, now.astimezone(UTC))
            if self._display_ready
            else None
        )
        if next_pass is None:
            next_pass_text = self._t("next_pass_none")
        else:
            countdown = format_countdown(next_pass.aos_utc - now.astimezone(UTC))
            next_pass_text = self._t(
                "next_pass",
                name=next_pass.satellite.name,
                countdown=countdown,
            )
        self.window_label.configure(text=f"{now:%d/%m/%Y}  •  {next_pass_text}")

    def _emit_alert_sound(self, event: str) -> None:
        if sys.platform != "win32":
            try:
                self.root.bell()
            except tk.TclError:
                pass
            return

        def play() -> None:
            try:
                import winsound

                frequency = 1050 if event == "two_minute" else 1450
                duration_ms = 350 if event == "two_minute" else 160
                winsound.Beep(frequency, duration_ms)
            except (ImportError, RuntimeError):
                pass

        threading.Thread(target=play, daemon=True).start()

    def _refresh_sound_button(self) -> None:
        self.sound_button.configure(
            text=self._t("sound_on") if self.sound_enabled else self._t("sound_muted")
        )

    def _toggle_sound(self) -> None:
        self.sound_enabled = not self.sound_enabled
        self.store.save_sound_enabled(self.sound_enabled)
        self._refresh_sound_button()

    def _update_aos_alerts(self, now: datetime) -> None:
        next_pass = (
            next_upcoming_pass(self._pass_results, now.astimezone(UTC))
            if self._display_ready
            else None
        )
        for event in self._aos_alerts.events(next_pass, now.astimezone(UTC)):
            if self.sound_enabled:
                self._emit_alert_sound(event)

    def _refresh_labels(self) -> None:
        self.station_label.configure(
            text=(
                f"{self.station.name}  •  {self.station.latitude_deg:+.5f}°, "
                f"{self.station.longitude_deg:+.5f}°  •  {self._t('mask')} "
                f"{self.station.min_elevation_deg:.1f}°"
            )
        )
        self._refresh_window_label()
        if self.satellites:
            newest = max(satellite.epoch_utc for satellite in self.satellites)
            now_utc = datetime.now(UTC)
            old_count = sum(
                (now_utc - satellite.epoch_utc).total_seconds() > 14 * 86400
                for satellite in self.satellites
            )
            warning = (
                f"  •  {self._t('old_data_count', count=old_count)}"
                if old_count
                else ""
            )
            pass_summary = (
                f"  •  {self._t('passes_count', count=self._visible_pass_total)}"
                if self._display_ready
                else ""
            )
            error_summary = (
                f"  •  {self._t('errors_count', count=self._calculation_error_count)}"
                if self._calculation_error_count
                else ""
            )
            self.tle_label.configure(
                text=(
                    f"{self._t('satellites_count', count=len(self.satellites))}"
                    f"{pass_summary}  •  {self._orbital_status}  •  "
                    f"{self._t('epoch')} {newest:%d/%m/%Y %H:%M} UTC"
                    f"{warning}{error_summary}"
                ),
                fg=(
                    "#ffb74d"
                    if old_count or self._calculation_error_count
                    else "#78909c"
                ),
            )
        else:
            self.tle_label.configure(text=self._orbital_status, fg="#78909c")

    def _load_saved_catalogs(self) -> None:
        text = self.store.load_catalog_text()
        if text is None:
            self.timeline.show_message(
                self._t("register_satellites"),
                self._t("register_satellites_message"),
            )
            return
        try:
            self.catalogs = parse_catalog_numbers(text)
        except CatalogListError:
            self.timeline.show_message(
                self._t("saved_list_error"),
                self._t("saved_list_error_message"),
            )
            return
        self._load_cached_satellites()
        self.update_orbital_data()

    def open_setup(self) -> None:
        SetupDialog(
            self.root,
            self.station,
            list(self.catalogs),
            self.language,
            self.store.directory,
            self._save_setup,
        )

    def _save_setup(
        self,
        station: Station,
        catalogs: list[int],
        language: str,
        data_directory: Path,
        copy_existing_data: bool,
    ) -> None:
        station_changed = station != self.station
        catalogs_changed = catalogs != self.catalogs
        language_changed = language != self.language
        storage_changed = data_directory.resolve() != self.store.directory.resolve()

        if storage_changed:
            self.store = self.store.relocate(
                data_directory,
                copy_existing=copy_existing_data,
            )
            self.store.save_timeline_hours(self.timeline_hours)
            self.store.save_sound_enabled(self.sound_enabled)
            if self.catalogs and not catalogs_changed:
                self.store.save_catalog_text(
                    "\n".join(str(value) for value in self.catalogs) + "\n"
                )
        self.station = station
        self.store.save_station(station)
        self.language = language
        self.store.save_language(language)
        if language_changed:
            self._apply_language()
        if catalogs_changed:
            self._save_catalogs(catalogs)
            return
        if station_changed:
            self._live_propagators.clear()
            if self.satellites:
                self.calculate()
        self._refresh_labels()

    def _save_catalogs(self, catalogs: list[int]) -> None:
        self.catalogs = catalogs
        self.satellites = []
        self._calculation_id += 1
        self._calculation_in_progress = False
        self._display_ready = False
        self._pass_results = {}
        self._visible_pass_total = 0
        self._calculation_error_count = 0
        self._live_propagators.clear()
        self._close_pass_popup()
        self.store.save_catalog_text("\n".join(str(value) for value in catalogs) + "\n")
        self._load_cached_satellites()
        self.update_orbital_data()

    def _load_cached_satellites(self) -> None:
        cache = self.store.load_orbital_cache()
        try:
            satellites = satellites_from_cache(cache, self.catalogs)
        except OrbitalDataError:
            satellites = []
        self.satellites = satellites
        if satellites:
            timestamp = str(cache.get("updated_at_utc", ""))
            try:
                updated_utc = datetime.fromisoformat(timestamp).astimezone(UTC)
                self._last_orbital_cache_update = updated_utc
                updated = updated_utc.astimezone()
                self._orbital_status = (
                    f"{self._t('local_cache')} {updated:%d/%m %H:%M}"
                )
            except ValueError:
                self._orbital_status = self._t("local_cache")
            self._refresh_labels()
            self.calculate()
        else:
            self._orbital_status = self._t("waiting_orbital")
            self._refresh_labels()
            self.timeline.show_message(
                self._t("updating_orbital"),
                self._t("first_run_internet"),
            )

    def update_orbital_data(self) -> None:
        if not self.catalogs or self._orbital_update_in_progress:
            return
        cache = self.store.load_orbital_cache()
        try:
            cached_satellites = satellites_from_cache(cache, self.catalogs)
        except OrbitalDataError:
            cached_satellites = []
        cached_catalogs = {item.catalog_number for item in cached_satellites}
        now_utc = datetime.now(UTC)
        catalogs = catalogs_to_download(
            self.catalogs,
            cached_catalogs,
            self._last_orbital_cache_update,
            now_utc,
            CELESTRAK_MIN_REFRESH,
        )
        if not catalogs:
            self._last_orbital_update_attempt = self._last_orbital_cache_update
            self._orbital_status = (
                f"{self._t('current_cache')} "
                f"{self._last_orbital_cache_update.astimezone():%d/%m %H:%M}"
            )
            self._refresh_labels()
            return

        self._orbital_update_in_progress = True
        attempted_at = now_utc
        self._last_orbital_update_attempt = attempted_at
        self._orbital_status = self._t("updating_celestrak")
        self._refresh_labels()
        catalog_snapshot = list(self.catalogs)

        def worker() -> None:
            downloaded, errors = download_catalogs(catalogs)
            self._orbital_result_queue.put(
                (attempted_at, catalog_snapshot, downloaded, errors)
            )

        threading.Thread(target=worker, daemon=True).start()

    def _poll_orbital_results(self) -> None:
        try:
            while True:
                attempted_at, requested_catalogs, downloaded, errors = (
                    self._orbital_result_queue.get_nowait()
                )
                self._orbital_update_in_progress = False
                if requested_catalogs != self.catalogs:
                    self.update_orbital_data()
                    continue
                cache = self.store.load_orbital_cache()
                existing = cache.get("satellites", [])
                merged: dict[int, dict[str, str]] = {}
                if isinstance(existing, list):
                    for record in existing:
                        if not isinstance(record, dict):
                            continue
                        try:
                            catalog = int(record["NORAD_CAT_ID"])
                        except (KeyError, TypeError, ValueError):
                            continue
                        merged[catalog] = {
                            str(key): str(value) for key, value in record.items()
                        }
                merged.update(downloaded)
                records = [
                    merged[catalog] for catalog in self.catalogs if catalog in merged
                ]

                if downloaded:
                    try:
                        self.store.save_orbital_cache(records, attempted_at)
                        self._last_orbital_cache_update = attempted_at
                    except OSError as exc:
                        errors.append(f"Não foi possível gravar o cache: {exc}")

                try:
                    satellites = satellites_from_cache(
                        {"satellites": records}, self.catalogs
                    )
                except OrbitalDataError:
                    satellites = []
                missing = len(self.catalogs) - len(satellites)
                if missing:
                    errors.append(f"{missing} catálogo(s) sem dados disponíveis.")

                if satellites:
                    self.satellites = satellites
                    self._live_propagators.clear()
                    sources = {
                        record.get("_DATA_SOURCE", "DADOS ORBITAIS")
                        for record in downloaded.values()
                    }
                    source_name = (
                        next(iter(sources))
                        if len(sources) == 1
                        else "CELESTRAK/SATNOGS"
                    )
                    if errors:
                        source = (
                            f"{source_name} PARCIAL"
                            if downloaded
                            else f"{self._t('local_cache')} • OFFLINE"
                        )
                        self._orbital_status = (
                            f"{source} {attempted_at.astimezone():%d/%m %H:%M}"
                        )
                    else:
                        self._orbital_status = (
                            f"{source_name} {attempted_at.astimezone():%d/%m %H:%M}"
                        )
                    self._refresh_labels()
                    self.calculate()
                else:
                    detail = errors[0] if errors else "Nenhuma fonte retornou dados."
                    self._orbital_status = self._t("sources_unavailable")
                    self._refresh_labels()
                    self.timeline.show_message(
                        self._t("orbital_unavailable"),
                        self._t("no_valid_cache", detail=detail),
                    )
        except queue.Empty:
            pass
        self.root.after(100, self._poll_orbital_results)

    def _apply_language(self) -> None:
        self.setup_button.configure(text=self._t("setup"))
        self.update_button.configure(text=self._t("update"))
        self.window_caption.configure(text=self._t("window"))
        self._refresh_sound_button()
        self.timeline.set_language(self.language)
        self._refresh_labels()

    def _window_changed(self, _event: tk.Event | None = None) -> None:
        try:
            selected = int(self.window_variable.get().split()[0])
        except (ValueError, IndexError):
            self.window_variable.set(f"{self.timeline_hours} h")
            return
        if selected not in WINDOW_OPTIONS:
            self.window_variable.set(f"{self.timeline_hours} h")
            return
        self.timeline_hours = selected
        self.store.save_timeline_hours(selected)
        self._refresh_window_label()
        if self.satellites:
            self.calculate()

    def calculate(self, show_loading: bool = True) -> None:
        if not self.satellites:
            return
        self._calculation_id += 1
        calculation_id = self._calculation_id
        self._calculation_in_progress = True
        calculation_center = datetime.now().astimezone()
        view_start, view_end = self._window_bounds(calculation_center)
        coverage_start = (view_start - CALCULATION_MARGIN).astimezone(UTC)
        coverage_end = max(
            (view_end + CALCULATION_MARGIN).astimezone(UTC),
            (calculation_center + NEXT_PASS_LOOKAHEAD).astimezone(UTC),
        )
        station = self.station
        satellites = list(self.satellites)

        if show_loading:
            self._display_ready = False
            self._pass_results = {}
            self._visible_pass_total = 0
            self._calculation_error_count = 0
            self._close_pass_popup()
            self.timeline.show_message(
                "Calculando passagens…", "A propagação SGP4 está em andamento."
            )

        def worker() -> tuple[dict[int, list[PassWindow]], list[str]]:
            results: dict[int, list[PassWindow]] = {}
            errors: list[str] = []
            max_workers = min(8, max(1, len(satellites)))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(
                        find_passes,
                        satellite,
                        station,
                        coverage_start,
                        coverage_end,
                    ): satellite
                    for satellite in satellites
                }
                for future in as_completed(futures):
                    satellite = futures[future]
                    try:
                        results[satellite.catalog_number] = future.result()
                    except Exception as exc:
                        errors.append(f"{satellite.name}: {exc}")
            return results, errors

        def run_worker() -> None:
            results, errors = worker()
            self._result_queue.put(
                (
                    calculation_id,
                    satellites,
                    calculation_center,
                    results,
                    errors,
                )
            )

        threading.Thread(target=run_worker, daemon=True).start()

    @staticmethod
    def _visible_pass_count(
        results: dict[int, list[PassWindow]],
        start_local: datetime,
        end_local: datetime,
    ) -> int:
        start_utc = start_local.astimezone(UTC)
        end_utc = end_local.astimezone(UTC)
        return sum(
            pass_window.los_utc > start_utc and pass_window.aos_utc < end_utc
            for passes in results.values()
            for pass_window in passes
        )

    def _poll_calculation_results(self) -> None:
        try:
            while True:
                (
                    calculation_id,
                    satellites,
                    calculation_center,
                    results,
                    errors,
                ) = self._result_queue.get_nowait()
                if calculation_id != self._calculation_id:
                    continue
                self._calculation_in_progress = False
                self._last_calculation_center = calculation_center
                self._pass_results = results
                self._display_ready = True

                now = datetime.now().astimezone()
                start_local, end_local = self._window_bounds(now)
                self.timeline.set_data(satellites, results, start_local, end_local)
                self.timeline.update_now_marker(now)
                total = self._visible_pass_count(results, start_local, end_local)
                self._visible_pass_total = total
                self._calculation_error_count = len(errors)
                self._refresh_labels()
        except queue.Empty:
            pass
        self.root.after(100, self._poll_calculation_results)

    def show_pass_details(
        self, pass_window: PassWindow | None, anchor: PassAnchor | None
    ) -> None:
        self._close_pass_popup()
        if pass_window is None:
            return
        self._selected_pass = pass_window

        local_timezone = datetime.now().astimezone().tzinfo
        aos = pass_window.aos_utc.astimezone(local_timezone)
        los = pass_window.los_utc.astimezone(local_timezone)
        maximum = pass_window.max_utc.astimezone(local_timezone)
        popup = tk.Frame(self.root, bg="#38586a")
        self._pass_popup = popup

        card = tk.Frame(
            popup,
            bg="#0d1822",
            highlightbackground="#38586a",
            highlightthickness=1,
            padx=14,
            pady=11,
        )
        card.pack(fill="both", expand=True)
        tk.Label(
            card,
            text=pass_window.satellite.name,
            anchor="w",
            bg="#0d1822",
            fg="#ffffff",
            font=("Segoe UI Semibold", 12),
        ).grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(
            card,
            text=f"NORAD {pass_window.satellite.catalog_number}",
            anchor="w",
            bg="#0d1822",
            fg="#78909c",
            font=("Segoe UI", 8),
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 9))

        rows = (
            (
                self._t("countdown"),
                pass_countdown_text(
                    pass_window, datetime.now(UTC), self.language
                ),
            ),
            (
                "AOS",
                f"{aos:%H:%M:%S}   AZ {pass_window.aos_azimuth_deg:.0f}°",
            ),
            (
                self._t("maximum"),
                f"{maximum:%H:%M:%S}   EL {pass_window.max_elevation_deg:.1f}°   "
                f"AZ {pass_window.max_azimuth_deg:.0f}°",
            ),
            (
                "LOS",
                f"{los:%H:%M:%S}   AZ {pass_window.los_azimuth_deg:.0f}°",
            ),
            (
                "DIST",
                self._t("range_at_max", value=pass_window.min_range_km),
            ),
        )
        for row, (label, value) in enumerate(rows, start=2):
            tk.Label(
                card,
                text=label,
                anchor="w",
                bg="#0d1822",
                fg="#78909c",
                font=("Segoe UI Semibold", 8),
            ).grid(row=row, column=0, sticky="nw", padx=(0, 13), pady=2)
            value_label = tk.Label(
                card,
                text=value,
                anchor="w",
                bg="#0d1822",
                fg="#dce8ef",
                font=("Consolas", 9, "bold"),
            )
            value_label.grid(row=row, column=1, sticky="w", pady=2)
            if row == 2:
                value_label.configure(fg="#7be3aa")
                self._pass_countdown_label = value_label

        popup.update_idletasks()
        width = popup.winfo_reqwidth()
        height = popup.winfo_reqheight()
        local_anchor = None
        if anchor is not None:
            root_x = self.root.winfo_rootx()
            root_y = self.root.winfo_rooty()
            local_anchor = (
                anchor[0] - root_x,
                anchor[1] - root_y,
                anchor[2] - root_x,
                anchor[3] - root_y,
            )
        x, y = popup_position(
            local_anchor,
            (width, height),
            (self.root.winfo_width(), self.root.winfo_height()),
        )
        popup.place(x=x, y=y, width=width, height=height)
        popup.lift()

    def _close_pass_popup(self) -> None:
        if self._pass_popup is not None:
            try:
                self._pass_popup.destroy()
            except tk.TclError:
                pass
            self._pass_popup = None
        self._selected_pass = None
        self._pass_countdown_label = None

    def _global_click(self, event: tk.Event) -> None:
        if self._pass_popup is None:
            return
        if event.widget is self.timeline.body:
            try:
                if self.timeline.pass_at(event.x, event.y) is not None:
                    return
            except tk.TclError:
                pass
        self._close_pass_popup()

    def _update_live_visibility(self, now: datetime) -> dict[int, str]:
        if not self._display_ready:
            return {}

        now_utc = now.astimezone(UTC)
        details: dict[int, str] = {}
        for satellite in self.satellites:
            active_pass = next(
                (
                    pass_window
                    for pass_window in self._pass_results.get(
                        satellite.catalog_number, []
                    )
                    if pass_window.aos_utc <= now_utc < pass_window.los_utc
                ),
                None,
            )
            if active_pass is None:
                continue

            try:
                propagator = self._live_propagators.get(satellite.catalog_number)
                if propagator is None:
                    propagator = Propagator(satellite, self.station)
                    self._live_propagators[satellite.catalog_number] = propagator
                observation = propagator.observe(now_utc)
            except Exception:
                continue

            countdown = format_countdown(active_pass.los_utc - now_utc)
            details[satellite.catalog_number] = (
                f"EL {observation.elevation_deg:.1f}°  "
                f"AZ {observation.azimuth_deg:.1f}°  LOS −{countdown}"
            )
        return details

    def _update_pass_popup_countdown(self, now: datetime) -> None:
        if self._selected_pass is None or self._pass_countdown_label is None:
            return
        try:
            self._pass_countdown_label.configure(
                text=pass_countdown_text(
                    self._selected_pass, now.astimezone(UTC), self.language
                )
            )
        except tk.TclError:
            self._close_pass_popup()

    def _tick(self) -> None:
        now = datetime.now().astimezone()
        self._refresh_window_label(now)
        self._update_aos_alerts(now)
        if self.satellites and self._display_ready:
            start_local, end_local = self._window_bounds(now)
            self.timeline.set_live_details(self._update_live_visibility(now))
            self.timeline.set_window(start_local, end_local)
            self.timeline.update_now_marker(now)
        else:
            self.timeline.set_live_details({})
        self._update_pass_popup_countdown(now)

        if self.satellites and not self._calculation_in_progress:
            needs_refresh = (
                self._last_calculation_center is None
                or now - self._last_calculation_center >= CALCULATION_REFRESH
            )
            if needs_refresh:
                self.calculate(show_loading=not self._display_ready)

        now_utc = now.astimezone(UTC)
        if (
            self.catalogs
            and not self._orbital_update_in_progress
            and self._last_orbital_update_attempt is not None
            and now_utc - self._last_orbital_update_attempt >= ORBITAL_UPDATE_INTERVAL
        ):
            self.update_orbital_data()

        delay = 1000 - now.microsecond // 1000
        self.root.after(max(delay, 100), self._tick)


def _enable_windows_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass


def run() -> None:
    _enable_windows_dpi_awareness()
    root = tk.Tk()
    try:
        root.iconbitmap(default=str(bundled_asset("assets/mission-control-timeline.ico")))
    except tk.TclError:
        # Source runs on platforms without Windows ICO support remain usable.
        pass
    MissionPassApp(root)
    root.mainloop()
