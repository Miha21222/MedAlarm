from __future__ import annotations

import csv
import io
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypeVar

import httpx
from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CatalogMedicine, CatalogMetadata


CATALOG_KEY = "moh_state_register"
DATASET_PAGE = "https://data.gov.ua/dataset/reestr_likarskyh_zasobiv_moz"
DATASET_API = "https://data.gov.ua/api/3/action/package_show?id=reestr_likarskyh_zasobiv_moz"
CATALOG_LICENSE = "CC BY"
_USER_AGENT = "MedAlarm/1.0 hobby medicine-reminder catalogue importer"


@dataclass(slots=True)
class CatalogResource:
    url: str
    last_modified: str | None


def normalize_catalog_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = value.translate(str.maketrans({"і": "и", "ї": "и", "є": "е", "ґ": "г", "ё": "е"}))
    return " ".join(re.sub(r"[^0-9a-zа-я]+", " ", value).split())


def _clean(value: str | None) -> str | None:
    cleaned = " ".join((value or "").split())
    return cleaned or None


def _join_unique(values: list[str | None], separator: str = "; ") -> str | None:
    result: list[str] = []
    for value in values:
        cleaned = _clean(value)
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return separator.join(result) or None


_CatalogItem = TypeVar("_CatalogItem")


def _catalog_value(item: object, field: str) -> str:
    value = item.get(field) if isinstance(item, Mapping) else getattr(item, field, None)
    return str(value or "")


def catalog_duplicate_key(item: object) -> tuple[str, ...]:
    registration = normalize_catalog_text(_catalog_value(item, "registration_number"))
    name = normalize_catalog_text(_catalog_value(item, "trade_name"))
    inn = normalize_catalog_text(_catalog_value(item, "inn"))
    form = normalize_catalog_text(_catalog_value(item, "form"))
    if registration:
        return "registration", registration, name, inn, form
    return (
        "display",
        name,
        inn,
        form,
        normalize_catalog_text(_catalog_value(item, "active_ingredients")),
        normalize_catalog_text(_catalog_value(item, "manufacturer")),
    )


def _catalog_record_score(item: object) -> tuple[int, int, int]:
    termination = normalize_catalog_text(_catalog_value(item, "early_termination"))
    not_terminated = 1 if termination in {"ни", "no", "not terminated", "false", "0"} else 0
    unrestricted = 1 if "необмеж" in normalize_catalog_text(_catalog_value(item, "valid_until")) else 0
    complete_fields = sum(
        bool(_catalog_value(item, field))
        for field in (
            "inn", "form", "dispensing_conditions", "active_ingredients", "pharmacotherapeutic_group",
            "atc_codes", "applicant", "manufacturer", "registration_number", "valid_from", "valid_until",
            "instruction_url",
        )
    )
    return not_terminated, unrestricted, complete_fields


def deduplicate_catalog_items(items: list[_CatalogItem]) -> list[_CatalogItem]:
    unique: dict[tuple[str, ...], _CatalogItem] = {}
    for item in items:
        key = catalog_duplicate_key(item)
        current = unique.get(key)
        if current is None or _catalog_record_score(item) > _catalog_record_score(current):
            unique[key] = item
    return list(unique.values())


def parse_registry_csv(content: bytes, *, minimum_records: int = 1000) -> list[dict[str, object]]:
    text = content.decode("cp1251")
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    required = {"ID", "Торгівельне найменування", "Номер Реєстраційного посвідчення"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError("MOH registry CSV has an unexpected schema")

    records: list[dict[str, object]] = []
    for row in reader:
        source_id = _clean(row.get("ID"))
        trade_name = _clean(row.get("Торгівельне найменування"))
        if not source_id or not trade_name:
            continue
        atc_codes = _join_unique([row.get("Код АТС 1"), row.get("Код АТС 2"), row.get("Код АТС 3")], ", ")
        manufacturer = _join_unique(
            [row.get(f"Виробник {number}: назва українською") for number in range(1, 6)]
        )
        record: dict[str, object] = {
            "source_id": source_id,
            "trade_name": trade_name,
            "inn": _clean(row.get("Міжнародне непатентоване найменування")),
            "form": _clean(row.get("Форма випуску")),
            "dispensing_conditions": _clean(row.get("Умови відпуску")),
            "active_ingredients": _clean(row.get("Склад (діючі)")),
            "pharmacotherapeutic_group": _clean(row.get("Фармакотерапевтична група")),
            "atc_codes": atc_codes,
            "applicant": _clean(row.get("Заявник: назва українською")),
            "manufacturer": manufacturer,
            "registration_number": _clean(row.get("Номер Реєстраційного посвідчення")),
            "valid_from": _clean(row.get("Дата початку дії")),
            "valid_until": _clean(row.get("Дата закінчення")),
            "early_termination": _clean(row.get("Дострокове припинення")),
            "instruction_url": _clean(row.get("URL інструкції")),
        }
        record["search_text"] = normalize_catalog_text(
            " ".join(
                str(record.get(field) or "")
                for field in ("trade_name", "inn", "active_ingredients", "manufacturer", "registration_number", "atc_codes")
            )
        )
        records.append(record)
    records = deduplicate_catalog_items(records)
    if len(records) < minimum_records:
        raise ValueError("MOH registry CSV contains too few valid records")
    return records


class MedicineCatalogService:
    @staticmethod
    async def latest_resource(client: httpx.AsyncClient) -> CatalogResource:
        response = await client.get(DATASET_API)
        response.raise_for_status()
        payload = response.json()
        resources = payload.get("result", {}).get("resources", [])
        csv_resources = [
            item
            for item in resources
            if str(item.get("format", "")).upper() == "CSV"
            and str(item.get("url", "")).startswith("https://data.gov.ua/")
        ]
        if not csv_resources:
            raise LookupError("The MOH open-data dataset has no hosted CSV resource")
        latest = max(csv_resources, key=lambda item: item.get("last_modified") or item.get("created") or "")
        return CatalogResource(
            url=str(latest["url"]),
            last_modified=latest.get("last_modified") or latest.get("created"),
        )

    @staticmethod
    async def cleanup_duplicates(session: AsyncSession) -> int:
        stored = list((await session.scalars(select(CatalogMedicine))).all())
        unique = deduplicate_catalog_items(stored)
        keep_ids = {item.source_id for item in unique}
        duplicate_ids = [item.source_id for item in stored if item.source_id not in keep_ids]
        for offset in range(0, len(duplicate_ids), 1000):
            await session.execute(
                delete(CatalogMedicine).where(CatalogMedicine.source_id.in_(duplicate_ids[offset : offset + 1000]))
            )
        metadata = await session.get(CatalogMetadata, CATALOG_KEY)
        if metadata is not None:
            metadata.record_count = len(unique)
        await session.flush()
        return len(unique)

    @staticmethod
    async def refresh(session: AsyncSession, *, force: bool = False) -> int:
        async with httpx.AsyncClient(
            headers={"User-Agent": _USER_AGENT, "Accept": "application/json,text/csv,*/*"},
            follow_redirects=True,
            timeout=httpx.Timeout(120.0),
        ) as client:
            resource = await MedicineCatalogService.latest_resource(client)
            metadata = await session.get(CatalogMetadata, CATALOG_KEY)
            count = await session.scalar(select(func.count()).select_from(CatalogMedicine)) or 0
            if not force and metadata and count and metadata.source_last_modified == resource.last_modified:
                return await MedicineCatalogService.cleanup_duplicates(session)
            response = await client.get(resource.url)
            response.raise_for_status()

        records = parse_registry_csv(response.content)
        await session.execute(delete(CatalogMedicine))
        for offset in range(0, len(records), 1000):
            await session.execute(insert(CatalogMedicine), records[offset : offset + 1000])
        if metadata is None:
            metadata = CatalogMetadata(key=CATALOG_KEY, source_url=resource.url)
            session.add(metadata)
        metadata.source_url = resource.url
        metadata.source_last_modified = resource.last_modified
        metadata.imported_at = datetime.now(UTC)
        metadata.record_count = len(records)
        await session.flush()
        return len(records)

    @staticmethod
    async def search(session: AsyncSession, query: str, limit: int = 20) -> list[CatalogMedicine]:
        normalized = normalize_catalog_text(query)
        tokens = [token for token in normalized.split() if len(token) >= 2]
        if not tokens:
            return []
        statement = select(CatalogMedicine)
        for token in tokens:
            statement = statement.where(CatalogMedicine.search_text.contains(token))
        candidates = deduplicate_catalog_items(list((await session.scalars(statement.limit(300))).all()))

        def rank(item: CatalogMedicine) -> tuple[int, int, str]:
            name = normalize_catalog_text(item.trade_name)
            inn = normalize_catalog_text(item.inn or "")
            exact = 0 if name == normalized else 1
            prefix = 0 if name.startswith(normalized) else 1 if inn.startswith(normalized) else 2
            return exact, prefix, name

        return sorted(candidates, key=rank)[:limit]

    @staticmethod
    async def get(session: AsyncSession, source_id: str) -> CatalogMedicine | None:
        return await session.get(CatalogMedicine, source_id)

    @staticmethod
    async def status(session: AsyncSession) -> dict[str, object]:
        metadata = await session.get(CatalogMetadata, CATALOG_KEY)
        count = await session.scalar(select(func.count()).select_from(CatalogMedicine)) or 0
        return {
            "ready": count > 0,
            "record_count": count,
            "source_updated_at": metadata.source_last_modified if metadata else None,
            "imported_at": metadata.imported_at if metadata else None,
            "source_url": DATASET_PAGE,
            "license": CATALOG_LICENSE,
        }
