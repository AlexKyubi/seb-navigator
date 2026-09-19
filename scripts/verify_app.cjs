const fs = require("fs");
const XLSX = require("../dist/assets/xlsx.full.min.js");

const normalize = (value) => String(value ?? "").toUpperCase().replace(/[^A-Z0-9А-ЯЁ]/g, "");
const headerKey = (value) => String(value ?? "").trim().toLowerCase().replaceAll("ё", "е").replace(/\s+/g, " ");
const findHeaderIndex = (headers, predicates) => headers.findIndex((header) => predicates.every((needle) => header.includes(needle)));
const asRate = (value) => {
  if (typeof value === "number" && Number.isFinite(value)) return value > 1 ? value / 100 : value;
  const parsed = Number(String(value ?? "").replace("%", "").replace(",", ".").trim());
  return Number.isFinite(parsed) ? (parsed > 1 ? parsed / 100 : parsed) : null;
};

const workbook = XLSX.read(fs.readFileSync(process.argv[2]), { type: "buffer" });
const rows = [];
for (const sheetName of workbook.SheetNames) {
  const grid = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName], { header: 1, defval: null, raw: true });
  const headerRow = grid.slice(0, 20).findIndex((row) => row.some((value) => headerKey(value) === "comm.code"));
  if (headerRow < 0) continue;
  const headers = grid[headerRow].map(headerKey);
  const codeIndex = headers.indexOf("comm.code");
  let belowIndex = findHeaderIndex(headers, ["ниже", "план"]);
  if (belowIndex < 0) belowIndex = findHeaderIndex(headers, ["ниже", "100"]);
  let planIndex = findHeaderIndex(headers, ["выше", "план"]);
  if (planIndex < 0) planIndex = findHeaderIndex(headers, ["100%"]);
  if (planIndex < 0) planIndex = findHeaderIndex(headers, ["при выполн"]);
  grid.slice(headerRow + 1).forEach((row) => {
    const commCode = String(row[codeIndex] ?? "").trim();
    const belowPlan = asRate(row[belowIndex]);
    const atPlan = asRate(row[planIndex]);
    if (commCode && belowPlan !== null && atPlan !== null) rows.push({ commCode, belowPlan, atPlan });
  });
}

const products = JSON.parse(fs.readFileSync("dist/data/catalog.json", "utf8"));
const keyMap = new Map();
for (const product of products) {
  const keys = new Set([normalize(product.commCode), ...(product.modelKeys || []).map(normalize)]);
  keys.delete("");
  for (const key of keys) {
    if (!keyMap.has(key)) keyMap.set(key, []);
    keyMap.get(key).push(product.article);
  }
}
const matched = new Set();
let unmatched = 0;
let ambiguous = 0;
for (const row of rows) {
  const articles = keyMap.get(normalize(row.commCode)) || [];
  if (articles.length === 1) matched.add(articles[0]);
  else if (articles.length > 1) ambiguous += 1;
  else unmatched += 1;
}
const result = { parsedRows: rows.length, matchedArticles: matched.size, unmatchedRows: unmatched, ambiguousRows: ambiguous };
console.log(JSON.stringify(result));
// Baseline raised 2026-09-19: 150 Mechta-only products were added to the
// catalog; matchedArticles grew from 172 to 185 because 13 of them have a
// real Tefal/Rowenta model code in their title that legitimately matches a
// Comm.Code row in this reference commissions file (verified by hand —
// e.g. C4250413 -> "Сковорода TEFAL C4250413 24 RENEW"). unmatchedRows
// dropped from 50 to 37 accordingly; parsedRows/ambiguousRows are unchanged.
if (result.parsedRows !== 222 || result.matchedArticles !== 185 || result.ambiguousRows !== 0) process.exitCode = 1;
