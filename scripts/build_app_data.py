from __future__ import annotations

import base64
import json
import re
from pathlib import Path

import openpyxl


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "Data"
DIST_DATA = ROOT / "dist" / "data"
CATALOG_PATH = DATA_DIR / "справочникSEB.xlsx"

# Obfuscation only — NOT encryption. The key ships in the public JS bundle
# (dist/assets/core.js), so anyone reading the client code can decode this.
# The point is to stop a casual/direct look (curl, "open in new tab", a raw
# Network-tab response) from immediately showing a readable product list with
# prices. Real access control still requires a server-side gate; see
# README "Граница защиты". Filename is deliberately non-descriptive so the
# endpoint isn't guessable from the URL alone.
OBFUSCATION_KEY = b"seb-navigator-2026-catalog-key"
CATALOG_OUTPUT_NAME = "idx-7f2ae1.bin"


def obfuscate(text: str) -> str:
    raw = text.encode("utf-8")
    xored = bytes(b ^ OBFUSCATION_KEY[i % len(OBFUSCATION_KEY)] for i, b in enumerate(raw))
    return base64.b64encode(xored).decode("ascii")


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
    # mechta.kz always shows articles zero-padded to 5 digits (e.g. "02171"),
    # but Excel stores the cell as a number and drops the leading zeros.
    # Pad back so it matches the real site/search-by-article expectation.
    if mechta_article.isdigit():
        mechta_article = mechta_article.zfill(5)
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
catalog_json = json.dumps(products, ensure_ascii=False, separators=(",", ":"))
old_plain_path = DIST_DATA / "catalog.json"
if old_plain_path.exists():
    old_plain_path.unlink()  # retired: was served as plain readable JSON
(DIST_DATA / CATALOG_OUTPUT_NAME).write_text(obfuscate(catalog_json), encoding="ascii")
print(json.dumps({"products": len(products), "output": CATALOG_OUTPUT_NAME}, ensure_ascii=False))
