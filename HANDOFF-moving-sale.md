# HANDOFF — moving-sale

## Goal

Website for Omri + wife to organize items being sold/given away during their move, and to share with buyers/pickup-ers. Google Sheet is the data source (both spouses edit it directly); the site is a read-only static viewer, hosted on GitHub Pages.

- Live site: https://omrisch.github.io/moving-sale/
- Repo: https://github.com/omrisch/moving-sale (public, pushed from local git repo at this folder)
- Local path: `/Users/OmriSchulman1/Documents/claude-projects/tools/moving-sale/`

## Current Progress

Fully working, deployed, and pushed as of the last commit (`c9fa56f`).

Files:
- `index.html` — item listing page
- `info.html` — pickup logistics page (home + office areas)
- `styles.css` — shared styles for both pages
- `README.md` — sheet setup + feature docs, kept up to date
- `.git/` — repo initialized here, remote `origin` → `github.com/omrisch/moving-sale`, branch `main`, GitHub Pages enabled (serves from `main` root)

Features implemented:
- Fetches published Google Sheet CSV client-side (`SHEET_CSV_URL` const in `index.html`), no backend.
- Hand-rolled CSV parser (handles quoted fields/commas) — has an inline self-test (`selfTestParseCSV`).
- Hand-rolled fuzzy search (subsequence match per query word) — self-tested (`selfTestFuzzyMatch`).
- Filters: Status, Category (auto-derived from sheet), Price min/max (₪).
- Status values: `For Sale`, `Free`, `Sold`, `Given Away` (shown grayed out, no WhatsApp button), `Inactive` (fully hidden — filtered out right after parsing, not counted anywhere).
- WhatsApp contact button per item → `wa.me/<WHATSAPP_NUMBER>` (const in `index.html`, currently `9720585518225`) with a pre-filled message including item name + price. Hidden for Sold/Given Away.
- EN / Hebrew language toggle (top-right pill, `#langToggle`): switches fixed UI strings (`I18N` object in both `index.html` and `info.html`), flips `<html dir>` to rtl for Hebrew, persists choice via `localStorage` key `moving-sale-lang` (shared across both pages).
- Per-item translation: optional Sheet columns `Item (HE)`, `Category (HE)`, `Description (HE)` — falls back to English column if blank (`localField()` helper). No translation API used, by design (see What Didn't Work).
- `info.html`: two Leaflet + OpenStreetMap maps (home area, office area) showing an **approximate circle**, not an exact pin — coordinates intentionally offset from the real geocoded address (Airbnb-style fuzzing), defined in the `SPOTS` const. Real address is only shared once a buyer coordinates over WhatsApp — never published on the site.
- Nav link between pages ("Pickup info" / "Back to listings") — fixed top-left corner, does NOT swap sides when language toggles (this was explicitly requested twice — see below).
- Bright, non-dark-mode-adaptive theme (see below).

## What Worked

- **Google Sheet as DB** — zero backend, zero auth, both spouses edit concurrently in Sheets natively. Publish-to-web CSV export is free and reliable.
- **Netlify Drop was offered as a hosting option but user chose GitHub Pages** for easier iterative UI updates via git push. `gh repo create --source=. --push` + `gh api POST /repos/:owner/:repo/pages` got Pages live in two commands.
- **Hand-rolled fuzzy search / CSV parser** instead of pulling in a JS library — kept the site dependency-free except Leaflet (which is the right call for actual map tiles, no sane hand-rolled alternative).
- **Manual `(HE)` sheet columns instead of a live translation API** for per-item text — user explicitly chose this after being shown the tradeoff (see AskUserQuestion below). Zero dependency, zero runtime failure mode, translation quality fully in the user's control.
- Verifying logic by extracting the `<script>` block and `eval`-ing it in Node (with `document`-touching calls like `init()` stripped) to run the self-tests and spot-check `parseCSV`/`fuzzyMatch`/`localField`/`whatsappLink` before pushing — caught nothing broken but this is the repeatable verification pattern for this project since there's no test framework.

## What Didn't Work / Reconsidered

- **Removed `prefers-color-scheme: dark` CSS media query entirely.** Originally the site had a light+dark theme; user's system was in dark mode, so everything below the (always-colorful) header rendered dark, which read as "still dark" after a "brighter UI" request. Fix was to drop adaptive dark mode, not to tune dark-mode colors — one fixed bright theme always.
- **RTL mirroring of fixed-position UI elements caused two rounds of bug reports:**
  1. `.lang-toggle` and `.nav-link` had `html[dir="rtl"]` overrides that flipped which corner they sat in when switching EN↔HE. User wanted them corner-stable — removed the RTL position overrides entirely.
  2. Even after that, the EN/עברית buttons *inside* the toggle swapped left-right order on toggle, because `.lang-toggle` is a flex container that inherits `direction` from `<html>` (which the language toggle itself sets to rtl for Hebrew) — flexbox row order follows `direction`. Fixed by forcing `direction:ltr` explicitly on `.lang-toggle` so internal button order never changes regardless of page direction.
  - **Lesson for this project: any fixed-position/fixed-order chrome must not use `html[dir="rtl"]` selectors AND must have explicit `direction:ltr` if it's a flex/grid container, or it will silently invert when the language toggle flips `<html dir>`.** Check `info.html`'s equivalent elements too if similar bugs are reported there.
  3. Same bug hit `#grid` — CSS Grid mirrors auto-placed item order when the container's `direction` is `rtl`, so item cards visually reordered on toggle even though DOM order never changed. Fixed the same way: `direction:ltr` on `#grid`/`.filters`/`.controls`. **Caveat this introduced and then fixed**: forcing a container to `direction:ltr` also forces that value onto descendant text via inheritance, which would left-align/mis-shape Hebrew text inside `.card`, `.filters button`, and `.controls input`/`span`. Fixed by re-asserting `direction:rtl` on those specific descendants scoped to `html[dir="rtl"]` — this is NOT the same mistake as #1/#2 above, because here the selector only corrects text-flow *inside* an item whose position is already order-stable, it doesn't move the item itself. If a future report says "text looks wrong in Hebrew" for some new element, this is the pattern to reach for; if a report says "positions/order swap", that's the `direction:ltr`-on-container pattern instead.
- Considered auto-translating item data live via a free MT API (no key) — rejected via `AskUserQuestion`; too flaky/rate-limited/quality-uncertain for a "must always work for a stranger clicking a link" use case. Manual `(HE)` columns won instead.

## Next Steps

Nothing outstanding was requested beyond what's shipped. Natural candidates if the user asks:
- Populate the Sheet with real inventory (currently only 2 test rows: "Bed Side Table", "Dutch Oven").
- Verify `info.html` map circles render correctly in a real browser (only Node-verified for parse/search logic — Leaflet rendering itself was not visually screenshot-tested).
- If reporting more bugs about EN/HE toggle moving things, check for the same `direction`/`dir` inheritance trap described above before assuming it's a new bug class.
- Consider adding the same corner-stability check to any *future* fixed-position elements added to either page.
