"""Read-only EasyOrders grouped product exporter; magazine excludes hidden/uncertain items."""
import csv
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from export_feed import read_products

OUTPUT = ROOT / "catalog_export_output"
FIELDS = ("id", "name", "price", "sale_price", "image_url", "status", "stock_status",
          "magazine_eligible", "reasons", "category_ids", "category_names")

def valid_price(x):
    try:
        n = Decimal(str(x))
        return n if n.is_finite() and n > 0 else None
    except Exception:
        return None

def picture(p):
    def scan(v):
        if isinstance(v, str):
            return v.strip() if v.strip().startswith("https://") else ""
        if isinstance(v, dict):
            for key in ("url", "src", "image_url", "thumb", "original_url"):
                r = scan(v.get(key))
                if r: return r
        if isinstance(v, list):
            for obj in v:
                r = scan(obj)
                if r: return r
        return ""
    for field in ("thumb", "image_url", "image", "images", "thumbnail", "product_images", "photos"):
        r = scan(p.get(field))
        if r: return r
    return ""

def categorize(p):
    value = p.get("categories", p.get("Categories"))
    complete = isinstance(value, list)
    by_id = {}
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                cid = item.get("id") or item.get("category_id")
                name = item.get("name") or item.get("title") or ""
                slug = item.get("slug") or ""
            elif isinstance(item, str):
                cid, name, slug = item, "", ""
            else:
                complete = False
                continue
            if cid:
                cid = str(cid)
                by_id[cid] = {"id": cid, "name": str(name), "slug": str(slug)}
            else:
                complete = False
    if p.get("category_id"):
        cid = str(p["category_id"])
        by_id.setdefault(cid, {"id": cid, "name": "", "slug": ""})
        complete = True
    return list(by_id.values()), complete

def status(p):
    if any(p.get(k) is True for k in ("hidden", "is_hidden", "deleted", "is_deleted", "archived")):
        return "hidden"
    if any(p.get(k) is False for k in ("active", "is_active", "visible", "is_visible")):
        return "hidden"
    if any(p.get(k) is False for k in ("hidden", "is_hidden")):
        return "visible"
    if any(p.get(k) is True for k in ("active", "is_active", "visible", "is_visible")):
        return "visible"
    return "unknown"

def stock(p):
    if p.get("track_stock") is False:
        return "not_tracked"
    if p.get("track_stock") is not True:
        return "unknown"
    try:
        qty = p.get("quantity", p.get("stock_quantity", p.get("stock")))
        return "sufficient" if Decimal(str(qty)) > 1 else "low"
    except Exception:
        return "unknown"

def evaluate(rows):
    catalog, products = {}, {}
    for p in rows:
        if not isinstance(p, dict) or not p.get("id"):
            raise ValueError("Invalid item without ID")
        pid = str(p["id"])
        if pid in products:
            raise ValueError("Repeated product ID")
        members, complete = categorize(p)
        for c in members:
            prev = catalog.get(c["id"], {})
            catalog[c["id"]] = {"id": c["id"], "name": c["name"] or prev.get("name", ""),
                                "slug": c["slug"] or prev.get("slug", "")}
        state = status(p)
        stock_state = stock(p)
        name = p.get("name") or p.get("title") or ""
        price = valid_price(p.get("sale_price")) or valid_price(p.get("price"))
        url = picture(p)
        reasons = []
        if state != "visible": reasons.append("hidden" if state == "hidden" else "visibility_unknown")
        if stock_state not in ("sufficient", "not_tracked"): reasons.append("stock_low" if stock_state == "low" else "stock_unknown")
        if not isinstance(name, str) or not name.strip(): reasons.append("name_missing")
        if not price: reasons.append("price_invalid")
        if not url: reasons.append("image_missing")
        if not complete or not members: reasons.append("category_unverified")
        products[pid] = {
            "id": pid, "name": name, "price": p.get("price"), "sale_price": p.get("sale_price"),
            "display_price": str(price) if price else "", "image_url": url,
            "status": state, "stock_status": stock_state,
            "magazine_eligible": not bool(reasons), "reasons": reasons,
            "category_ids": [c["id"] for c in members],
        }
    for p in products.values():
        p["category_names"] = [catalog[c]["name"] for c in p["category_ids"]]
    return catalog, products

def save_csv(path, records, keys=FIELDS):
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        for p in records:
            row = dict(p)
            for key in ("category_ids", "category_names", "reasons"):
                if isinstance(row.get(key), list): row[key] = " | ".join(row[key])
            writer.writerow(row)

def export(raw, output=OUTPUT):
    output = Path(output)
    audit_dir, magazine_dir = output / "audit_all", output / "magazine_ready"
    audit_dir.mkdir(parents=True, exist_ok=True)
    magazine_dir.mkdir(parents=True, exist_ok=True)
    catalog, products = evaluate(raw.values() if isinstance(raw, dict) else raw)
    all_rows = sorted(products.values(), key=lambda p: (p["name"].casefold(), p["id"]))
    categories = []
    for cid, c in sorted(catalog.items(), key=lambda v: (v[1]["name"].casefold(), v[0])):
        selected = [p for p in all_rows if cid in p["category_ids"]]
        allowed = [p for p in selected if p["magazine_eligible"]]
        base = re.sub(r"[^a-zA-Z0-9_-]", "-", c["slug"]).strip("-")[:45] or "group"
        stem = base + "-" + cid[:8]
        cinfo = {**c, "file_stem": stem, "total": len(selected),
                 "visible": sum(p["status"] == "visible" for p in selected),
                 "hidden": sum(p["status"] == "hidden" for p in selected),
                 "unknown": sum(p["status"] == "unknown" for p in selected),
                 "magazine_eligible": len(allowed)}
        categories.append(cinfo)
        for directory, selection in ((audit_dir, selected), (magazine_dir, allowed)):
            (directory / (stem + ".json")).write_text(json.dumps(
                {"category": cinfo, "products": selection}, ensure_ascii=False, indent=2), encoding="utf-8")
            save_csv(directory / (stem + ".csv"), selection)
    summary = {"generated_utc": datetime.now(timezone.utc).isoformat(),
               "products": len(all_rows), "categories": len(categories),
               "visible": sum(p["status"] == "visible" for p in all_rows),
               "hidden": sum(p["status"] == "hidden" for p in all_rows),
               "unknown_visibility": sum(p["status"] == "unknown" for p in all_rows),
               "uncategorized": sum("category_unverified" in p["reasons"] for p in all_rows),
               "magazine_eligible": sum(p["magazine_eligible"] for p in all_rows)}
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "categories.json").write_text(json.dumps(categories, ensure_ascii=False, indent=2), encoding="utf-8")
    save_csv(output / "categories.csv", categories,
             ("id", "name", "slug", "total", "visible", "hidden", "unknown", "magazine_eligible", "file_stem"))
    (output / "all_products.json").write_text(json.dumps(all_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    save_csv(output / "all_products.csv", all_rows)
    print("READ_ONLY_EXPORT_DONE", json.dumps(summary, ensure_ascii=False))
    return summary

if __name__ == "__main__":
    key = os.environ.get("EASYORDERS_API_KEY", "").strip()
    if not key: raise RuntimeError("EASYORDERS_API_KEY missing from secrets")
    export(read_products(key))
