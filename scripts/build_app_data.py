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
    sulpak_article = str(record.get("Артикул") or "").strip()
    mechta_article = str(record.get("Mechta.code") or "").strip()
    if not sulpak_article and not mechta_article:
        continue
    # Stable internal key used for sales history, relation map and DOM identity.
    # Sulpak-sourced rows keep their existing bare numeric article (unchanged,
    # so historical sales tied to it keep matching). Mechta-only rows (no
    # Sulpak/SEB code) get an "M"-prefixed key so it can never collide with a
    # numeric Sulpak article.
    article = sulpak_article or f"M{mechta_article}"
    original_title = str(record.get("Наименование") or "").strip()
    sulpak_title = str(record.get("Sulpak.title") or "").strip()
    comm_code = str(record.get("Comm.Code") or "").strip()
    search_text = " ".join(part for part in (original_title, sulpak_title, comm_code) if part)
    # NOTE: modelKeys feeds both catalog search (catalog.js) AND commission
    # matching (buildRelation() in core.js / verify_app.cjs). Do NOT add
    # sulpak_article/mechta_article here: they are short bare numbers and a
    # coincidental equality with an unrelated Comm.Code in a commission sheet
    # would silently attach the wrong commission rate to a product. Search
    # already covers both codes directly via the dedicated sulpakArticle/
    # mechtaArticle fields (see catalog.js `filtered()`), so nothing is lost.
    model_keys = {normalize(comm_code)} if normalize(comm_code) else set()
    for token in re.findall(r"[A-ZА-ЯЁ0-9][A-ZА-ЯЁ0-9._/-]{4,}", search_text.upper()):
        candidate = normalize(token)
        if len(candidate) >= 5 and any(char.isdigit() for char in candidate):
            model_keys.add(candidate)
    products.append(
        {
            "article": article,
            "sulpakArticle": sulpak_article or None,
            "mechtaArticle": mechta_article or None,
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
