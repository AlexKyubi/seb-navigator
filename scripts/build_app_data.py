from __future__ import annotations

import json
import re
from pathlib import Path

import openpyxl


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "Data"
DIST_DATA = ROOT / "dist" / "data"
CATALOG_PATH = DATA_DIR / "справочникSEB.xlsx"


def normalize(value: object) -> str:
    return re.sub(r"[^A-Z0-9А-ЯЁ]", "", str(value or "").upper())


def header_key(value: object) -> str:
    return " ".join(str(value or "").strip().lower().replace("ё", "е").split())


def find_column(headers: dict[str, int], *needles: str) -> int | None:
    for label, column in headers.items():
        if all(needle in label for needle in needles):
            return column
    return None


catalog_wb = openpyxl.load_workbook(CATALOG_PATH, read_only=True, data_only=True)
catalog_ws = catalog_wb.active
catalog_headers = {str(cell.value).strip(): cell.column for cell in catalog_ws[1] if cell.value is not None}

products: list[dict[str, object]] = []
for values in catalog_ws.iter_rows(min_row=2, values_only=True):
    record = {name: values[column - 1] for name, column in catalog_headers.items()}
    article = str(record.get("Артикул") or "").strip()
    if not article:
        continue
    original_title = str(record.get("Наименование") or "").strip()
    sulpak_title = str(record.get("Sulpak.title") or "").strip()
    comm_code = str(record.get("Comm.Code") or "").strip()
    search_text = " ".join(part for part in (original_title, sulpak_title, comm_code) if part)
    model_keys = {normalize(comm_code)} if normalize(comm_code) else set()
    for token in re.findall(r"[A-ZА-ЯЁ0-9][A-ZА-ЯЁ0-9._/-]{4,}", search_text.upper()):
        candidate = normalize(token)
        if len(candidate) >= 5 and any(char.isdigit() for char in candidate):
            model_keys.add(candidate)
    products.append(
        {
            "article": article,
            "category": str(record.get("категория") or "").strip(),
            "subcategory": str(record.get("Подкатегория") or "").strip(),
            "title": sulpak_title or original_title,
            "originalTitle": original_title,
            "brand": str(record.get("Sulpak.brand") or "").strip(),
            "photoUrl": str(record.get("Sulpak.photoUrl") or "").strip(),
            "commCode": comm_code,
            "modelKeys": sorted(model_keys),
        }
    )

DIST_DATA.mkdir(parents=True, exist_ok=True)
(DIST_DATA / "catalog.json").write_text(json.dumps(products, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(json.dumps({"products": len(products)}, ensure_ascii=False))
