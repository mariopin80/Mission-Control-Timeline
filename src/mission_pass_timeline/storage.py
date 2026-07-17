from __future__ import annotations

import json
import os
from pathlib import Path

from .models import Station


def application_data_dir() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    path = root / "MissionPassTimeline"
    path.mkdir(parents=True, exist_ok=True)
    return path


class SettingsStore:
    VALID_TIMELINE_HOURS = (3, 6, 8, 12, 24)
    DEFAULT_TIMELINE_HOURS = 6

    def __init__(self, directory: Path | None = None):
        self.directory = directory or application_data_dir()
        self.config_path = self.directory / "config.json"
        self.tle_path = self.directory / "satellites.tle"

    def _load_document(self) -> dict[str, object]:
        if not self.config_path.exists():
            return {}
        try:
            values = json.loads(self.config_path.read_text(encoding="utf-8"))
            return values if isinstance(values, dict) else {}
        except (OSError, TypeError, json.JSONDecodeError):
            return {}

    def _save_document(self, document: dict[str, object]) -> None:
        document["schema_version"] = 2
        temporary = self.config_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(self.config_path)

    def load_station(self) -> Station:
        try:
            document = self._load_document()
            station_values = document.get("station", {})
            if not isinstance(station_values, dict):
                return Station()
            return Station.from_dict(station_values)
        except (ValueError, TypeError):
            return Station()

    def save_station(self, station: Station) -> None:
        station.validate()
        document = self._load_document()
        document["station"] = station.to_dict()
        self._save_document(document)

    def load_timeline_hours(self) -> int:
        document = self._load_document()
        try:
            hours = int(document.get("timeline_hours", self.DEFAULT_TIMELINE_HOURS))
        except (TypeError, ValueError):
            return self.DEFAULT_TIMELINE_HOURS
        if hours not in self.VALID_TIMELINE_HOURS:
            return self.DEFAULT_TIMELINE_HOURS
        return hours

    def save_timeline_hours(self, hours: int) -> None:
        if hours not in self.VALID_TIMELINE_HOURS:
            raise ValueError(f"Janela de tempo inválida: {hours} h")
        document = self._load_document()
        document["timeline_hours"] = hours
        self._save_document(document)

    def load_tle_text(self) -> str | None:
        try:
            return self.tle_path.read_text(encoding="utf-8-sig")
        except FileNotFoundError:
            return None

    def save_tle_text(self, text: str) -> None:
        temporary = self.tle_path.with_suffix(".tmp")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(self.tle_path)
