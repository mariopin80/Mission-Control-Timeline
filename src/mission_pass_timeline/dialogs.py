from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from .models import Station
from .orbital_data import CatalogListError, parse_catalog_entry


class CatalogListDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        catalogs: list[int],
        on_save: Callable[[list[int]], None],
    ):
        super().__init__(parent)
        self.title("Lista de satélites — números NORAD")
        self.geometry("650x410")
        self.minsize(520, 340)
        self.transient(parent)
        self.grab_set()
        self.configure(bg="#111820")
        self._on_save = on_save

        content = ttk.Frame(self, padding=22)
        content.pack(fill="both", expand=True)
        ttk.Label(
            content,
            text="SATÉLITES RASTREADOS",
            style="Title.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            content,
            text=(
                "Informe os números de catálogo NORAD separados por vírgulas, "
                "espaços ou linhas. Exemplo: 25544, 33591, 27607"
            ),
            style="Hint.TLabel",
            wraplength=590,
            justify="left",
        ).pack(anchor="w", pady=(5, 14))

        editor_frame = tk.Frame(
            content,
            bg="#29495b",
            highlightbackground="#29495b",
            highlightthickness=1,
        )
        editor_frame.pack(fill="both", expand=True)
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

        footer = ttk.Frame(content)
        footer.pack(fill="x", pady=(13, 0))
        self.count_label = ttk.Label(footer, style="Hint.TLabel")
        self.count_label.pack(side="left")
        buttons = ttk.Frame(footer)
        buttons.pack(side="right")
        ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(
            buttons,
            text="Salvar lista",
            style="Accent.TButton",
            command=self._save,
        ).pack(side="left")

        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Control-Return>", lambda _event: self._save())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self._refresh_count()
        self.editor.focus_set()

    def _editor_modified(self, _event: tk.Event | None = None) -> None:
        if not self.editor.edit_modified():
            return
        self.editor.edit_modified(False)
        self._refresh_count()

    def _refresh_count(self) -> None:
        try:
            count = len(parse_catalog_entry(self.editor.get("1.0", "end-1c")))
            text = f"{count} satélite{'s' if count != 1 else ''} na lista"
            color = "#7be3aa"
        except CatalogListError:
            text = "Lista aguardando dados válidos"
            color = "#78909c"
        self.count_label.configure(text=text, foreground=color)

    def _save(self) -> None:
        try:
            catalogs = parse_catalog_entry(self.editor.get("1.0", "end-1c"))
        except CatalogListError as exc:
            messagebox.showerror("Lista NORAD inválida", str(exc), parent=self)
            return
        self._on_save(catalogs)
        self.destroy()


class StationDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        station: Station,
        on_save: Callable[[Station], None],
    ):
        super().__init__(parent)
        self.title("Configuração da estação")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(bg="#111820")
        self._on_save = on_save

        self.variables = {
            "name": tk.StringVar(value=station.name),
            "latitude": tk.StringVar(value=f"{station.latitude_deg:.6f}"),
            "longitude": tk.StringVar(value=f"{station.longitude_deg:.6f}"),
            "altitude": tk.StringVar(value=f"{station.altitude_m:.1f}"),
            "mask": tk.StringVar(value=f"{station.min_elevation_deg:.1f}"),
        }

        content = ttk.Frame(self, padding=22)
        content.grid(sticky="nsew")
        fields = [
            ("Nome da estação", "name", "Ex.: PU2PTU Ground Station"),
            ("Latitude (°)", "latitude", "Sul é negativo"),
            ("Longitude (°)", "longitude", "Oeste é negativo"),
            ("Altitude (m)", "altitude", "Acima do nível médio do mar"),
            ("Elevação mínima (°)", "mask", "Máscara do horizonte"),
        ]
        first_entry: ttk.Entry | None = None
        for row, (label, key, hint) in enumerate(fields):
            ttk.Label(content, text=label).grid(row=row, column=0, sticky="w", pady=7)
            entry = ttk.Entry(content, textvariable=self.variables[key], width=27)
            entry.grid(row=row, column=1, sticky="ew", padx=(18, 10), pady=7)
            ttk.Label(content, text=hint, style="Hint.TLabel").grid(
                row=row, column=2, sticky="w", pady=7
            )
            if first_entry is None:
                first_entry = entry

        buttons = ttk.Frame(content)
        buttons.grid(row=len(fields), column=0, columnspan=3, sticky="e", pady=(18, 0))
        ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(
            buttons, text="Salvar", style="Accent.TButton", command=self._save
        ).pack(side="left")

        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Return>", lambda _event: self._save())
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        if first_entry is not None:
            first_entry.focus_set()

    @staticmethod
    def _number(value: str) -> float:
        return float(value.strip().replace(",", "."))

    def _save(self) -> None:
        try:
            station = Station(
                name=self.variables["name"].get().strip(),
                latitude_deg=self._number(self.variables["latitude"].get()),
                longitude_deg=self._number(self.variables["longitude"].get()),
                altitude_m=self._number(self.variables["altitude"].get()),
                min_elevation_deg=self._number(self.variables["mask"].get()),
            )
            station.validate()
        except ValueError as exc:
            messagebox.showerror("Dados inválidos", str(exc), parent=self)
            return
        self._on_save(station)
        self.destroy()
