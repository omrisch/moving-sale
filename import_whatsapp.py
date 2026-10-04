"""WhatsApp chat export (.zip) -> photos/ + sheet rows on the clipboard, via `claude -p`.

    python3 import_whatsapp.py ~/Downloads/"WhatsApp Chat - Moving Sale.zip"
    python3 import_whatsapp.py export.zip --dry     # preview: photos to a temp folder, no push, no clipboard

Claude reads the chat + the current sheet, groups photos with their posts, skips
duplicates and items already in the sheet, and suggests status changes
(e.g. "sold the wagon") for existing rows. Re-exporting the whole chat each time is fine.
"""
from PIL import Image, ImageOps
import csv, hashlib, io, json, re, shutil, subprocess, sys, tempfile, urllib.request, zipfile
from pathlib import Path

HERE = Path(__file__).parent
PHOTOS = HERE / "photos"
SHEET_CSV_URL = re.search(r'SHEET_CSV_URL = "([^"]+)"', (HERE / "index.html").read_text()).group(1)
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
            "type": "object", "required": ["row", "item", "column", "value"],
            "properties": {"row": {"type": "integer"}, "item": {"type": "string"},
                           "column": {"type": "string"}, "value": {"type": "string"}}}},
    },
}

PROMPT = """You turn a WhatsApp chat of moving-sale posts into rows for a Google Sheet that powers a sale website.

CURRENT SHEET (row number, then its columns):
{sheet}

WHATSAPP CHAT (photo filenames are <attached: ...>; the files are in {photo_dir}):
{chat}

Rules:
- One new item per sale post; its photo is the <attached> file in the same message.
- Photo-only messages right after a post: if that post sells many things at a per-piece price (e.g. "any clothes 30 shekels"), each photo is its own item - open the photo with Read to name and describe it, price per the post. Otherwise they're extra photos of the same item; ignore them (one photo per item).
- One photo showing several separately-sellable things (e.g. 2 pairs of shoes) -> one item per thing, same Photo, each with Crop = [left, top, right, bottom] as fractions 0-1 of the image framing just that thing (generous margins). Otherwise Crop = [].
- Skip posts already in the sheet (Photo URL starting with the same wa-xxxxxxxxxx name, or same item) and repeated posts within the chat.
- Item: short English name (e.g. "Green Toys wagon", "2T autumn/winter clothes bundle"). No "(NEW)" tags; say "new" in Description instead.
- Price: digits only, the asking price (not what was originally paid). Blank if Free or unclear.
- Status: one of {statuses}. "Free" if given away for free.
- Category: reuse an existing sheet category when one fits, else a short new one (e.g. "Kids clothes", "Toys").
- Room: "Clothes" for any clothing, shoes or accessories (adults' or kids'). Otherwise reuse an existing Room value when obvious, else blank.
- Description: useful details (condition, sizes, contents, brands) as one line. Omit pickup location and price.
- Photo: the attached filename exactly.
- updates: only for messages that clearly change an existing sheet row (sold, reserved, price change). Column is Status or Price; Status must be from the list above. Otherwise empty.
"""


def sheet_text():
    rows = list(csv.reader(io.StringIO(urllib.request.urlopen(SHEET_CSV_URL).read().decode())))
    head = rows[0]
    keep = [head.index(c) for c in ["Room", "Item", "Category", "Price", "Status", "Photo URL"]]
    used = [n for n, r in enumerate(rows[1:], 2) if r[head.index("Item")].strip()]
    lines = ["row\t" + "\t".join(head[i] for i in keep)]
    lines += [f"{n}\t" + "\t".join(rows[n - 1][i] for i in keep) for n in used]
    return "\n".join(lines), max(used, default=1) + 1


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
        sheet, next_row = sheet_text()
        print("Asking Claude (a minute or two)...", file=sys.stderr)
        out = subprocess.run(
            ["claude", "-p", "--output-format", "json", "--json-schema", json.dumps(SCHEMA),
             "--allowedTools", "Read", "--add-dir", tmp],
            input=PROMPT.format(sheet=sheet, chat=chat, photo_dir=tmp, statuses=", ".join(STATUSES)),
            capture_output=True, text=True, check=True).stdout
        res = json.loads(out)["structured_output"]
        items = [it for it in res["new_items"] if it["Photo"] in files]
        crops = {}
        out_dir = Path(tempfile.mkdtemp(prefix="wa-preview-")) if dry else PHOTOS
        for it in items:
            src_file = files[it["Photo"]]
            if len(it["Crop"]) == 4:
                n = crops[it["Photo"]] = crops.get(it["Photo"], 0) + 1
                it["Photo"] = f"{src_file.stem}-{n}.jpg"
            out_dir.mkdir(exist_ok=True)
            if len(it["Crop"]) == 4:
                im = ImageOps.exif_transpose(Image.open(src_file)).convert("RGB")
                w, h = im.size
                l, t, r, b = it["Crop"]
                im.crop((int(l * w), int(t * h), int(r * w), int(b * h))).save(out_dir / it["Photo"], quality=88)
            else:
                shutil.copy(src_file, out_dir / it["Photo"])

    # Sheet columns A-H: Room, Item, Category, Price, Status, Date, Photo URL, Description
    # (stop at H: the (HE) columns hold GOOGLETRANSLATE formulas, don't paste over them)
    clean = lambda s: " ".join(s.split())
    tsv = "\n".join("\t".join([clean(it["Room"]), clean(it["Item"]), clean(it["Category"]), it["Price"],
                               it["Status"], "", f"photos/{it['Photo']}", clean(it["Description"])]) for it in items)
    print(f"\n{len(items)} new items (paste at A{next_row}):\n{tsv}" if items else "\nNo new items.")
    if res["updates"]:
        print("\nUpdate these existing cells by hand:")
        for u in res["updates"]:
            print(f"  row {u['row']} ({u['item']}): {u['column']} -> {u['value']}")
    if dry:
        print(f"\nPreview photos: {out_dir}")
    if dry or not items:
        return
    subprocess.run("pbcopy", input=tsv.encode(), check=True)
    subprocess.run(["git", "add", "photos"], cwd=HERE, check=True)
    subprocess.run(["git", "commit", "-m", f"Add {len(items)} item photos from WhatsApp"], cwd=HERE, check=True)
    subprocess.run(["git", "push"], cwd=HERE, check=True)
    print(f"\nRows copied to clipboard. Click cell A{next_row} in the sheet and paste.")


if __name__ == "__main__":
    main(sys.argv[1], "--dry" in sys.argv)
