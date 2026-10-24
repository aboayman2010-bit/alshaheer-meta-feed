import csv, io, json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

API = "https://api.easy-orders.net/api/v1/external-apps/products"
SAVINGS_ID = "61b0fbe5-a5e6-4b5c-8177-bbd009248cc4"
OUT = Path(__file__).parent / "site"

def fetch_json(url, key):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"Api-Key": key, "Accept": "application/json"}, method="GET"), timeout=50) as r:
                return json.load(r)
        except HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError("Easy Orders HTTP " + str(e.code)) from None
        except (URLError, TimeoutError):
            if attempt == 2:
                raise RuntimeError("Connection error") from None
        time.sleep(5 * (attempt + 1))

def unpack(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for k in ("data", "products", "items", "results"):
            v = payload.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                for inner in ("data", "products", "items", "results"):
                    if isinstance(v.get(inner), list):
                        return v[inner]
    raise RuntimeError("Unrecognized API response")

def read_products(key):
    products = {}
    for page in range(1, 101):
        params = urlencode({"join": "categories", "limit": 100, "page": page})
        rows = unpack(fetch_json(API + "?" + params, key))
        before = len(products)
        for p in rows:
            if not isinstance(p, dict) or not p.get("id"):
                raise RuntimeError("Invalid product row")
            products[str(p["id"])] = p
        if rows and len(products) == before:
            raise RuntimeError("Repeated pagination page")
        print("Page", page, "rows", len(rows), "total", len(products), flush=True)
        if len(rows) < 100:
            break
        time.sleep(2.2)
    else:
        raise RuntimeError("Exceeded pagination limit")
    if len(products) < 500:
        raise RuntimeError("Suspiciously few products")
    return products

def membership(p):
    cats = p.get("categories", p.get("Categories"))
    if isinstance(cats, list):
        result = set()
        for c in cats:
            cid = c.get("id") or c.get("category_id") if isinstance(c, dict) else c if isinstance(c, str) else None
            if not cid:
                return None
            result.add(str(cid))
        return result
    if "category_id" in p:
        return {str(p["category_id"])} if p["category_id"] else set()
    return None

def make_feed(products):
    savings, outside, unknown = [], [], []
    for pid, p in products.items():
        cats = membership(p)
        if cats is None:
            unknown.append(pid)
        elif SAVINGS_ID in cats:
            savings.append(pid)
        else:
            outside.append(pid)
    if len(unknown) > max(50, int(len(products) * 0.05)):
        raise RuntimeError("Category data missing broadly; refuse publication")
    if not (1 <= len(savings) <= int(len(products) * 0.6)):
        raise RuntimeError("Unexpected savings count; refuse publication")
    csvfile = io.StringIO(newline="")
    writer = csv.writer(csvfile, lineterminator="\r\n")
    writer.writerow(["id", "custom_label_0"])
    savings_set = set(savings)
    for pid in sorted(products):
        writer.writerow([pid, "وفر اكثر" if pid in savings_set else "other"])
    return csvfile.getvalue().encode("utf-8-sig"), dict(
        total_products=len(products), confirmed_savings=len(savings),
        outside=len(outside), unknown_excluded=len(unknown),
        generated_utc=datetime.now(timezone.utc).isoformat())

def main():
    key = os.getenv("EASYORDERS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Missing EASYORDERS_API_KEY secret")
    data, report = make_feed(read_products(key))
    OUT.mkdir(exist_ok=True)
    (OUT / "supplementary_savings.csv").write_bytes(data)
    (OUT / "status.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    (OUT / "index.html").write_text('<html><meta charset="utf-8"><body><a href="supplementary_savings.csv">Meta Savings CSV</a></body></html>', encoding="utf-8")
    print("SUCCESS", report, flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        key = os.environ.get("EASYORDERS_API_KEY", "")
        msg = str(exc).replace(key, "[REDACTED]") if key else str(exc)
        print("FAILED SAFELY:", msg, file=sys.stderr)
        sys.exit(1)
