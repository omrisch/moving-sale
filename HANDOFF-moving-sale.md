# HANDOFF — moving-sale

## Goal

Website for Omri + wife to organize items being sold/given away during their move, and to share with buyers/pickup-ers. Google Sheet is the data source (both spouses edit it directly); the site is a read-only static viewer, hosted on GitHub Pages.

- Live site: https://omrisch.github.io/moving-sale/
- Repo: https://github.com/omrisch/moving-sale (public, pushed from local git repo at this folder)
- Local path: `/Users/OmriSchulman1/Documents/claude-projects/tools/moving-sale/`

## Current Progress

Fully working, deployed, and pushed as of the last commit (`11ea479`).

Files:
- `index.html` — item listing page
- `info.html` — pickup logistics page (home + office areas)
- `styles.css` — shared styles for both pages
- `README.md` — sheet setup + feature docs, kept up to date
- `photos/` — local item photos, pushed to the repo and served via relative path `photos/<filename>` from GitHub Pages
- `.git/` — repo initialized here, remote `origin` → `github.com/omrisch/moving-sale`, branch `main`, GitHub Pages enabled (serves from `main` root)

### Sheet columns (as of last check)

`Room, Item, Category, Price, Status, Date, Photo URL, Description, Item (HE), Category (HE), Status (HE), Date (HE), Description (HE)`

- **`Room`** (new) — internal-tracking column Omri added himself, now also wired into the site as a filter + sort option (no code change was needed for the column to *exist* since the CSV parser is header-driven and position-agnostic — code was added separately to actually filter/sort by it).
- **`Status (HE)` / `Date (HE)`** (new) — per-item Hebrew overrides, same fallback-to-English pattern as `Item (HE)`/`Category (HE)`/`Description (HE)`. Omri fills these via a live `GOOGLETRANSLATE()` formula in the sheet — **important**: this means the published CSV can transiently contain literal `"Loading..."` or `"#VALUE!"`/`"#N/A"` text instead of a real translation (confirmed by curling the same cell twice, 3s apart, and getting different values — it's a live recalculating formula, not stable data). The site guards against this via `isTranslatePlaceholder()` in `index.html`, which treats those strings as absent and falls back to English. **If any new (HE) column is ever added, reuse this guard, don't assume the cell is stable text.**
- **`Description`** now sometimes holds a plain product URL (original retailer link) appended after any existing free text, e.g. `"Like New https://www.ikea.com/..."`. These came from a research pass (see below) and the site renders any URL found in Description as a "More info" hyperlink (`formatDescription()`), not as raw text.

### Features implemented (cumulative)

- Fetches published Google Sheet CSV client-side (`SHEET_CSV_URL` const in `index.html`), no backend.
- Hand-rolled CSV parser (handles quoted fields/commas), header-driven/position-agnostic — self-tested (`selfTestParseCSV`).
- Hand-rolled fuzzy search — **tokenized** subsequence match (see "What Didn't Work" below for why this changed) — self-tested (`selfTestFuzzyMatch`).
- Filters, all now in a **left sidebar** (`<aside class="sidebar">`, see layout section below): Status, Category, **Room (new)**, Price min/max (₪), Date "Available by ≤".
- Sort dropdown (`#sortSelect`): Default / Name (A→Z) / Date (soonest first) / **Room (A→Z) (new)**. Undated items sort **first** under "Date" mode (flipped from originally sorting last — Omri clarified no date = already available now, not "unknown/last").
- Status values: `For Sale`, `Free`, `Available Soon`, `Sold`, `Given Away` (grayed out, no WhatsApp button), `Inactive` (fully hidden). `Available Soon` keeps the WhatsApp button active.
- When an item is `Available Soon` **and** has a `Date`, the redundant "Available Soon" status badge is now suppressed — only the "Available from {date}" badge shows (both used to render at once).
- `Date` column: free text, parsed via `new Date(it.Date)` (`parseItemDate()`) for sort/filter — recommend `YYYY-MM-DD`. Sorting/filtering always uses the English `Date` column; `Date (HE)` is display-only (can't be parsed).
- WhatsApp contact button per item, 3s global cooldown to deter rapid repeat taps.
- EN/Hebrew toggle, persisted via `localStorage`. Sidebar and grid stay visually **left**-anchored/order-stable in both languages (same `direction:ltr`-on-container + re-assert `direction:rtl`-on-descendants pattern as the rest of the site — see "What Didn't Work").
- Per-item translation columns fall back to English when blank or a translate-formula placeholder (`localField()`, `localStatus()`, `localDate()`, all sharing `isTranslatePlaceholder()`).
- **Infinite-scroll batch rendering (new)**: `index.html` renders item cards 8 at a time (`BATCH_SIZE`), loading the next batch via `IntersectionObserver` on `#scrollSentinel` as the user scrolls — instead of building all ~50 cards (+ firing all their image loads) on first paint. State lives in module-level `renderState` (`{filtered, shown, lang}`); `render()` resets it and calls `appendBatch()` once, the observer calls `appendBatch()` again on scroll.
- **Loading spinner (new)**: `#loading` now has a CSS-only spinner (`.spinner` + `@keyframes spin`) alongside the text, for perceived performance while the CSV fetch is in flight.
- **Left sidebar layout (new)**: all filters/sort moved from the top into `<aside class="sidebar">` (240px fixed column, `position:sticky`), item grid into `<main class="content">`. `.layout{display:flex;direction:ltr}` keeps the sidebar visually left in both languages; collapses to stacked full-width on mobile (`@media max-width:760px`).
- `info.html`: two Leaflet + OpenStreetMap maps showing an approximate/fuzzed circle, not an exact pin.
- Nav link fixed top-left, corner-stable across language toggle.
- Bright, non-dark-mode-adaptive theme.

## Recent session: product-link research + description links

Omri asked for a CSV of original-retailer product links (IKEA, Decathlon, Nespresso, etc.) to paste into the sheet's `Description` column, to give buyers a reference for what the item actually is.

**Process**: split the ~52 sheet items into 5 groups (by Room) and ran them as 5 **parallel background `Agent` calls**, each told to web-search and *verify* (not guess) a real, resolving product-page URL per item, returning `NONE` when no confident match existed (generic/unbranded items, ambiguous model numbers, discontinued products with no live page). Result: 23/52 items got a verified link. A `Mirror` item was later identified by Omri as IKEA NISSEDAL specifically (multiple color/size variants exist — asked Omri which one via `AskUserQuestion` rather than guess).

**Lesson — don't use `HYPERLINK()` formulas for this**: first instinct was to write the CSV cells as `=HYPERLINK("url","label")` so pasting into Sheets renders clickable links directly. Wrong: Google Sheets' *published-to-web CSV export* (what the site fetches) bakes formulas down to their **computed display text only** — the URL itself is dropped, so the site could never parse it back out. Correct approach: paste **plain text** (existing description + a bare URL), and have the **site** parse the URL out of the Description string and render it as a link (see `formatDescription()` in index.html, label configurable — currently "More info", was briefly "Link to item" per an earlier ask). This is the durable pattern for any future "paste computed-looking values into cells that the site later needs to parse" request — always ask "does the published CSV export preserve this, or only its display value?"

## What Worked

- **Google Sheet as DB**, publish-to-web CSV, zero backend/auth.
- **GitHub Pages via `gh` CLI** for iterative UI updates via git push.
- **Hand-rolled fuzzy search / CSV parser** instead of a JS dependency — CSV parser's header-driven design meant the new `Room` column needed zero parser changes.
- **Manual `(HE)` sheet columns** instead of a live translation API for *item* text — though Omri did end up using `GOOGLETRANSLATE()` for `Status (HE)`/`Date (HE)`, which is what surfaced the placeholder-flicker issue above. Worth knowing before recommending GOOGLETRANSLATE for anything else in this sheet.
- **5 parallel research `Agent`s** for the product-link lookup — much faster than one sequential pass over 52 items, and keeping each agent scoped to one Room group with explicit "verify, don't guess, say NONE if unsure" instructions kept the false-positive rate low.
- **Playwright MCP + local `python3 -m http.server`** remains the right verification pattern for this project — used repeatedly this session to catch real, non-obvious bugs (see below) that Node-only self-tests missed entirely, because they only reproduce with real fetched sheet data and real DOM/event wiring, not synthetic unit inputs.

## What Didn't Work / Bugs Found & Fixed This Session

- **Search silently broke when links were added to Description.** The hand-rolled fuzzy matcher did subsequence matching (`isSubsequence`) against the **entire concatenated haystack string** (all fields glued together with spaces), not per-word. Two independent problems stacked on top of each other:
  1. Appending long product URLs (80+ chars, one continuous token) into `Description` meant almost *any* short query was accidentally a subsequence of the URL itself (e.g. "guitar" is a subsequence of a random IKEA URL just by letter-order coincidence).
  2. Even after stripping URLs from the search haystack (`stripUrl()`), matching across the *whole* haystack still let letters from **unrelated adjacent fields** chain together into false positives — e.g. "guitar" matched "Grey Plant Stand Furniture" because the English fields get duplicated in the haystack (once as `it.Item`, again via `localField(it,"en",...)` which returns the same value when there's no HE difference), giving enough letters for a coincidental g→u→i→t→a→r chain to complete *across* both copies.
  - **Fix**: `fuzzyMatch()` now tokenizes the haystack by whitespace and requires each query word to be a subsequence of a **single token**, not spanning tokens/fields. Combined with `stripUrl()` still removing URLs before building the haystack (a single very long token could still accidentally contain a short query as a subsequence). Both fixes verified live via Playwright against the real sheet.
  - **Lesson**: any future haystack-widening change (new field added to search) needs re-testing against short/generic queries with Playwright + real data, not just the existing Node self-tests — the self-tests use short, curated strings that don't have enough length/redundancy to expose this class of bug.
- **Price filter silently included every blank-price item.** Original logic only applied the min/max check `if (!isNaN(price))` — so items with an empty `Price` cell (most Free items, several unpriced items) bypassed the filter entirely and always showed, even with an active price range set. Fixed: if either `min` or `max` is set, items without a parseable price are now excluded.
- **Removed `prefers-color-scheme: dark` CSS media query entirely** (earlier session) — a "brighter UI" request read as unfixed because dark mode was still adaptive; fix was to drop adaptive dark mode, not tune its colors.
- **Infinite scroll stopped loading more items after search narrowed the list.** `IntersectionObserver` only fires its callback on an intersection *state change* (not-visible→visible or vice versa). If the sentinel was already visible before a search (short page) and remained visible after (still short page), no new callback fired, so `appendBatch()` never ran again even though `renderState.shown < renderState.filtered.length`. **Fix**: added `fillViewport()` — loops `appendBatch()` while the sentinel is still within `rootMargin` of the viewport — called from both `render()` (so search/filter results fill the visible area immediately) and the observer callback (so scroll-triggered loads also fully catch up in one go instead of one batch per callback). Verified via Playwright: searched for a broad query (44/53 matches), confirmed scrolling now progressively loads batches (16→24→32...) instead of freezing at the first 8.
- **RTL mirroring of fixed-position/fixed-order UI is a recurring bug class in this project.** Three confirmed instances so far: `.lang-toggle`/`.nav-link` corner position, the EN/עברית button order inside the toggle, and `#grid`/`.filters`/`.controls` item/button order. All three share one root cause: flex/grid child order and any `html[dir="rtl"]` position override both follow the inherited CSS `direction`, so anything meant to stay visually stable across language toggle needs **explicit `direction:ltr` on the container**, with `direction:rtl` re-asserted only on descendant *text* elements (inputs/spans/card content), never on the container itself. **The new sidebar (`.layout`, `.sidebar`) follows this same pattern** — confirmed via Playwright screenshot that it stays left in both languages. Any new fixed-position/fixed-order element added to either page should follow this same recipe from the start rather than being discovered as a bug later.
- Considered auto-translating item data live via a free MT API — rejected earlier for reliability; Omri later chose `GOOGLETRANSLATE()` sheet formulas for Status/Date specifically, which is a different tradeoff (see placeholder-flicker issue above) — worth surfacing if he asks to extend HE translation to other fields.

## Next Steps

- Watch for further sheet edits to `Status (HE)`/`Date (HE)` — if Omri reports Hebrew still showing English/garbage, check whether `isTranslatePlaceholder()` needs a new placeholder string added (currently matches `"Loading..."` and any `#XXXX!`/`#XXXX` Sheets error pattern).
- The product-link CSV (23/52 items linked) was pasted into the sheet's `Description` column already. If Omri wants the remaining ~29 unlinked items (mostly unbranded/generic — fridge, oven, dishwasher, car, motorcycle, etc.) followed up, that would need either more specific hints from him (make/model) or accepting no link for genuinely generic items.
- If new sheet columns get added in the future needing HE fallback, follow the `isTranslatePlaceholder()`-guarded pattern established this session, not the earlier unguarded `localField()` pattern.
- If Omri ever wants direct Sheet-writing (vs. manual paste), the path is a GCP service account (sheet shared as Editor, key JSON, docId-based write script) — offered and declined before, don't re-propose Drive-sync `.gsheet` files (confirmed dead end, `.gsheet` is just a cloud pointer JSON).
- Verify `info.html` map circles render correctly in a real browser if that page gets touched again — it was only Node-verified for parse/search logic in an earlier session, never Playwright-screenshot-tested.
- General pattern going forward: **any change to `index.html` that touches filtering/sorting/search should get a Playwright pass against the live sheet data before pushing** — this session's bugs (search, price filter) both passed Node self-tests fine but only reproduced against real multi-item, real-field data in a real browser.
