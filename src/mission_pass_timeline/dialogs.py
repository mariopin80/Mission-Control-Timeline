from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable

from . import __version__
from .i18n import LANGUAGES, translate
from .models import Station
from .orbital_data import CatalogListError, parse_catalog_entry

SetupSaveHandler = Callable[[Station, list[int], str], None]


class SetupDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        station: Station,
        catalogs: list[int],
        language: str,
        on_save: SetupSaveHandler,
    ):
        super().__init__(parent)
        self.geometry("720x590")
        self.minsize(660, 520)
        self.transient(parent)
        self.grab_set()
        self.configure(bg="#111820")
        self._on_save = on_save
        self.language = language if language in LANGUAGES else "en"

        self.station_variables = {
            "name": tk.StringVar(value=station.name),
            "latitude": tk.StringVar(value=f"{station.latitude_deg:.6f}"),
            "longitude": tk.StringVar(value=f"{station.longitude_deg:.6f}"),
            "altitude": tk.StringVar(value=f"{station.altitude_m:.1f}"),
            "mask": tk.StringVar(value=f"{station.min_elevation_deg:.1f}"),
        }
        self.language_variable = tk.StringVar(value=LANGUAGES[self.language])

        content = ttk.Frame(self, padding=18)
        content.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)
        self.notebook = ttk.Notebook(content, style="Setup.TNotebook")
        self.notebook.grid(row=0, column=0, sticky="nsew")

        self.satellites_tab = ttk.Frame(self.notebook, padding=18)
        self.station_tab = ttk.Frame(self.notebook, padding=18)
        self.language_tab = ttk.Frame(self.notebook, padding=18)
        self.about_tab = ttk.Frame(self.notebook, padding=18)
        self._build_satellites_tab(catalogs)
        self._build_station_tab()
        self._build_language_tab()
        self._build_about_tab()

        footer = ttk.Frame(content)
        footer.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        self.cancel_button = ttk.Button(footer, command=self.destroy)
        self.cancel_button.pack(side="right", padx=(8, 0))
        self.save_button = ttk.Button(
            footer, style="Accent.TButton", command=self._save
        )
        self.save_button.pack(side="right")

        self.language_selector.bind("<<ComboboxSelected>>", self._language_changed)
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Control-Return>", lambda _event: self._save())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._apply_language()
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _build_satellites_tab(self, catalogs: list[int]) -> None:
        tab = self.satellites_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)
        self.satellites_title = ttk.Label(tab, style="Title.TLabel")
        self.satellites_title.grid(row=0, column=0, sticky="w")
        self.satellites_instructions = ttk.Label(
            tab, style="Hint.TLabel", wraplength=625, justify="left"
        )
        self.satellites_instructions.grid(
            row=1, column=0, sticky="ew", pady=(5, 14)
        )
        editor_frame = tk.Frame(
            tab, bg="#29495b", highlightbackground="#29495b", highlightthickness=1
        )
        editor_frame.grid(row=2, column=0, sticky="nsew")
        self.editor = tk.Text(
            editor_frame,
            wrap="word",
            undo=True,
            bg="#09141d",
            fg="#e8f1f5",
            insertbackground="#ffffff",
            selectbackground="#29495b",
            selectforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            padx=12,
            pady=11,
            font=("Consolas", 11),
        )
        scrollbar = ttk.Scrollbar(
            editor_frame, orient="vertical", command=self.editor.yview
        )
        self.editor.configure(yscrollcommand=scrollbar.set)
        self.editor.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.editor.insert("1.0", ", ".join(str(value) for value in catalogs))
        self.editor.bind("<<Modified>>", self._editor_modified)
        self.editor.edit_modified(False)
        self.count_label = ttk.Label(tab, style="Hint.TLabel")
        self.count_label.grid(row=3, column=0, sticky="w", pady=(10, 0))

    def _build_station_tab(self) -> None:
        self.station_labels: dict[str, ttk.Label] = {}
        self.station_hints: dict[str, ttk.Label] = {}
        keys = ("name", "latitude", "longitude", "altitude", "mask")
        for row, key in enumerate(keys):
            label = ttk.Label(self.station_tab)
            label.grid(row=row, column=0, sticky="w", pady=8)
            entry = ttk.Entry(
                self.station_tab,
                textvariable=self.station_variables[key],
                width=28,
            )
            entry.grid(row=row, column=1, sticky="ew", padx=(18, 12), pady=8)
            hint = ttk.Label(self.station_tab, style="Hint.TLabel")
            hint.grid(row=row, column=2, sticky="w", pady=8)
            self.station_labels[key] = label
            self.station_hints[key] = hint
        self.station_tab.columnconfigure(1, weight=1)

    def _build_language_tab(self) -> None:
        self.language_title = ttk.Label(
            self.language_tab, style="Title.TLabel"
        )
        self.language_title.pack(anchor="w")
        self.language_selector = ttk.Combobox(
            self.language_tab,
            state="readonly",
            width=24,
            values=tuple(LANGUAGES.values()),
            textvariable=self.language_variable,
            style="Timeline.TCombobox",
        )
        self.language_selector.pack(anchor="w", pady=(20, 10))
        self.language_hint = ttk.Label(
            self.language_tab,
            style="Hint.TLabel",
            wraplength=580,
            justify="left",
        )
        self.language_hint.pack(anchor="w")

    def _build_about_tab(self) -> None:
        logo_path = self._bundle_root() / "assets" / "mission-control-timeline-about.png"
        self.about_logo_image: tk.PhotoImage | None = None
        try:
            self.about_logo_image = tk.PhotoImage(file=str(logo_path))
        except tk.TclError:
            pass
        if self.about_logo_image is not None:
            ttk.Label(
                self.about_tab,
                image=self.about_logo_image,
            ).pack(anchor="w", pady=(0, 14))
        ttk.Label(
            self.about_tab,
            text="MISSION CONTROL TIMELINE",
            style="Title.TLabel",
        ).pack(anchor="w")
        self.about_description = ttk.Label(
            self.about_tab, wraplength=610, justify="left"
        )
        self.about_description.pack(anchor="w", pady=(15, 22))
        self.about_version = ttk.Label(self.about_tab, style="Hint.TLabel")
        self.about_version.pack(anchor="w", pady=3)
        self.about_developer = ttk.Label(self.about_tab, style="Hint.TLabel")
        self.about_developer.pack(anchor="w", pady=3)
        self.about_orbital = ttk.Label(self.about_tab, style="Hint.TLabel")
        self.about_orbital.pack(anchor="w", pady=3)
        self.about_license_summary = ttk.Label(
            self.about_tab,
            style="Hint.TLabel",
            wraplength=610,
            justify="left",
        )
        self.about_license_summary.pack(anchor="w", pady=(14, 10))
        legal_buttons = ttk.Frame(self.about_tab)
        legal_buttons.pack(anchor="w")
        self.license_button = ttk.Button(
            legal_buttons, command=lambda: self._open_legal_document("LICENSE")
        )
        self.license_button.pack(side="left")
        self.terms_button = ttk.Button(
            legal_buttons, command=lambda: self._open_legal_document("TERMS")
        )
        self.terms_button.pack(side="left", padx=8)
        self.privacy_button = ttk.Button(
            legal_buttons, command=lambda: self._open_legal_document("PRIVACY")
        )
        self.privacy_button.pack(side="left")

    @staticmethod
    def _bundle_root() -> Path:
        return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))

    def _open_legal_document(self, document: str) -> None:
        language = self._selected_language()
        path = self._bundle_root() / "licenses" / f"{document}-{language}.txt"
        try:
            contents = path.read_text(encoding="utf-8")
        except OSError:
            messagebox.showerror(
                "Mission Control Timeline",
                translate(language, "legal_file_error"),
                parent=self,
            )
            return

        titles = {
            "LICENSE": "license_button",
            "TERMS": "terms_button",
            "PRIVACY": "privacy_button",
        }
        viewer = tk.Toplevel(self)
        viewer.title(
            f"Mission Control Timeline — {translate(language, titles[document])}"
        )
        viewer.geometry("720x560")
        viewer.minsize(560, 400)
        viewer.transient(self)
        viewer.configure(bg="#111820")
        content = ttk.Frame(viewer, padding=16)
        content.pack(fill="both", expand=True)
        text_frame = tk.Frame(
            content,
            bg="#29495b",
            highlightbackground="#29495b",
            highlightthickness=1,
        )
        text_frame.pack(fill="both", expand=True)
        text = tk.Text(
            text_frame,
            wrap="word",
            bg="#09141d",
            fg="#dce8ef",
            selectbackground="#29495b",
            selectforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            padx=14,
            pady=12,
            font=("Segoe UI", 10),
        )
        scrollbar = ttk.Scrollbar(
            text_frame, orient="vertical", command=text.yview
        )
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        text.insert("1.0", contents)
        text.configure(state="disabled")
        ttk.Button(
            content,
            text=translate(language, "close"),
            command=viewer.destroy,
        ).pack(anchor="e", pady=(12, 0))
        viewer.bind("<Escape>", lambda _event: viewer.destroy())

    def _selected_language(self) -> str:
        selected_name = self.language_variable.get()
        return next(
            (code for code, name in LANGUAGES.items() if name == selected_name),
            "en",
        )

    def _language_changed(self, _event: tk.Event | None = None) -> None:
        self.language = self._selected_language()
        self._apply_language()

    def _apply_language(self) -> None:
        t = lambda key, **values: translate(self.language, key, **values)
        self.title(t("setup_title"))
        tabs = (
            (self.satellites_tab, "tab_satellites"),
            (self.station_tab, "tab_station"),
            (self.language_tab, "tab_language"),
            (self.about_tab, "tab_about"),
        )
        for tab, key in tabs:
            if str(tab) in self.notebook.tabs():
                self.notebook.tab(tab, text=t(key))
            else:
                self.notebook.add(tab, text=t(key))
        self.satellites_title.configure(text=t("tracked_satellites"))
        self.satellites_instructions.configure(text=t("norad_instructions"))
        labels = {
            "name": "station_name",
            "latitude": "latitude",
            "longitude": "longitude",
            "altitude": "altitude",
            "mask": "minimum_elevation",
        }
        hints = {
            "name": "station_name_hint",
            "latitude": "latitude_hint",
            "longitude": "longitude_hint",
            "altitude": "altitude_hint",
            "mask": "minimum_elevation_hint",
        }
        for key in labels:
            self.station_labels[key].configure(text=t(labels[key]))
            self.station_hints[key].configure(text=t(hints[key]))
        self.language_title.configure(text=t("language_title"))
        self.language_hint.configure(text=t("language_hint"))
        self.about_description.configure(text=t("about_description"))
        self.about_version.configure(text=t("about_version", version=__version__))
        self.about_developer.configure(text=t("about_developer"))
        self.about_orbital.configure(text=t("about_orbital"))
        self.about_license_summary.configure(text=t("about_license_summary"))
        self.license_button.configure(text=t("license_button"))
        self.terms_button.configure(text=t("terms_button"))
        self.privacy_button.configure(text=t("privacy_button"))
        self.cancel_button.configure(text=t("cancel"))
        self.save_button.configure(text=t("save"))
        self._refresh_count()

    def _editor_modified(self, _event: tk.Event | None = None) -> None:
        if not self.editor.edit_modified():
            return
        self.editor.edit_modified(False)
        self._refresh_count()

    def _refresh_count(self) -> None:
        try:
            count = len(parse_catalog_entry(self.editor.get("1.0", "end-1c")))
            text = translate(
                self.language, "satellites_in_list", count=count
            )
            color = "#7be3aa"
        except CatalogListError:
            text = translate(self.language, "invalid_list_waiting")
            color = "#78909c"
        self.count_label.configure(text=text, foreground=color)

    @staticmethod
    def _number(value: str) -> float:
        return float(value.strip().replace(",", "."))

    def _save(self) -> None:
        language = self._selected_language()
        try:
            catalogs = parse_catalog_entry(self.editor.get("1.0", "end-1c"))
        except CatalogListError as exc:
            messagebox.showerror(
                translate(language, "invalid_norad"), str(exc), parent=self
            )
            return
        try:
            station = Station(
                name=self.station_variables["name"].get().strip(),
                latitude_deg=self._number(self.station_variables["latitude"].get()),
                longitude_deg=self._number(self.station_variables["longitude"].get()),
                altitude_m=self._number(self.station_variables["altitude"].get()),
                min_elevation_deg=self._number(self.station_variables["mask"].get()),
            )
            station.validate()
        except ValueError as exc:
            messagebox.showerror(
                translate(language, "invalid_station"), str(exc), parent=self
            )
            return
        self._on_save(station, catalogs, language)
        self.destroy()
