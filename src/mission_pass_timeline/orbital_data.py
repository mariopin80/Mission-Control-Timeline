from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sgp4 import omm
from sgp4.api import Satrec
from sgp4.exporter import export_omm

from .models import Satellite

UTC = timezone.utc
CELESTRAK_GP_URL = "https://celestrak.org/NORAD/elements/gp.php"
SATNOGS_TLE_URL = "https://db.satnogs.org/api/tle/"
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


def parse_catalog_entry(text: str) -> list[int]:
    """Parse NORAD numbers entered with commas, semicolons, or whitespace."""

    values = [value for value in re.split(r"[,;\s]+", text.strip()) if value]
    catalogs: list[int] = []
    seen: set[int] = set()
    for position, value in enumerate(values, start=1):
        if not CATALOG_PATTERN.fullmatch(value) or int(value) <= 0:
            raise CatalogListError(
                f"Item {position} (“{value}”): informe somente um número NORAD positivo."
            )
        catalog = int(value)
        if catalog in seen:
            raise CatalogListError(f"O catálogo NORAD {catalog} está repetido.")
        seen.add(catalog)
        catalogs.append(catalog)
    if not catalogs:
        raise CatalogListError("Informe pelo menos um número NORAD.")
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
    fields["_DATA_SOURCE"] = "CELESTRAK"
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


def decode_satnogs_response(payload: bytes, expected_catalog: int) -> dict[str, str]:
    try:
        values = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OrbitalDataError("O SatNOGS retornou uma resposta inválida.") from exc
    if not isinstance(values, list) or not values or not isinstance(values[0], dict):
        raise OrbitalDataError(
            f"Nenhum dado no SatNOGS para o NORAD {expected_catalog}."
        )
    record = values[0]
    try:
        catalog = int(record["norad_cat_id"])
        line1 = str(record["tle1"])
        line2 = str(record["tle2"])
        name = str(record.get("tle0", f"SAT {catalog}")).removeprefix("0 ").strip()
        satrec = Satrec.twoline2rv(line1, line2)
        fields = {
            str(key): str(value) for key, value in export_omm(satrec, name).items()
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise OrbitalDataError(f"Registro SatNOGS inválido: {exc}") from exc
    if catalog != expected_catalog or int(fields["NORAD_CAT_ID"]) != expected_catalog:
        raise OrbitalDataError(f"O SatNOGS retornou {catalog} para {expected_catalog}.")
    fields["_DATA_SOURCE"] = "SATNOGS"
    satellite_from_omm(fields)
    return fields


def download_satnogs_catalog(
    catalog: int,
    *,
    timeout: float = 15.0,
    opener: Callable[..., object] = urlopen,
) -> dict[str, str]:
    url = f"{SATNOGS_TLE_URL}?norad_cat_id={catalog}"
    request = Request(url, headers={"User-Agent": "MissionControlTimeline/0.5"})
    try:
        with opener(request, timeout=timeout) as response:  # type: ignore[attr-defined]
            payload = response.read()
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        raise OrbitalSourceError(f"Falha ao consultar SatNOGS: {exc}") from exc
    return decode_satnogs_response(payload, catalog)


def download_catalogs(
    catalogs: Iterable[int],
    primary: Callable[[int], dict[str, str]] = download_catalog,
    fallback: Callable[[int], dict[str, str]] = download_satnogs_catalog,
) -> tuple[dict[int, dict[str, str]], list[str]]:
    """Use CelesTrak first and switch to SatNOGS after a source failure."""

    downloaded: dict[int, dict[str, str]] = {}
    errors: list[str] = []
    primary_available = True
    for catalog in catalogs:
        try:
            downloader = primary if primary_available else fallback
            downloaded[catalog] = downloader(catalog)
        except OrbitalSourceError as exc:
            if primary_available:
                primary_available = False
                try:
                    downloaded[catalog] = fallback(catalog)
                except OrbitalDataError as fallback_exc:
                    errors.append(f"{exc}; {fallback_exc}")
            else:
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
