import pytest

from app.database.models import CatalogMedicine
from app.services.medicine_catalog_service import (
    MedicineCatalogService,
    deduplicate_catalog_items,
    normalize_catalog_text,
    parse_registry_csv,
)


def test_parse_registry_csv_maps_official_fields():
    headers = [
        "ID",
        "Торгівельне найменування",
        "Міжнародне непатентоване найменування",
        "Форма випуску",
        "Умови відпуску",
        "Склад (діючі)",
        "Фармакотерапевтична група",
        "Код АТС 1",
        "Код АТС 2",
        "Код АТС 3",
        "Заявник: назва українською",
        "Виробник 1: назва українською",
        "Номер Реєстраційного посвідчення",
        "Дата початку дії",
        "Дата закінчення",
        "Дострокове припинення",
        "URL інструкції",
    ]
    values = [
        "record-1",
        "АСПІРИН КАРДІО®",
        "Acetylsalicylic acid",
        "таблетки по 100 мг №28",
        "без рецепта",
        "ацетилсаліцилова кислота",
        "Антитромботичні засоби",
        "B01AC06",
        "",
        "",
        "Заявник",
        "Виробник",
        "UA/7802/01/01",
        "01.01.2025",
        "необмежений",
        "Ні",
        "https://example.test/instruction",
    ]
    csv_text = ";".join(f'"{value}"' for value in headers) + "\n" + ";".join(f'"{value}"' for value in values)

    records = parse_registry_csv(csv_text.encode("cp1251"), minimum_records=1)

    assert records[0]["trade_name"] == "АСПІРИН КАРДІО®"
    assert records[0]["registration_number"] == "UA/7802/01/01"
    assert records[0]["atc_codes"] == "B01AC06"
    assert "аспирин кардио" in records[0]["search_text"]


def test_normalization_matches_russian_and_ukrainian_spelling():
    assert normalize_catalog_text("Аспірин") == normalize_catalog_text("Аспирин")


def test_catalog_deduplication_keeps_the_best_copy_of_same_registered_form():
    base = {
        "source_id": "old",
        "trade_name": "Ліки",
        "inn": "Medicine",
        "form": "таблетки по 100 мг",
        "registration_number": "UA/1/01/01",
        "early_termination": "Так",
        "valid_until": "01.01.2025",
    }
    current = {
        **base,
        "source_id": "current",
        "early_termination": "Ні",
        "valid_until": "необмежений",
        "dispensing_conditions": "без рецепта",
    }
    distinct_strength = {**current, "source_id": "other", "form": "таблетки по 200 мг"}

    deduplicated = deduplicate_catalog_items([base, current, distinct_strength])

    assert [item["source_id"] for item in deduplicated] == ["current", "other"]


@pytest.mark.asyncio
async def test_catalog_search_prioritizes_trade_name(db_session):
    db_session.add_all(
        [
            CatalogMedicine(source_id="1", trade_name="АСПІРИН®", inn="Acetylsalicylic acid", search_text="аспирин acetylsalicylic acid"),
            CatalogMedicine(source_id="2", trade_name="АСПІРИН КАРДІО®", inn="Acetylsalicylic acid", search_text="аспирин кардио acetylsalicylic acid"),
            CatalogMedicine(source_id="3", trade_name="ІНШІ ЛІКИ", inn="Other", search_text="инши лики other"),
            CatalogMedicine(source_id="4", trade_name="АСПІРИН®", inn="Acetylsalicylic acid", search_text="аспирин acetylsalicylic acid"),
        ]
    )
    await db_session.flush()

    results = await MedicineCatalogService.search(db_session, "Аспирин", limit=10)

    assert [item.source_id for item in results] == ["1", "2"]
