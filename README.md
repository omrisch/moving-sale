# Moving Sale

Static site on GitHub Pages; items and photos live in Supabase (free tier). No build step.
Visitors browse anonymously; only admins (Omri + Estella) can sign in and change things.

Live at: **https://omrisch.github.io/moving-sale/**
Repo: **https://github.com/omrisch/moving-sale**

## Files

- `index.html` — the item listing (search, filters, cart, WhatsApp contact) + admin login/forms
- `info.html` — pickup logistics page (approximate location maps)
- `pickups.html` — **admin-only** calendar of pickups/deliveries (when, where, who, which items); `pickups` table in `schema.sql`
- `styles.css` — shared styling for both pages
- `schema.sql` — the database: `items` table, photo bucket, and the rules (visitors read, admins write)
- `supa.py` — tiny Supabase client for the local scripts (reads `.env`)
- `import_whatsapp.py` — WhatsApp chat export -> new items + photos
- `migrate_from_sheet.py` — one-time copy of the old Google Sheet (done once, kept for reference)
- `.env` — **not committed**: `SUPABASE_SECRET_KEY=...` and `DATABASE_URL=...`

## Editing items

- **On the site:** "Admin login" at the bottom of the filters. Then "+ Add item", and on each card a
  status dropdown, Edit and Delete. Photos picked on the phone are resized and stripped of GPS before upload.
  Status `Inactive` hides an item from visitors (admins still see it).
- **From Claude (incl. the mobile app):** claude.ai > Customize > Connectors > find **Supabase** (or
  Add custom connector: `https://mcp.supabase.com/mcp?project_ref=<project ref>&features=database`),
  sign in with the Supabase account. Then in any chat: "mark the wagon sold", "fill the Hebrew names",
  "lower all toys by 10 shekels". It edits the `items` table directly. It has full database access, so
  read what it plans to run before approving anything that isn't about `items`.
- **ChatGPT:** same connector URL, via developer-mode connectors (check your plan supports it).

## Setup (once)

1. Supabase project (free) > copy Project URL + publishable key into `SUPABASE_URL` /
   `SUPABASE_PUBLISHABLE_KEY` in `index.html` (both are public by design).
2. `.env` with the secret key + database connection string (Connect > Session pooler).
3. `psql "$DATABASE_URL" -f schema.sql`
4. Authentication > Sign In / Providers: turn off "Allow new users to sign up". Users > Add user for
   each admin, then: `update auth.users set raw_app_meta_data = raw_app_meta_data || '{"role":"admin"}' where email = '...';`

## Pickups calendar

`pickups.html` ("Pickups" button in the admin bar). Month grid on desktop, agenda list on phones.
Click a day to add, an entry to edit; each entry links to WhatsApp/call the buyer.
Rows live in the `pickups` table (admins only, visitors can't read it). Any assistant with the Supabase
connector can write it: one row per appointment, `day` + `at` are local Israel date/time, `item_ids`
are `items.id`. The table comment tells the assistant this, plus to set those items to Reserved.

## Adding items from WhatsApp

1. Forward the sale posts (photo + caption) into one dedicated WhatsApp chat.
2. Phone: that chat > chat info > **Export Chat > Attach Media** > save the zip to the Mac.
3. `python3 import_whatsapp.py ~/Downloads/"WhatsApp Chat - <name>.zip"` (`--dry` to preview)
   - `claude -p` names/prices/categories each post, one item per photo for "any piece X shekels" posts,
     crops photos showing several items, skips anything already listed, Room = `Clothes` for clothing
   - suggests status/price changes from messages like `sold - green toys wagon`
   - shows everything and asks before saving; photos go to Supabase storage (resized, no GPS)

Re-export the whole chat each time; photos already uploaded are skipped.

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
- **Filters** — status, category, room, price range (₪ min/max), available-by date; sort options.
- **Language toggle** (EN / עברית) — switches UI text and the `*_he` columns when filled; RTL in Hebrew.
- **WhatsApp button** per item, pre-filled with the item name + price (`WHATSAPP_NUMBER` in `index.html`). Hidden on Sold/Given Away.
- **My list (cart)** — "+ Add to my list" on each card; floating "My list (n)" opens the list with a total and sends one WhatsApp message listing everything. Saved per-browser, no accounts; sold/deleted items drop off on next visit.
- **Several photos per item** — first is the card cover (star a photo in the edit form to make it the cover); clicking a card shows all of them.
- **Item view** — clicking a card opens all photos + every detail read-only, with WhatsApp / Add to my list.
- **Visitor stats** — https://omrisch.goatcounter.com (no cookies). Your own visits aren't counted while logged in as admin.
- **Pickup info page** (`info.html`) — two maps showing an approximate circle, not an exact pin. Exact address only over WhatsApp.

