from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sgp4.alpha5 import from_alpha5
from sgp4.api import Satrec

from .models import Satellite

UTC = timezone.utc


class TleFormatError(ValueError):
    """Raised when a TLE list cannot be parsed safely."""


def _catalog_number(line: str) -> int:
    try:
        return from_alpha5(line[2:7])
    except (ValueError, IndexError) as exc:
        raise TleFormatError(f"Número de catálogo inválido na linha: {line}") from exc


def _epoch_utc(satrec: Satrec) -> datetime:
    # Satrec exposes the TLE epoch as year + fractional day of year.
    return datetime(
        satrec.epochyr + (1900 if satrec.epochyr >= 57 else 2000), 1, 1, tzinfo=UTC
    ) + timedelta(days=satrec.epochdays - 1.0)


def parse_tle(text: str) -> list[Satellite]:
    """Parse common two-line and named three-line TLE lists.

    Comment lines beginning with ``#``, ``;`` or ``//`` and blank lines are
    ignored. A leading ``0 `` on a name line is removed.
    """

    lines = [
        line.rstrip("\r\n")
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", ";", "//"))
    ]
    satellites: list[Satellite] = []
    seen_catalogs: set[int] = set()
    index = 0

    while index < len(lines):
        current = lines[index].strip()
        if current.startswith("1 "):
            name: str | None = None
            line1 = current
            index += 1
        else:
            name = current[2:].strip() if current.startswith("0 ") else current
            index += 1
            if index >= len(lines) or not lines[index].lstrip().startswith("1 "):
                raise TleFormatError(
                    f"Era esperada a linha 1 do TLE depois de “{name}”."
                )
            line1 = lines[index].strip()
            index += 1

        if index >= len(lines) or not lines[index].lstrip().startswith("2 "):
            raise TleFormatError(
                f"Era esperada a linha 2 do TLE após o catálogo {_catalog_number(line1)}."
            )
        line2 = lines[index].strip()
        index += 1

        catalog1 = _catalog_number(line1)
        catalog2 = _catalog_number(line2)
        if catalog1 != catalog2:
            raise TleFormatError(
                f"As linhas 1 e 2 pertencem a catálogos diferentes: "
                f"{catalog1} e {catalog2}."
            )
        if catalog1 in seen_catalogs:
            raise TleFormatError(
                f"O catálogo {catalog1} aparece mais de uma vez na lista."
            )

        try:
            satrec = Satrec.twoline2rv(line1, line2)
        except Exception as exc:
            raise TleFormatError(
                f"TLE inválido para o catálogo {catalog1}: {exc}"
            ) from exc

        satellites.append(
            Satellite(
                name=(name or f"SAT {catalog1}").strip(),
                line1=line1,
                line2=line2,
                catalog_number=catalog1,
                epoch_utc=_epoch_utc(satrec),
            )
        )
        seen_catalogs.add(catalog1)

    if not satellites:
        raise TleFormatError("O arquivo não contém nenhum TLE reconhecível.")

    return satellites
