"""Temporary promo prices for the catalog.

Usage:
  python scripts/build_promo.py "<prices.xlsx>" [--label "Личный заказ · октябрь 2026"] [--dry-run]
  python scripts/build_promo.py --remove

The xlsx needs a header row containing "Comm code" and a price column whose
header contains "Цена". Each Comm code is matched to a catalog product the same
way commissions are (commCode / modelKeys, must be unique). The result is
written, obfuscated like the catalog, to dist/data/promo.bin. Removing that file
(--remove) switches the whole feature off: the frontend simply shows no prices
and hides the "only with prices" filter.

Both modes also bump the service-worker cache version so installed PWAs drop
the previous copy of the file.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import re
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
CATALOG = DIST / "data" / "idx-7f2ae1.bin"
PROMO = DIST / "data" / "promo.bin"
SW = DIST / "sw.js"
KEY = b"seb-navigator-2026-catalog-key"  # same obfuscation (not encryption) as the catalog


def obfuscate(text: str) -> str:
    raw = text.encode("utf-8")
    return base64.b64encode(bytes(b ^ KEY[i % len(KEY)] for i, b in enumerate(raw))).decode("ascii")


def deobfuscate(b64: str) -> str:
    raw = base64.b64decode(b64)
    return bytes(b ^ KEY[i % len(KEY)] for i, b in enumerate(raw)).decode("utf-8")


def norm(value: object) -> str:
    return re.sub(r"[^A-Z0-9А-ЯЁ]", "", str(value or "").upper())


def bump_cache() -> None:
    text = SW.read_text(encoding="utf-8")
    match = re.search(r'const CACHE = "seb-navigator-v(\d+)";', text)
    if not match:
        print("WARNING: CACHE constant not found in sw.js; bump it by hand")
        return
    new = int(match.group(1)) + 1
    SW.write_text(text.replace(match.group(0), f'const CACHE = "seb-navigator-v{new}";'), encoding="utf-8")
    print(f"sw.js cache bumped to v{new}")


def read_rows(path: Path) -> list[tuple[str, float]]:
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    rows: list[tuple[str, float]] = []
    for sheet in workbook.worksheets:
        grid = list(sheet.iter_rows(values_only=True))
        header = next(
            (i for i, row in enumerate(grid[:30]) if any(str(v or "").strip().lower() == "comm code" for v in row)),
            None,
        )
        if header is None:
            continue
        heads = [str(v or "").strip().lower() for v in grid[header]]
        code_col = heads.index("comm code")
        price_col = next((i for i, h in enumerate(heads) if "цена" in h), None)
        if price_col is None:
            continue
        for row in grid[header + 1:]:
            if code_col >= len(row) or price_col >= len(row):
                continue
            code = str(row[code_col] or "").strip()
            price = row[price_col]
            if not code or isinstance(price, bool):
                continue
            try:
                value = float(str(price).replace(" ", "").replace(",", "."))
            except ValueError:
                continue
            if value > 0:
                rows.append((code, value))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("xlsx", nargs="?", type=Path)
    parser.add_argument("--label", help="text shown next to the prices (default: from the file name)")
    parser.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    parser.add_argument("--remove", action="store_true", help="delete the promo file (feature off)")
    args = parser.parse_args()

    if args.remove:
        if PROMO.exists():
            PROMO.unlink()
            print(f"removed {PROMO.relative_to(ROOT)}")
            bump_cache()
        else:
            print("promo file is not present; nothing to remove")
        return 0
    if not args.xlsx:
        parser.error("give the xlsx path or use --remove")

    catalog = json.loads(deobfuscate(CATALOG.read_text(encoding="ascii")))
    keymap: dict[str, list[dict]] = {}
    for product in catalog:
        keys = {norm(product.get("commCode"))} | {norm(k) for k in product.get("modelKeys", [])}
        keys.discard("")
        for key in keys:
            keymap.setdefault(key, []).append(product)

    # fallback for titles like "FV 6832E0": normalized title contains the whole Comm code
    title_text = [(p, norm(p.get("title")) + " " + norm(p.get("originalTitle"))) for p in catalog]

    def by_title(code: str) -> list[dict]:
        key = norm(code)
        if len(key) < 6:
            return []
        return [p for p, text in title_text if key in text]

    rows = read_rows(args.xlsx)
    prices: dict[str, int] = {}
    matched, unmatched, ambiguous, conflicts = [], [], [], []
    seen: dict[str, float] = {}
    for code, price in rows:
        if code in seen:
            if seen[code] != price:
                conflicts.append((code, seen[code], price))
            continue
        seen[code] = price
        found = keymap.get(norm(code), [])
        if not found:
            found = by_title(code)
        if len(found) > 1:
            exact = [p for p in found if norm(p.get("commCode")) == norm(code)]
            found = exact if len(exact) == 1 else found
        if len(found) == 1:
            prices[found[0]["article"]] = int(round(price))
            matched.append((code, found[0]["article"], found[0]["title"]))
        elif not found:
            unmatched.append(code)
        else:
            ambiguous.append((code, [p["article"] for p in found]))

    print(f"rows with a price: {len(rows)}; unique Comm codes: {len(seen)}")
    print(f"matched to catalog: {len(matched)}; not in catalog: {len(unmatched)}; ambiguous: {len(ambiguous)}; price conflicts: {len(conflicts)}")
    if unmatched:
        print("not in catalog:", ", ".join(unmatched))
    for code, arts in ambiguous:
        print(f"ambiguous {code}: {arts}")
    for code, a, b in conflicts:
        print(f"conflict {code}: kept {a}, ignored {b}")

    if args.dry_run:
        print("dry run: nothing written")
        return 0
    if not prices:
        print("no prices matched; refusing to write an empty file")
        return 1

    label = args.label or re.sub(r"[_]+", " ", re.sub(r"_?для_SC_sent$|_sent$", "", args.xlsx.stem)).strip()
    payload = {
        "version": 1,
        "label": label,
        "source": args.xlsx.name,
        "updatedAt": dt.datetime.now().isoformat(timespec="seconds"),
        "prices": prices,
    }
    PROMO.write_text(obfuscate(json.dumps(payload, ensure_ascii=False, separators=(",", ":"))), encoding="ascii")
    print(f"wrote {PROMO.relative_to(ROOT)}: {len(prices)} prices, label: {label!r}")
    bump_cache()
    return 0


if __name__ == "__main__":
    sys.exit(main())
