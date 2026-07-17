from __future__ import annotations

import ctypes
import math
import queue
import threading
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .dialogs import StationDialog
from .models import PassWindow, Satellite, Station
from .orbit import Propagator, find_passes
from .storage import SettingsStore
from .timeline import PassAnchor, TimelineView
from .tle import TleFormatError, parse_tle

UTC = timezone.utc
WINDOW_OPTIONS = (3, 6, 8, 12, 24)
CALCULATION_REFRESH = timedelta(minutes=5)
CALCULATION_MARGIN = timedelta(minutes=30)
HISTORY_DURATION = timedelta(minutes=30)


def format_countdown(duration: timedelta) -> str:
    """Format a non-negative LOS countdown as MM:SS or HH:MM:SS."""

    total_seconds = max(0, math.ceil(duration.total_seconds()))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def moving_window_bounds(center: datetime, hours: int) -> tuple[datetime, datetime]:
    """Place the current instant 30 minutes after the start of a fixed span."""

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
        self.satellites: list[Satellite] = []
        self._pass_results: dict[int, list[PassWindow]] = {}
        self._live_propagators: dict[int, Propagator] = {}
        self._pass_popup: tk.Frame | None = None
        self._visible_pass_total = 0
        self._calculation_error_count = 0
        self._display_ready = False
        self._calculation_id = 0
        self._calculation_in_progress = False
        self._last_calculation_center: datetime | None = None
        self._result_queue: queue.Queue[
            tuple[
                int,
                list[Satellite],
                datetime,
                dict[int, list[PassWindow]],
                list[str],
            ]
        ] = queue.Queue()

        self._configure_root()
        self._configure_styles()
        self._build_ui()
        self._load_saved_tle()
        self._poll_calculation_results()
        self._tick()

    def _configure_root(self) -> None:
        self.root.title(f"Mission Control — Satellite Pass Timeline {__version__}")
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

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=(18, 13))
        top.pack(fill="x")
        title_group = ttk.Frame(top)
        title_group.pack(side="left")
        ttk.Label(title_group, text="MISSION CONTROL", style="Title.TLabel").pack(
            anchor="w"
        )
        self.station_label = ttk.Label(title_group, style="Hint.TLabel")
        self.station_label.pack(anchor="w", pady=(2, 0))

        controls = ttk.Frame(top)
        controls.pack(side="right")
        ttk.Button(controls, text="Importar TLE", command=self.import_tle).pack(
            side="left", padx=4
        )
        ttk.Button(controls, text="Estação", command=self.open_station).pack(
            side="left", padx=4
        )
        ttk.Label(controls, text="JANELA", style="Hint.TLabel").pack(
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

        self.visibility_bar = tk.Frame(self.root, bg="#10261f", height=42)
        self.visibility_bar.pack_propagate(False)
        tk.Frame(self.visibility_bar, bg="#32d583", width=5).pack(side="left", fill="y")
        tk.Label(
            self.visibility_bar,
            text="EM VISADA",
            bg="#10261f",
            fg="#7be3aa",
            font=("Segoe UI Semibold", 10),
        ).pack(side="left", padx=(13, 17))
        self.visibility_label = tk.Label(
            self.visibility_bar,
            text="",
            anchor="w",
            justify="left",
            bg="#10261f",
            fg="#e8fff2",
            font=("Consolas", 10, "bold"),
        )
        self.visibility_label.pack(side="left", fill="x", expand=True, padx=(0, 16))

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

        self.timeline = TimelineView(self.root, on_pass_selected=self.show_pass_details)
        self.timeline.pack(fill="both", expand=True)
        self.root.bind_all("<Button-1>", self._global_click, add="+")
        self._refresh_labels()

    def _window_bounds(
        self, center: datetime | None = None
    ) -> tuple[datetime, datetime]:
        center = center or datetime.now().astimezone()
        if center.tzinfo is None:
            center = center.astimezone()
        return moving_window_bounds(center, self.timeline_hours)

    def _refresh_window_label(self, now: datetime | None = None) -> None:
        now = now or datetime.now().astimezone()
        start_local, end_local = self._window_bounds(now)
        if start_local.date() == end_local.date():
            interval = f"{start_local:%d/%m/%Y %H:%M} — {end_local:%H:%M}"
        else:
            interval = f"{start_local:%d/%m %H:%M} — {end_local:%d/%m %H:%M}"
        self.window_label.configure(
            text=(
                f"JANELA MÓVEL {self.timeline_hours} H  •  {interval}"
                "  •  30 MIN DE HISTÓRICO"
            )
        )

    def _refresh_labels(self) -> None:
        self.station_label.configure(
            text=(
                f"{self.station.name}  •  {self.station.latitude_deg:+.5f}°, "
                f"{self.station.longitude_deg:+.5f}°  •  máscara "
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
            warning = f"  •  {old_count} TLE ANTIGO(S)" if old_count else ""
            pass_summary = (
                f"  •  {self._visible_pass_total} PASSAGENS"
                if self._display_ready
                else ""
            )
            error_summary = (
                f"  •  {self._calculation_error_count} ERRO(S)"
                if self._calculation_error_count
                else ""
            )
            self.tle_label.configure(
                text=(
                    f"{len(self.satellites)} SATÉLITES{pass_summary}  •  "
                    f"TLE {newest:%d/%m/%Y %H:%M} UTC{warning}{error_summary}"
                ),
                fg=(
                    "#ffb74d"
                    if old_count or self._calculation_error_count
                    else "#78909c"
                ),
            )
        else:
            self.tle_label.configure(text="NENHUM TLE CARREGADO", fg="#78909c")

    def _load_saved_tle(self) -> None:
        text = self.store.load_tle_text()
        if text is None:
            self.timeline.show_message(
                "Importe uma lista de TLE",
                "Use o botão “Importar TLE” e depois confira as coordenadas da estação.",
            )
            return
        try:
            self.satellites = parse_tle(text)
        except TleFormatError:
            self.timeline.show_message(
                "Não foi possível abrir a lista salva",
                "Importe novamente um arquivo TLE válido.",
            )
            return
        self._refresh_labels()
        self.calculate()

    def import_tle(self) -> None:
        filename = filedialog.askopenfilename(
            parent=self.root,
            title="Importar lista de TLE",
            filetypes=[
                ("Arquivos TLE", "*.tle *.txt"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not filename:
            return
        try:
            text = Path(filename).read_text(encoding="utf-8-sig")
            satellites = parse_tle(text)
        except UnicodeDecodeError:
            try:
                text = Path(filename).read_text(encoding="latin-1")
                satellites = parse_tle(text)
            except (OSError, TleFormatError, UnicodeDecodeError) as exc:
                messagebox.showerror("Falha ao importar", str(exc), parent=self.root)
                return
        except (OSError, TleFormatError) as exc:
            messagebox.showerror("Falha ao importar", str(exc), parent=self.root)
            return

        self.satellites = satellites
        self._live_propagators.clear()
        self.store.save_tle_text(text)
        self._refresh_labels()
        self.calculate()

    def open_station(self) -> None:
        StationDialog(self.root, self.station, self._save_station)

    def _save_station(self, station: Station) -> None:
        self.station = station
        self._live_propagators.clear()
        self.store.save_station(station)
        self._refresh_labels()
        if self.satellites:
            self.calculate()

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
        coverage_end = (view_end + CALCULATION_MARGIN).astimezone(UTC)
        station = self.station
        satellites = list(self.satellites)

        if show_loading:
            self._display_ready = False
            self._pass_results = {}
            self._visible_pass_total = 0
            self._calculation_error_count = 0
            self._close_pass_popup()
            self._hide_visibility_bar()
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
                "AOS",
                f"{aos:%H:%M:%S}   AZ {pass_window.aos_azimuth_deg:.0f}°",
            ),
            (
                "MÁX",
                f"{maximum:%H:%M:%S}   EL {pass_window.max_elevation_deg:.1f}°   "
                f"AZ {pass_window.max_azimuth_deg:.0f}°",
            ),
            (
                "LOS",
                f"{los:%H:%M:%S}   AZ {pass_window.los_azimuth_deg:.0f}°",
            ),
            (
                "DIST",
                f"{pass_window.min_range_km:.0f} km no ponto de máxima",
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
            tk.Label(
                card,
                text=value,
                anchor="w",
                bg="#0d1822",
                fg="#dce8ef",
                font=("Consolas", 9, "bold"),
            ).grid(row=row, column=1, sticky="w", pady=2)

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

    def _hide_visibility_bar(self) -> None:
        if self.visibility_bar.winfo_manager():
            self.visibility_bar.pack_forget()

    def _update_live_visibility(self, now: datetime) -> None:
        if not self._display_ready:
            self._hide_visibility_bar()
            return

        now_utc = now.astimezone(UTC)
        details: list[str] = []
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
            details.append(
                f"{satellite.name}   EL {observation.elevation_deg:5.1f}°   "
                f"AZ {observation.azimuth_deg:5.1f}°   LOS −{countdown}"
            )

        if not details:
            self._hide_visibility_bar()
            return

        self.visibility_bar.configure(height=18 + 24 * len(details))
        self.visibility_label.configure(text="\n".join(details))
        if not self.visibility_bar.winfo_manager():
            self.visibility_bar.pack(fill="x", before=self.window_bar)

    def _tick(self) -> None:
        now = datetime.now().astimezone()
        self._refresh_window_label(now)
        if self.satellites and self._display_ready:
            start_local, end_local = self._window_bounds(now)
            self.timeline.set_window(start_local, end_local)
            self.timeline.update_now_marker(now)
            self._update_live_visibility(now)
        else:
            self._hide_visibility_bar()

        if self.satellites and not self._calculation_in_progress:
            needs_refresh = (
                self._last_calculation_center is None
                or now - self._last_calculation_center >= CALCULATION_REFRESH
            )
            if needs_refresh:
                self.calculate(show_loading=not self._display_ready)

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
    MissionPassApp(root)
    root.mainloop()
