from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sgp4 import omm
from sgp4.api import Satrec

from .models import Satellite

UTC = timezone.utc
CELESTRAK_GP_URL = "https://celestrak.org/NORAD/elements/gp.php"
CATALOG_PATTERN = re.compile(r"^[0-9]{1,9}$")


class CatalogListError(ValueError):
    """Raised when the NORAD catalog list is malformed."""


class OrbitalDataError(RuntimeError):
    """Raised when orbital data cannot be downloaded or validated."""


class OrbitalSourceError(OrbitalDataError):
    """Raised when the remote source asks the client to stop querying."""


def catalogs_to_download(
    catalogs: Iterable[int],
    cached_catalogs: set[int],
    cache_updated_utc: datetime | None,
    now_utc: datetime,
    minimum_refresh: timedelta,
) -> list[int]:
    """Avoid duplicate downloads while still fetching uncached catalogs."""

    catalogs = list(catalogs)
    missing = [catalog for catalog in catalogs if catalog not in cached_catalogs]
    if cache_updated_utc is None:
        return catalogs
    if cache_updated_utc.tzinfo is None or now_utc.tzinfo is None:
        raise ValueError("Os instantes de atualização devem possuir fuso horário.")
    fresh = (
        now_utc.astimezone(UTC) - cache_updated_utc.astimezone(UTC) < minimum_refresh
    )
    return missing if fresh else catalogs


def parse_catalog_numbers(text: str) -> list[int]:
    """Parse one unique numeric NORAD catalog identifier per non-empty line."""

    catalogs: list[int] = []
    seen: set[int] = set()
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        value = raw_line.strip()
        if not value or value.startswith(("#", ";")):
            continue
        if not CATALOG_PATTERN.fullmatch(value) or int(value) <= 0:
            raise CatalogListError(
                f"Linha {line_number}: informe somente um número NORAD positivo."
            )
        catalog = int(value)
        if catalog in seen:
            raise CatalogListError(f"O catálogo NORAD {catalog} está repetido.")
        seen.add(catalog)
        catalogs.append(catalog)
    if not catalogs:
        raise CatalogListError("O arquivo não contém nenhum número NORAD.")
    return catalogs


def _epoch_utc(value: object) -> datetime:
    text = str(value).strip().replace("Z", "+00:00")
    try:
        epoch = datetime.fromisoformat(text)
    except ValueError as exc:
        raise OrbitalDataError(f"Época orbital inválida: {value}") from exc
    if epoch.tzinfo is None:
        epoch = epoch.replace(tzinfo=UTC)
    return epoch.astimezone(UTC)


def satellite_from_omm(fields: Mapping[str, object]) -> Satellite:
    normalized = {str(key): str(value) for key, value in fields.items()}
    try:
        catalog = int(normalized["NORAD_CAT_ID"])
        name = normalized.get("OBJECT_NAME", f"SAT {catalog}").strip()
        epoch = _epoch_utc(normalized["EPOCH"])
        normalized["EPOCH"] = epoch.strftime("%Y-%m-%dT%H:%M:%S.%f")
        satrec = Satrec()
        omm.initialize(satrec, normalized)
    except (KeyError, TypeError, ValueError) as exc:
        raise OrbitalDataError(f"Registro OMM inválido: {exc}") from exc
    return Satellite(
        name=name or f"SAT {catalog}",
        line1="",
        line2="",
        catalog_number=catalog,
        epoch_utc=epoch,
        omm_fields=normalized,
    )


def decode_celestrak_response(payload: bytes, expected_catalog: int) -> dict[str, str]:
    try:
        values = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OrbitalDataError("O CelesTrak retornou uma resposta inválida.") from exc
    if (
        not isinstance(values, list)
        or len(values) != 1
        or not isinstance(values[0], dict)
    ):
        raise OrbitalDataError(f"Nenhum dado orbital para o NORAD {expected_catalog}.")
    fields = {str(key): str(value) for key, value in values[0].items()}
    satellite = satellite_from_omm(fields)
    if satellite.catalog_number != expected_catalog:
        raise OrbitalDataError(
            f"O CelesTrak retornou {satellite.catalog_number} para {expected_catalog}."
        )
    return fields


def download_catalog(
    catalog: int,
    *,
    timeout: float = 15.0,
    opener: Callable[..., object] = urlopen,
) -> dict[str, str]:
    url = f"{CELESTRAK_GP_URL}?CATNR={catalog}&FORMAT=JSON"
    request = Request(url, headers={"User-Agent": "MissionControlTimeline/0.5"})
    try:
        with opener(request, timeout=timeout) as response:  # type: ignore[attr-defined]
            payload = response.read()
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        raise OrbitalSourceError(f"Falha ao baixar o NORAD {catalog}: {exc}") from exc
    return decode_celestrak_response(payload, catalog)


def download_catalogs(
    catalogs: Iterable[int],
    downloader: Callable[[int], dict[str, str]] = download_catalog,
) -> tuple[dict[int, dict[str, str]], list[str]]:
    """Download sequentially and stop immediately if the source is unavailable."""

    downloaded: dict[int, dict[str, str]] = {}
    errors: list[str] = []
    for catalog in catalogs:
        try:
            downloaded[catalog] = downloader(catalog)
        except OrbitalSourceError as exc:
            errors.append(str(exc))
            break
        except OrbitalDataError as exc:
            errors.append(str(exc))
    return downloaded, errors


def satellites_from_cache(
    document: Mapping[str, object], catalogs: Iterable[int]
) -> list[Satellite]:
    records = document.get("satellites", [])
    if not isinstance(records, list):
        raise OrbitalDataError("O cache orbital possui formato inválido.")
    by_catalog: dict[int, Satellite] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        try:
            satellite = satellite_from_omm(record)
        except OrbitalDataError:
            continue
        by_catalog[satellite.catalog_number] = satellite
    return [by_catalog[catalog] for catalog in catalogs if catalog in by_catalog]
