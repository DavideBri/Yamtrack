# Yamtrack Frontend Rebuild — Mobile-First PWA (TV Time-style)

Status: **DRAFT v1** — living document, more reference material to come.
Branch: `claude/pwa-mobile-first-rebuild-qxh9x9`

## 1. Goal

Rebuild the Yamtrack UI as a **mobile-first, installable PWA** with app-like
performance and a design language modeled on TV Time (see reference
screenshots): bottom tab navigation, top segmented tabs (Watchlist / Upcoming),
swipeable list/grid views, big one-tap check-in buttons, poster grids with
progress bars, and countdown cards for upcoming episodes.

Desktop stays fully supported (sidebar layout at `lg:`+), but every screen is
designed for the phone first and enhanced upward.

## 2. Current state (audit)

| Area | Today |
|---|---|
| Rendering | Django server-rendered templates, HTMX 2.0 partial swaps |
| Interactivity | Alpine.js 3.x (dropdowns, modals, menu state) |
| Styling | Tailwind CSS v4 (`static/css/input.css` → `main.css`), dark-only hardcoded hex palette (`#212529`, `#1a1d20`…) |
| Images | lazysizes lazy-loading |
| Navigation | Fixed left sidebar; on mobile it's an overlay drawer behind a hamburger — no bottom nav |
| PWA | Manifest is good (icons, shortcuts, screenshots); service worker is minimal cache-first with a single static list, no runtime caching, no offline page, no cache versioning strategy |
| API | None — all endpoints return HTML. Key interactions: `media_save`, `episode_save`, `media_delete`, `progress_edit`, `track_modal`, `history_modal` |
| Pages | Home (up-next sections), Media list (grid/table), Search, Media details, Season details, Calendar (events app), Statistics, Lists, Profile/Settings |

### What this means for architecture

The backend has no JSON API, and the HTMX + Alpine stack is already
lightweight (~60 KB JS total). A SPA rewrite (React/Vue + DRF) would require
building an entire API surface first and would *hurt* first-load performance.

**Decision: keep Django + HTMX + Alpine + Tailwind. Rebuild the presentation
layer (templates, CSS, navigation model, service worker), not the stack.**
This gets TV Time UX and PWA performance with a fraction of the risk. A JSON
API can still be added later for a native app without throwing this work away.

## 3. Design system (TV Time-inspired)

### 3.1 Navigation model

- **Mobile (`< lg`)**: fixed **bottom tab bar** (safe-area aware,
  `env(safe-area-inset-bottom)`), 4–5 tabs:
  - **Shows** (TV/anime up-next — the home experience)
  - **Movies** (and other one-shot media)
  - **Discover** (search)
  - **Profile** (stats, lists, settings)
  - The current hamburger/drawer disappears on mobile; secondary destinations
    (calendar, individual media-type lists, lists, settings) move under
    Profile and into top-level tabs' own headers.
- **Desktop (`lg:`+)**: keep the sidebar (already good), bottom bar hidden.
- **Top segmented tabs** inside sections, mirroring TV Time:
  - Shows → `Watchlist | Upcoming` (Watchlist = current home "in progress /
    watch next" sections; Upcoming = calendar data scoped to tracked media)
  - Swipe left/right between segments (CSS scroll-snap; no JS carousel lib).

### 3.2 Core components (new template components)

| Component | TV Time reference | Notes |
|---|---|---|
| `episode_card` | "S05 \| E01 +7 · Soda" cards | Landscape still/backdrop left, show-name pill (chevron → details), `SXX \| EYY (+n)` line, episode title, **large circular check button** on the right. Check = `episode_save` via HTMX, optimistic UI (fills green instantly, reverts on error) |
| `countdown_card` | "44 GIORNI" upcoming cards | Same anatomy but right side shows big day-count; PREMIERE/FINALE badges; expandable "N episodes" accordion |
| `poster_card` | Grid view | 2:3 poster, bottom progress bar (existing `progress_bar.html` restyled), watched-count overlay in grid-of-upcoming variant |
| `section_pill` | "GUARDA IL PROSSIMO" headers | Centered gray pill section separators |
| `view_toggle` | Grid icon top-right | List ⇄ grid per section, persisted per user (existing `layout` param on media_list — extend to home) |
| `bottom_sheet` | — | Replace desktop-style modals (track modal, history modal) with bottom sheets on mobile, drag-to-dismiss (Alpine + CSS transforms) |
| `badge` | PREMIERE / ULTIMO | Black pill badges on cards |
| `skeleton` | — | Skeleton shimmer placeholders for every card type, used during HTMX loads |

### 3.3 Visual tokens

- Replace scattered hex values with **CSS custom properties** in
  `@theme` (Tailwind v4): `--color-surface`, `--color-surface-raised`,
  `--color-accent` (TV Time yellow `#fdd935` as progress/accent candidate —
  final palette TBD with the user), `--color-success` (check green).
- Light + dark themes via `prefers-color-scheme` with manual override
  (TV Time screenshots are light; Yamtrack today is dark-only — support both,
  keep dark as default).
- Typography: keep Roboto Flex (already self-hosted woff2), tighten the scale
  for mobile density (large numerals for countdowns).

## 4. Screen mapping (TV Time → Yamtrack)

| TV Time screen | Yamtrack page | Work |
|---|---|---|
| Watchlist (list view, IMG_7930) | Home | Re-render `home_section` as episode-card list: "Watch next" / "Haven't watched in a while" sections (backend already computes sections). Add watch-history sub-list (episodes just checked, grayed with green check) |
| Watchlist (grid view, IMG_7931) | Home | Poster grid with yellow progress bars, view toggle top-right |
| Upcoming (list, IMG_7932/7933) | New `Upcoming` segment on home; data from events/calendar app filtered to user's tracked media | Countdown cards grouped by date pills ("25 JUN 2026", "Later"), expandable episode lists |
| Upcoming (grid, IMG_7934) | Same | Poster grid with day-count overlay |
| Bottom nav | Global | New `base.html` layout |

Media details, season details, search, statistics, lists, calendar and
settings are **restyled with the same component library** (cards, sheets,
pills) but keep their current information architecture.

## 5. PWA & performance workstream

### 5.1 Service worker rewrite (`serviceworker.js`)

- **Precache app shell**: CSS, JS libs, fonts, icons, an `/offline` fallback
  page — with build-hash-based cache names (reuse existing
  `get_static_file_mtime` mtime pattern to generate a version string in the
  SW template — serve SW through Django view, which already exists).
- **Runtime strategies**:
  - Posters/stills (TMDB etc.): `stale-while-revalidate`, capped LRU cache
    (e.g. 300 entries) — biggest perceived-speed win.
  - HTML navigations: `network-first` with cache fallback + offline page.
  - Static: `cache-first`.
- **Offline check-in queue (stretch)**: queue `episode_save` POSTs in
  IndexedDB via Background Sync, replay when online, reconcile UI.

### 5.2 Performance budget & tactics

- Budgets: < 100 KB JS (gzip), < 50 KB CSS, LCP < 2.0 s on mid-range Android
  over 4G, CLS < 0.1, Lighthouse PWA + Performance ≥ 90.
- Replace lazysizes with native `loading="lazy"` + `decoding="async"` +
  explicit `width/height` (kills CLS, drops a JS lib).
- `fetchpriority="high"` on first-viewport posters; responsive `srcset`
  from provider image sizes (TMDB has them for free).
- Cross-document **View Transitions** (`@view-transition`) + poster
  `view-transition-name` for app-like page morphs — pure CSS, no JS.
- HTMX partial swaps for tab/segment switches (no full page reload between
  Watchlist/Upcoming); `hx-boost` for internal navigation.
- Paginate/lazy-load home sections (`hx-trigger="revealed"`), avoid
  rendering entire library server-side in one response.
- Audit N+1 queries on home/media_list while touching views (they gate TTFB).

### 5.3 Manifest polish

- Already strong; update `theme_color`/`background_color` to new tokens, add
  fresh mobile screenshots (`form_factor: narrow`), verify maskable icons.

## 6. Task flow (phased, each phase shippable)

### Phase 0 — Foundations *(no visible change)*
- [ ] 0.1 Design tokens: extract palette to `@theme` custom properties; map current hexes; add light-scheme values.
- [ ] 0.2 Component scaffolding: create `templates/app/components/ui/` (badge, pill, skeleton, sheet, card shells) with a demo page behind DEBUG.
- [ ] 0.3 Baseline metrics: record Lighthouse (mobile) scores + bundle sizes for home, media list, details. These are the regression gate.

### Phase 1 — App shell & navigation
- [ ] 1.1 New `base.html` layout: bottom tab bar (mobile) / sidebar (desktop), safe-area insets, `100dvh` layout, scroll restoration.
- [ ] 1.2 Move secondary nav under Profile tab; header restructure per-screen (title, segmented tabs, view toggle).
- [ ] 1.3 `hx-boost` navigation + View Transitions between pages.
- [ ] 1.4 Acceptance: all existing pages reachable on mobile without drawer; no horizontal scroll anywhere; tap targets ≥ 44 px.

### Phase 2 — Watchlist (home) rebuild ← the money screen
- [ ] 2.1 Episode card component with one-tap check-in (optimistic HTMX, error revert, undo toast).
- [ ] 2.2 Home list view: section pills, "watch next" / stale sections, recently-watched history rows.
- [ ] 2.3 Home grid view: poster cards + progress bars, view toggle persisted per user.
- [ ] 2.4 Skeleton states + `hx-trigger="revealed"` section lazy-load.
- [ ] 2.5 Acceptance: check-in round trip feels instant (< 100 ms perceived); home LCP ≤ 2.0 s on throttled 4G.

### Phase 3 — Upcoming segment
- [ ] 3.1 Backend: view/partial exposing upcoming events for the user's tracked media, grouped by date buckets (reuse `events` app).
- [ ] 3.2 Countdown cards (list) with date pills, PREMIERE/FINALE badges, expandable episode accordion.
- [ ] 3.3 Upcoming grid view with day-count overlays.
- [ ] 3.4 Segmented Watchlist ⇄ Upcoming tabs with swipe (scroll-snap) + HTMX prefetch of the inactive tab.

### Phase 4 — Remaining screens restyle
- [ ] 4.1 Media list: apply poster/episode cards, filter UI as bottom sheet.
- [ ] 4.2 Search/Discover: sticky search field, source/type chips, card results.
- [ ] 4.3 Media & season details: hero backdrop, tracking controls as bottom sheet, episode checklist rows.
- [ ] 4.4 Calendar, statistics, lists, settings: token + component sweep.
- [ ] 4.5 Remove dead CSS/templates from old layout.

### Phase 5 — PWA hardening
- [ ] 5.1 Service worker rewrite (precache + runtime strategies + versioned invalidation + offline page).
- [ ] 5.2 Image pipeline: native lazy-load, srcset, fetchpriority; drop lazysizes.
- [ ] 5.3 Manifest polish + install prompt affordance ("Add to home screen" hint in Profile).
- [ ] 5.4 (Stretch) Offline check-in queue with Background Sync.
- [ ] 5.5 Acceptance: Lighthouse PWA installable, Performance ≥ 90 mobile, app opens instantly from home screen with cached shell offline.

### Phase 6 — QA & release
- [ ] 6.1 Cross-device pass (iOS Safari standalone quirks: safe areas, `100dvh`, no pull-to-refresh conflicts; Android Chrome).
- [ ] 6.2 Template test-suite updates (`pytest` covers views/templates today — keep green each phase).
- [ ] 6.3 Before/after metrics vs Phase 0 baseline; screenshots for README/manifest.

## 7. Open questions (for upcoming reference material)

1. **Accent palette** — adopt TV Time-style yellow progress accents, or keep Yamtrack indigo? (Plan assumes both themes tokenized, so this is a one-line change.)
2. **Bottom tab set** — proposed Shows / Movies / Discover / Profile. Yamtrack tracks 8 media types; confirm which get top-level tabs vs living under Profile/lists.
3. **Upcoming scope** — tracked media only (TV Time behavior) or all calendar events?
4. **Light theme** — ship in phase 0–1 or defer? TV Time reference is light; Yamtrack userbase may expect dark default.
5. Additional screenshots to come — details, discover, and profile screens will refine Phase 4 specs.
