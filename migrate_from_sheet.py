"""One-time copy of the old Google Sheet into Supabase. Run while the sheet is still published:

    python3 migrate_from_sheet.py "<published CSV link>" [--dry]

Every photo (Drive or retailer link) is copied into Supabase storage, resized and without metadata,
so nothing depends on the Drive folder any more. A photo that can't be fetched keeps its link.
After it's done, unpublish the sheet: File > Share > Publish to web > Stop publishing.
"""
import csv, hashlib, io, json, re, sys, urllib.request
from datetime import datetime, timedelta, timezone

PLACEHOLDER = re.compile(r"^(Loading\.\.\.|#[A-Z/]+!?)$")  # GOOGLETRANSLATE still resolving / error
STATUSES = {"For Sale", "Free", "Available Soon", "Reserved", "Sold", "Given Away", "Inactive"}


def clean(v):
    v = (v or "").strip()
    return None if not v or PLACEHOLDER.match(v) else v


def iso_date(v):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(v, fmt).date().isoformat()
        except (ValueError, TypeError):
            pass
    return None


def to_row(r, i, base):
    price = re.sub(r"[^\d]", "", r.get("Price", ""))
    return {
        "item": clean(r["Item"]), "item_he": clean(r.get("Item (HE)")),
        "category": clean(r.get("Category")), "category_he": clean(r.get("Category (HE)")),
        "description": clean(r.get("Description")), "description_he": clean(r.get("Description (HE)")),
        "status": r["Status"].strip() if r["Status"].strip() in STATUSES else "Inactive",
        "available_from": iso_date(clean(r.get("Date"))), "price": int(price) if price else None,
        "room": clean(r.get("Room")), "photos": (r.get("Photo URL") or "").split(),
        # keep the sheet order: later rows = newer
        "created_at": (base + timedelta(seconds=i)).isoformat(),
    }


def copy_photo(url):
    import supa
    from import_whatsapp import prepare
    from PIL import Image
    m = re.search(r"drive\.google\.com/.*(?:/d/|[?&]id=)([\w-]+)", url)
    src = f"https://lh3.googleusercontent.com/d/{m[1]}=w1600" if m else url
    path = f"sheet-{hashlib.md5(url.encode()).hexdigest()[:12]}.webp"
    try:
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
        supa.upload(path, prepare(Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read()))), "image/webp")
        return path
    except Exception as e:
        print(f"  kept link ({e}): {url[:80]}")
        return url


def main(url, dry):
    rows = list(csv.DictReader(io.StringIO(urllib.request.urlopen(url).read().decode())))
    rows = [{k.strip(): v for k, v in r.items()} for r in rows if (r.get("Item") or "").strip()]
    base = datetime.now(timezone.utc) - timedelta(days=1)
    out = [to_row(r, i, base) for i, r in enumerate(rows)]
    bad = [r["item"] for r, src in zip(out, rows) if src["Status"].strip() not in STATUSES]
    if bad:
        print(f"Unknown status -> Inactive: {bad}")
    if dry:
        print(json.dumps(out[:3], ensure_ascii=False, indent=1), f"\n... {len(out)} items")
        return
    import supa
    if supa.items():
        sys.exit("The items table isn't empty; not importing twice.")
    for i, r in enumerate(out, 1):
        print(f"Copying photos {i}/{len(out)}", end="\r")
        r["photos"] = [copy_photo(u) for u in r["photos"]]
    supa.insert(out)
    print(f"Imported {len(out)} items.")


if __name__ == "__main__":
    assert iso_date("2026-08-01") == "2026-08-01" and iso_date("1/8/2026") == "2026-08-01" and iso_date("soon") is None
    assert clean("Loading...") is None and clean("#VALUE!") is None and clean(" x ") == "x"
    main(sys.argv[1], "--dry" in sys.argv)
