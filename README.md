# Moving Sale

Static site. Google Sheet is the database — edit the sheet, the site updates. No backend, no build step.

Live at: **https://omrisch.github.io/moving-sale/**
Repo: **https://github.com/omrisch/moving-sale**

## Files

- `index.html` — the item listing (search, filters, WhatsApp contact)
- `info.html` — pickup logistics page (approximate location maps)
- `styles.css` — shared styling for both pages

## Sheet setup

1. Google Sheet, row 1 headers:

   `Item | Category | Price | Status | Photo URL | Description`

   Optional Hebrew translation columns (leave blank to fall back to English):

   `Item (HE) | Category (HE) | Description (HE)`

   - `Status` must be one of: `For Sale`, `Free`, `Sold`, `Given Away`, `Inactive`
     - `Sold` / `Given Away` still show on the site, grayed out, no WhatsApp button.
     - `Inactive` is fully hidden — not shown, not counted, not filterable. Use it for items not ready to list yet.
   - `Photo URL`: upload photo to Google Drive/Photos (or anywhere), get a public link, paste it
   - `Price`: number only (₪), leave blank if Free

2. **File → Share → Publish to web** → pick the sheet tab → format **CSV** → Publish → copy the link.

3. In `index.html`, near the top of the `<script>`:

   ```js
   const SHEET_CSV_URL = "...";
   ```

   already set to the published link. Only touch this if you republish under a different link.

## Updating the live site

```
git add -A
git commit -m "describe the change"
git push
```

GitHub Pages redeploys automatically after a push (usually live within ~1 min).

## Local preview

```
cd tools/moving-sale && python3 -m http.server 8000
```
then visit `http://localhost:8000`.

## Features

- **Search** — fuzzy (typo/partial-tolerant), matches item/category/description in both languages.
- **Filters** — status, category (auto-built from the sheet), price range (₪ min/max).
- **Language toggle** (EN / עברית, top-right) — switches UI text and, if filled in, the `(HE)` columns; saved per-browser via localStorage. Switches the page to RTL in Hebrew.
- **WhatsApp button** per item, pre-filled with the item name + price, sent to the shared number in `WHATSAPP_NUMBER` (near the top of `index.html`'s script). Hidden on Sold/Given Away items.
- **Pickup info page** (`info.html`, linked from the header) — two maps (home / office) showing an approximate circle, not an exact pin, à la Airbnb. Coordinates are intentionally offset from the real address — see the `SPOTS` constant in `info.html` if you need to adjust them. Exact address is only shared once you've coordinated over WhatsApp.

## You + your wife organizing

Edit the same Google Sheet together (Sheets supports simultaneous editing). The site is read-only — it always reflects whatever's currently in the sheet.

- skipped: photo upload UI — paste an already-hosted image link instead. Add an upload flow only if pasting links gets annoying.
- skipped: automatic address reveal — pickup address is exchanged manually over WhatsApp, not published on the site, by design.
