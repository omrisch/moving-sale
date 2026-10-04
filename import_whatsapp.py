"""WhatsApp chat export (.zip) -> photos/ + sheet rows on the clipboard.

    python3 import_whatsapp.py ~/Downloads/"WhatsApp Chat - Sale inbox.zip"
    python3 import_whatsapp.py export.zip --dry     # preview only: no copy, no push

Each image + its caption becomes one row. Photos already in photos/ are skipped,
so re-exporting the whole chat every time is fine.
"""
import re, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path

HERE = Path(__file__).parent
PHOTOS = HERE / "photos"
# iOS:     [04/10/2026, 16:54:12] Name: text
# Android: 04/10/2026, 16:54 - Name: text
HEADER = re.compile(r"^‎?\[?\d{1,2}[./]\d{1,2}[./]\d{2,4},? \d{1,2}:\d{2}(?::\d{2})?(?: ?[AP]M)?\]? (?:- )?[^:]+: (.*)$")
IMAGE = re.compile(r"[\w\-]+\.(?:jpe?g|png|webp)", re.I)
ATTACH_NOISE = re.compile(r"<attached: [^>]*>|\(file attached\)|image omitted|‎")
# ponytail: price = last number next to shekel/₪/NIS/"for"; anything fancier, fix it in the sheet
PRICE = re.compile(r"(?:₪|for)\s*(\d[\d,]*)|(\d[\d,]*)\s*(?:₪|shekels?|nis|ש\"ח|שקל)", re.I)
FREE = re.compile(r"\bfree\b|חינם|במתנה", re.I)


def messages(chat_text):
    msgs = []
    for line in chat_text.splitlines():
        m = HEADER.match(line)
        if m:
            msgs.append(m.group(1))
        elif msgs:
            msgs[-1] += "\n" + line
    return msgs


def items(msgs):
    """Images followed by caption text (same message or the next one) -> (photo, caption)."""
    out, pending = [], []
    for msg in msgs:
        imgs = IMAGE.findall(msg)
        text = ATTACH_NOISE.sub("", IMAGE.sub("", msg)).strip()
        pending += imgs
        if text and pending:
            out.append((pending[0], text))  # ponytail: first image only; multi-photo items later if needed
            pending = []
    out += [(p, "") for p in pending]
    return out


def row(photo, caption):
    name = re.split(r" - |\. |, |\n", caption, maxsplit=1)[0].strip() or "UNNAMED"
    prices = [a or b for a, b in PRICE.findall(caption)]
    free = bool(FREE.search(caption))
    price = "" if free or not prices else prices[-1].replace(",", "")
    desc = " ".join(caption.split())
    # Sheet columns A-H: Room, Item, Category, Price, Status, Date, Photo URL, Description
    # (stop at H: the (HE) columns hold GOOGLETRANSLATE formulas, don't paste over them)
    return ["", name, "", price, "Free" if free else "For Sale", "", f"photos/{photo}", desc]


def main(src, dry):
    with tempfile.TemporaryDirectory() as tmp:
        zipfile.ZipFile(src).extractall(tmp)
        chat = next(Path(tmp).rglob("*.txt")).read_text(encoding="utf-8")
        new = [(p, c) for p, c in items(messages(chat)) if not (PHOTOS / p).exists()]
        if not dry:
            PHOTOS.mkdir(exist_ok=True)
            for p, _ in new:
                shutil.copy(next(Path(tmp).rglob(p)), PHOTOS / p)
    if not new:
        print("Nothing new.")
        return
    tsv = "\n".join("\t".join(row(p, c)) for p, c in new)
    print(tsv)
    if dry:
        return
    subprocess.run("pbcopy", input=tsv.encode(), check=True)
    subprocess.run(["git", "add", "photos"], cwd=HERE, check=True)
    subprocess.run(["git", "commit", "-m", f"Add {len(new)} item photos from WhatsApp"], cwd=HERE, check=True)
    subprocess.run(["git", "push"], cwd=HERE, check=True)
    print(f"\n{len(new)} rows copied. Paste into the first empty row, column A.")


def demo():
    ios = ("[04/10/2026, 16:54:12] Wife: ‎<attached: 00000012-PHOTO-2026-10-04-16-54-12.jpg>\n"
           "[04/10/2026, 16:54:20] Wife: (NEW) Garbage truck toy new on the box - with lights. Payed 120 shekels, selling for 70. Pickup in Ramat Gan\n"
           "[04/10/2026, 16:49:01] Wife: ‎<attached: 00000013-PHOTO-2026-10-04-16-49-01.jpg>\n"
           "Orchard Shopping list game, a mix between memory game and bingo. In perfect condition - 40 shekels.\n"
           "[04/10/2026, 17:00:00] Wife: ok thanks\n")
    rows = [row(*i) for i in items(messages(ios))]
    assert [r[1] for r in rows] == ["(NEW) Garbage truck toy new on the box", "Orchard Shopping list game"], rows
    assert [r[3] for r in rows] == ["70", "40"], rows
    android = "04/10/2026, 16:54 - Wife: IMG-20261004-WA0001.jpg (file attached)\nKids chair, free\n"
    r = row(*items(messages(android))[0])
    assert r[1] == "Kids chair" and r[4] == "Free" and r[3] == "" and r[6] == "photos/IMG-20261004-WA0001.jpg", r
    print("ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]:
        demo()
    else:
        main(sys.argv[1], "--dry" in sys.argv)
