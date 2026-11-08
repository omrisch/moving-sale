"""WhatsApp chat export (.zip) -> new items + photos in Supabase, via `claude -p`.

    python3 import_whatsapp.py ~/Downloads/"WhatsApp Chat - Moving Sale.zip"
    python3 import_whatsapp.py export.zip --dry     # preview: photos to a temp folder, nothing saved

Claude reads the chat + the current items, groups photos with their posts, skips
duplicates and items already listed, and suggests status/price changes
(e.g. "sold the wagon"). Shows everything and asks before saving. Re-exporting the whole chat is fine.
Needs .env with SUPABASE_SECRET_KEY (see README).
"""
from PIL import Image, ImageOps
import hashlib, io, json, subprocess, sys, tempfile, zipfile
from pathlib import Path
import supa

COLS = ["Room", "Item", "Category", "Price", "Status", "Description", "Photo"]
STATUSES = ["For Sale", "Free", "Available Soon", "Reserved", "Sold", "Given Away", "Inactive"]

SCHEMA = {
    "type": "object", "required": ["new_items", "updates"],
    "properties": {
        "new_items": {"type": "array", "items": {
            "type": "object", "required": COLS + ["Crop"],
            "properties": {**{c: {"type": "string"} for c in COLS},
                           "Crop": {"type": "array", "items": {"type": "number"}}}}},
        "updates": {"type": "array", "items": {
            "type": "object", "required": ["id", "item", "column", "value"],
            "properties": {"id": {"type": "string"}, "item": {"type": "string"},
                           "column": {"type": "string"}, "value": {"type": "string"}}}},
    },
}

PROMPT = """You turn a WhatsApp chat of moving-sale posts into items for a sale website's database.

CURRENT ITEMS (id, then fields):
{sheet}

WHATSAPP CHAT (photo filenames are <attached: ...>; the files are in {photo_dir}):
{chat}

Rules:
- One new item per sale post; its photo is the <attached> file in the same message.
- Photo-only messages right after a post: if that post sells many things at a per-piece price (e.g. "any clothes 30 shekels"), each photo is its own item - open the photo with Read to name and describe it, price per the post. Otherwise they're extra photos of the same item; ignore them (one photo per item).
- One photo showing several separately-sellable things (e.g. 2 pairs of shoes) -> one item per thing, same Photo, each with Crop = [left, top, right, bottom] as fractions 0-1 of the image framing just that thing (generous margins). Otherwise Crop = [].
- Skip posts already in the current items (same item) and repeated posts within the chat.
- Item: short English name (e.g. "Green Toys wagon", "2T autumn/winter clothes bundle"). No "(NEW)" tags; say "new" in Description instead.
- Price: digits only, the asking price (not what was originally paid). Blank if Free or unclear.
- Status: one of {statuses}. "Free" if given away for free.
- Category: reuse an existing category when one fits, else a short new one (e.g. "Kids clothes", "Toys").
- Room: "Clothes" for any clothing, shoes or accessories (adults' or kids'). Otherwise reuse an existing Room value when obvious, else blank.
- Description: useful details (condition, sizes, contents, brands) as one line. Omit pickup location and price.
- Photo: the attached filename exactly.
- updates: only for messages that clearly change an existing item (sold, reserved, price change); id = its id. Column is Status or Price; Status must be from the list above. Otherwise empty.
"""


def items_text():
    head = ["id", "room", "item", "category", "price", "status"]
    rows = [[str(r[c] or "") for c in head] for r in supa.items()]
    return "\n".join("\t".join(r) for r in [head] + rows)


def prepare(im):
    # Same as the site's admin form: max 1600px WebP, no metadata (GPS etc.)
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((1600, 1600))
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=85)
    return buf.getvalue()


def main(src, dry):
    with tempfile.TemporaryDirectory() as tmp:
        zipfile.ZipFile(src).extractall(tmp)
        chat = next(Path(tmp).rglob("*.txt")).read_text(encoding="utf-8")
        # WhatsApp renumbers files on every export -> rename by content hash so re-imports dedupe
        files = {}
        for f in list(Path(tmp).rglob("*")):
            if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                new = f"wa-{hashlib.md5(f.read_bytes()).hexdigest()[:10]}{f.suffix.lower()}"
                chat = chat.replace(f.name, new)
                files[new] = f.rename(f.with_name(new))
        sheet = items_text()
        print("Asking Claude (a minute or two)...", file=sys.stderr)
        out = subprocess.run(
            ["claude", "-p", "--output-format", "json", "--json-schema", json.dumps(SCHEMA),
             "--allowedTools", "Read", "--add-dir", tmp],
            input=PROMPT.format(sheet=sheet, chat=chat, photo_dir=tmp, statuses=", ".join(STATUSES)),
            capture_output=True, text=True, check=True).stdout
        res = json.loads(out)["structured_output"]
        items = [it for it in res["new_items"] if it["Photo"] in files]
        crops, photos = {}, {}
        for it in items:
            src_file = files[it["Photo"]]
            im = Image.open(src_file)
            if len(it["Crop"]) == 4:
                n = crops[it["Photo"]] = crops.get(it["Photo"], 0) + 1
                im = ImageOps.exif_transpose(im)
                w, h = im.size
                l, t, r, b = it["Crop"]
                im = im.crop((int(l * w), int(t * h), int(r * w), int(b * h)))
                it["Photo"] = f"{src_file.stem}-{n}.webp"
            else:
                it["Photo"] = f"{src_file.stem}.webp"
            # photo already uploaded on an earlier run = item already imported
            it["skip"] = not dry and supa.photo_exists(it["Photo"])
            if not it["skip"]:
                photos[it["Photo"]] = prepare(im)

    items = [it for it in items if not it["skip"]]
    clean = lambda s: " ".join(s.split()) or None
    rows = [{"room": clean(it["Room"]), "item": clean(it["Item"]), "category": clean(it["Category"]),
             "price": int(it["Price"]) if it["Price"].isdigit() else None, "status": it["Status"],
             "description": clean(it["Description"]), "photos": [it["Photo"]]} for it in items]
    for r in rows:
        print(f"  + {r['item']} | {r['category']} | {r['room']} | {r['price'] or ''} | {r['status']}")
    print(f"{len(rows)} new items." if rows else "No new items.")
    for u in res["updates"]:
        print(f"  ~ {u['item']}: {u['column']} -> {u['value']}")
    if dry:
        out_dir = Path(tempfile.mkdtemp(prefix="wa-preview-"))
        for name, data in photos.items():
            (out_dir / name).write_bytes(data)
        print(f"\nPreview photos: {out_dir}")
        return
    if not (rows or res["updates"]) or input("\nSave all of this? [y/N] ").strip().lower() != "y":
        return
    for name, data in photos.items():
        supa.upload(name, data, "image/webp")
    if rows:
        supa.insert(rows)
    for u in res["updates"]:
        value = int(u["value"]) if u["column"] == "Price" and u["value"].isdigit() else u["value"]
        supa.update(u["id"], {u["column"].lower(): value})
    print("Saved. Add Hebrew names on the site (Edit) or ask Claude to fill the *_he columns.")


if __name__ == "__main__":
    main(sys.argv[1], "--dry" in sys.argv)
