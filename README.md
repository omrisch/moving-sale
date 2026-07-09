# Moving Sale

Static page. Google Sheet is the database. Edit the sheet, page updates.

## Setup (5 min)

1. Make a Google Sheet with these column headers in row 1:

   `Item | Category | Price | Status | Photo URL | Description`

   - `Status` must be one of: `For Sale`, `Free`, `Sold`, `Given Away`
   - `Photo URL`: upload photo to Google Drive/Photos (or anywhere), get a public link, paste it
   - `Price`: number only, leave blank if Free

2. **File → Share → Publish to web** → pick the sheet tab → format **CSV** → Publish → copy the link.

3. Open `index.html`, find this line near the top of the `<script>`:

   ```js
   const SHEET_CSV_URL = "PASTE_YOUR_PUBLISHED_CSV_LINK_HERE";
   ```

   Replace with the link you copied.

4. Open `index.html` in a browser to check it. If `fetch` fails locally, run a tiny local server:

   ```
   cd tools/moving-sale && python3 -m http.server 8000
   ```
   then visit `http://localhost:8000`.

## Share it with buyers

Push this folder to a free static host, e.g. **GitHub Pages** or drag the folder into **Netlify Drop** (netlify.com/drop). You get a public URL to send around. No further deploys needed — the page always pulls live from the Sheet.

## You + your wife organizing

Just edit the same Google Sheet together (Sheets supports simultaneous editing). The site is read-only — it reflects whatever's in the sheet.

- skipped: photo upload UI — you paste an already-hosted image link instead. Add an upload flow only if pasting links gets annoying.
- skipped: contact/inquiry form — page is browse-only for now. Add a mailto/WhatsApp link per item if buyers need a direct way to reach you.
