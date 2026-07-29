from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from .i18n import DEFAULT_LANGUAGE, LANGUAGES
from .models import Station

REGISTRY_KEY = r"Software\Mario Pin\Mission Control Timeline"
REGISTRY_VALUE = "DataDirectory"


def default_application_data_dir() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "MissionControlTimeline"


def configured_data_dir() -> Path | None:
    if os.name != "nt":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
            value, _kind = winreg.QueryValueEx(key, REGISTRY_VALUE)
        if isinstance(value, str) and value.strip():
            return Path(os.path.expandvars(value.strip())).expanduser()
    except (ImportError, OSError):
        pass
    return None


def set_configured_data_dir(path: Path) -> None:
    if os.name != "nt":
        return
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
        winreg.SetValueEx(key, REGISTRY_VALUE, 0, winreg.REG_SZ, str(path))


def application_data_dir() -> Path:
    default_path = default_application_data_dir()
    root = default_path.parent
    path = configured_data_dir() or default_path
    legacy_path = root / "MissionPassTimeline"
    if not path.exists() and legacy_path.exists():
        try:
            shutil.copytree(legacy_path, path)
        except OSError:
            pass
    path.mkdir(parents=True, exist_ok=True)
    return path


def program_dir() -> Path:
    """Return the folder containing the executable, or the project in source mode."""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


class SettingsStore:
    VALID_TIMELINE_HOURS = (3, 6, 8, 12, 24)
    DEFAULT_TIMELINE_HOURS = 6
    DEFAULT_SOUND_ENABLED = True
    DEFAULT_LANGUAGE = DEFAULT_LANGUAGE

    def __init__(
        self,
        directory: Path | None = None,
        cache_directory: Path | None = None,
        legacy_cache_path: Path | None = None,
    ):
        self.directory = directory or application_data_dir()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.config_path = self.directory / "config.json"
        self.catalog_path = self.directory / "satellites.txt"
        self.cache_path = (cache_directory or self.directory) / "orbital_cache.json"
        if cache_directory is None:
            self._migrate_legacy_cache(
                legacy_cache_path or program_dir() / "orbital_cache.json"
            )

    @staticmethod
    def validate_directory(directory: Path) -> Path:
        directory = directory.expanduser().resolve()
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=".mission-control-write-test-",
            dir=directory,
        ):
            pass
        return directory

    def relocate(self, directory: Path, copy_existing: bool = True) -> "SettingsStore":
        destination = self.validate_directory(directory)
        if destination == self.directory.resolve():
            return self

        if copy_existing:
            for source in (self.config_path, self.catalog_path, self.cache_path):
                if not source.is_file():
                    continue
                target = destination / source.name
                temporary = target.with_suffix(target.suffix + ".tmp")
                shutil.copy2(source, temporary)
                temporary.replace(target)

        set_configured_data_dir(destination)
        return SettingsStore(directory=destination, cache_directory=destination)

    def _migrate_legacy_cache(self, legacy_path: Path) -> None:
        if self.cache_path.exists() or legacy_path == self.cache_path:
            return
        try:
            payload = legacy_path.read_bytes()
            temporary = self.cache_path.with_suffix(".tmp")
            temporary.write_bytes(payload)
            temporary.replace(self.cache_path)
        except (FileNotFoundError, OSError):
            pass

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

    def load_sound_enabled(self) -> bool:
        value = self._load_document().get("sound_enabled", self.DEFAULT_SOUND_ENABLED)
        return value if isinstance(value, bool) else self.DEFAULT_SOUND_ENABLED

    def save_sound_enabled(self, enabled: bool) -> None:
        if not isinstance(enabled, bool):
            raise TypeError("O estado do som deve ser verdadeiro ou falso.")
        document = self._load_document()
        document["sound_enabled"] = enabled
        self._save_document(document)

    def load_language(self) -> str:
        value = self._load_document().get("language", self.DEFAULT_LANGUAGE)
        return value if isinstance(value, str) and value in LANGUAGES else self.DEFAULT_LANGUAGE

    def save_language(self, language: str) -> None:
        if language not in LANGUAGES:
            raise ValueError(f"Unsupported language: {language}")
        document = self._load_document()
        document["language"] = language
        self._save_document(document)

    def load_catalog_text(self) -> str | None:
        try:
            return self.catalog_path.read_text(encoding="utf-8-sig")
        except FileNotFoundError:
            return None

    def save_catalog_text(self, text: str) -> None:
        temporary = self.catalog_path.with_suffix(".tmp")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(self.catalog_path)

    def load_orbital_cache(self) -> dict[str, object]:
        try:
            document = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return {}
        return document if isinstance(document, dict) else {}

    def save_orbital_cache(
        self, records: list[dict[str, str]], updated_at: datetime
    ) -> None:
        document = {
            "schema_version": 1,
            "source": "CelesTrak/SatNOGS OMM cache",
            "updated_at_utc": updated_at.isoformat(),
            "satellites": records,
        }
        temporary = self.cache_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(self.cache_path)
