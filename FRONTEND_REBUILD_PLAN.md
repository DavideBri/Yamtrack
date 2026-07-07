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
| `media_card` (list) | "S05 \| E01 +7 · Soda" episode cards; movie cards (IMG_7936) | Landscape still/backdrop left, **large circular check button** right, swappable middle: episodes get show-name pill + `SXX \| EYY (+n)` + episode title; movies get title + `runtime • genres`. Check = `episode_save`/`media_save` via HTMX, optimistic UI (fills green instantly, reverts on error) |
| `countdown_card` | "44 GIORNI" upcoming cards | Same anatomy but right side shows big day-count; PREMIERE/FINALE badges; expandable "N episodes" accordion |
| `poster_card` | Grid view | 2:3 poster, 3-col mobile grid; bottom progress bar (existing `progress_bar.html` restyled) for episodic media, **no bar for movies** (IMG_7935); day-count overlay in upcoming variant |
| `empty_state` | Empty Upcoming films (IMG_7937) | Big headline, illustration, one-line hint, single **yellow pill CTA** routing to discover/browse. Reused for every empty list/section |
| `shelf` | Profile "Serie / Preferite / Film" rows (IMG_7940) | Horizontal scroll-snap poster row with section header + chevron "see all" link |
| `stat_tile` | Profile "Tempo serie / Episodi visti" (IMG_7939) | Big-numeral tiles (months/days/hours, counts); tap-through to full statistics page |
| `stat_card` | Statistics page (IMG_7943–7947) | Card stack, three variants: **big-number** (huge numeral + unit words + "N in the last 7 days" delta line), **bar chart** (weekly hours/episodes, axis labels, period caption), **ranked table** (label column + value column: genres, networks, top scores). Cards can pair number⇄chart as a swipeable 2-page carousel (scroll-snap) with dot indicators (yellow active dot), optional footer ("ALL TIME" period, compare link) |
| `section_pill` | "GUARDA IL PROSSIMO" headers | Centered gray pill section separators |
| `view_toggle` | Grid icon top-right | List ⇄ grid per section, persisted per user (existing `layout` param on media_list — extend to home) |
| `bottom_sheet` | — | Replace desktop-style modals (track modal, history modal) with bottom sheets on mobile, drag-to-dismiss (Alpine + CSS transforms) |
| `badge` | PREMIERE / ULTIMO | Black pill badges on cards |
| `detail_sheet` | Episode detail (IMG_7953–7955) | Full-height sheet: chevron-down to dismiss, **horizontal pager between episodes** of the season (dot indicators, yellow active), sticky mini-header ("Show S05 \| E06") once scrolled past the hero |
| `meta_row` | Detail screens | Calendar icon + air/release date, eye icon + watched date (or "Not watched"), big check circle right (gray → green), one-tap toggle |
| `provider_pills` | "Dove guardare" | Horizontal scroll of streaming-provider pills (logo + name) from TMDB `watch/providers` (already fetched); gear icon → region picker |
| `trailer_card` | "Guarda il trailer 02:25" | Thumbnail + play overlay + duration, links out to YouTube (needs `videos` append in TMDB provider) |
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
| Film Watchlist grid (IMG_7935) | Movies tab (medialist movie) | 3-col poster grid under "Watch next" pill; view toggle top-right |
| Film Watchlist list (IMG_7936) | Movies tab | `media_card` movie variant: title, `runtime • genres`, check circle (one-tap mark completed) |
| Film Upcoming empty (IMG_7937) | Movies tab → Upcoming segment | `empty_state` component with yellow "Browse all movies" CTA → discover |
| Profile (IMG_7939/7940) | New Profile hub page | Hero backdrop header (avatar, username, edit pill, notification bell, ⋯ menu → settings), stat tiles pulling from existing `statistics` view (time watched, episodes seen), Lists section with create-card (existing `lists` app), horizontal shelves: per-media-type "recently active" + favorites. Chevrons deep-link to statistics, lists, and medialists |
| Statistics (IMG_7943–7947) | Statistics page rebuild | Back-chevron header + per-media-type segmented tabs (Serie/Film → all tracked types). Card stack of `stat_card`s — see §4.1 for the card inventory and backend gaps |
| Bottom nav | Global | New `base.html` layout |

Media details, season details, search, lists, calendar and settings are
**restyled with the same component library** (cards, sheets, pills) but keep
their current information architecture.

### 4.1 Statistics page — card inventory (TV Time → Yamtrack)

Yamtrack already computes: activity heatmap, media-type/status/score
distributions, top rated, timeline, streaks, day-of-week stats
(`app/statistics.py`). The TV Time layout reorganizes this into a **per-media-
type card stack** and adds a few aggregates we don't have yet:

| TV Time card | Yamtrack source | Gap |
|---|---|---|
| Time spent watching (3 mesi 23 giorni 19 ore + 7-day delta) + weekly hours bar chart (carousel pair) | — | **New**: needs runtime aggregation over watched episodes/media |
| Total episodes watched (4.532 + 7-day delta) + weekly episodes bar chart | `Episode` rows + history timestamps | New aggregate, data already present |
| Biggest binges (show / episodes / hours table) | History timestamps | New aggregate: max episodes of one show within a day |
| Series added (91, "17 still in production") | Media rows + provider status | Count exists; "in production" needs persisted status metadata |
| Top genres table | Provider details (render-time only) | **Backend gap** (see below) |
| Top networks/streaming services table | Provider details (render-time only) | **Backend gap** (see below) |
| Ratings given (474 on 68 series) + most-given per show | `Media.score` | Adapt: TV Time uses "Wow" reactions; we show score counts + avg/mode per show |
| Character votes / comments / likes received | — | **Omit** — no social graph. Keep notes count as the nearest concept (optional card) |

**Backend gap — persisted metadata**: `Item` stores only
id/source/type/title/image. Genres, runtime, and networks live in provider
API responses fetched at page-render time. Time-watched, top-genres, and
top-networks cards require persisting `runtime_minutes`, `genres`, and
`networks/studios` (JSON) on `Item`, populated on save and backfilled through
the existing `sync_metadata` task machinery. This is the one schema change in
the whole plan — worth doing early (Phase 0) so data accumulates.

**Chart rendering**: these are simple weekly bar charts — render as inline
SVG in templates (server-side values, no JS) instead of loading Chart.js on
mobile stats. Keep Chart.js only where genuinely interactive (or drop it in
Phase 5 if the SVG approach covers everything).

### 4.2 Detail screens (IMG_7953–7958)

**Episode detail** — today this lives inside the season page + track modal;
it becomes a `detail_sheet` opened from any episode row/card:

| TV Time element | Yamtrack mapping |
|---|---|
| Hero still, `S05 \| E08` + title overlay, show-name pill → show page, share icon | Season/episode metadata (already fetched); share = Web Share API with canonical URL |
| Meta row: air date · watched state · check circle | `Episode.end_date` + calendar data; check = `episode_save` (unwatch on re-tap), same optimistic pattern as cards |
| Swipe between episodes + dot pager | Episodes of the current season, server-rendered pages loaded lazily via HTMX on swipe |
| "Dove guardare" provider pills | TMDB `watch/providers` — **already in provider payloads**, just needs rendering + region setting (gear) |
| Episode info: community stars + synopsis | TMDB episode rating/overview |
| Rate-this-episode stars, "where did you watch it?" picker, emoji reactions, favorite character, comments | **Omit** — community/social features. Optional stretch: per-episode score (would need a `score` field on `Episode`; today scores exist only at media/season level) — logged as open question |

**Movie / media detail** (IMG_7957–7958) — full-page route, restyled:

| TV Time element | Yamtrack mapping |
|---|---|
| Hero backdrop, title + `runtime • genres` overlay, collapsing sticky header, ⋯ menu | Existing details data; ⋯ menu hosts edit/delete/history (today's track-modal actions) |
| Meta row: release date · watched date · green check | `Media` dates + one-tap `media_save` status toggle |
| INFO \| ALTRO segmented tabs | INFO = providers, synopsis, trailer, cast, related; ALTRO = your tracking (history, notes, repeats, score) |
| "Dove guardare" pills | As above — render already-fetched `providers` data |
| "What interests you most?" survey | **Omit** (TV Time data collection) |
| Trailer card | Add `videos` to TMDB append list (one-line provider change) + `trailer_card` |
| "34 hanno aggiunto questo film" | Count of users on this instance tracking the item — cheap aggregate, nice multi-user touch |
| Cast shelf | Already rendered (`cast_card`) — restyle as `shelf` |
| "Gli altri hanno visto anche" | Existing `related`/recommendations section — restyle as `shelf` |

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
- [ ] 0.4 Schema: add persisted metadata to `Item` (`runtime_minutes`, `genres`, `networks` JSON) + populate on save + backfill via `sync_metadata` task. Do this first so watch-time/genre/network stats (§4.1) have data by the time Phase 5 ships.

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

### Phase 4 — Movies tab & Profile hub
- [ ] 4.1 Movies tab: Watchlist segment as medialist (movie) with list/grid variants of `media_card`/`poster_card`; one-tap complete via `media_save`.
- [ ] 4.2 Movies Upcoming segment (calendar events, movie type) + `empty_state` with yellow browse CTA; roll `empty_state` out to all lists/sections.
- [ ] 4.3 Profile hub page: hero header (avatar/backdrop from user settings), stat tiles fed by `app/statistics.py` aggregates, Lists section (create-card + shelf), horizontal `shelf` rows per media type + favorites; ⋯ menu → settings, bell → upcoming/notifications.
- [ ] 4.4 Acceptance: Profile stat tiles match statistics page numbers; shelves are scroll-snap, 60 fps, images lazy beyond first three.

### Phase 5 — Remaining screens restyle
- [ ] 5.1 Media list (other types): apply poster/episode cards, filter UI as bottom sheet.
- [ ] 5.2 Search/Discover: sticky search field, source/type chips, card results.
- [ ] 5.3 Media details rebuild (§4.2): hero backdrop + collapsing header, meta row with one-tap check, INFO/ALTRO tabs, provider pills (render existing `watch/providers` data + region setting), trailer card (add `videos` append to TMDB provider), "N users track this" count, cast/related as shelves; ⋯ menu absorbs track-modal actions.
- [ ] 5.3b Episode `detail_sheet` (§4.2): sheet with episode pager (HTMX lazy pages), meta row + check, provider pills, synopsis/rating; season page episode rows open it. Season details page restyled to match.
- [ ] 5.4 Statistics rebuild (§4.1): per-media-type segmented tabs; `stat_card` stack — time watched (+7-day delta, weekly hours chart), episodes watched (+delta, weekly chart), biggest binges, added counts, top genres, top networks, scores given; number⇄chart swipe carousels; inline-SVG charts, Chart.js removed from this page. Backend: new aggregates in `app/statistics.py` reading the Phase 0 metadata.
- [ ] 5.5 Calendar, lists, settings: token + component sweep.
- [ ] 5.6 Remove dead CSS/templates from old layout.

### Phase 6 — PWA hardening
- [ ] 6.1 Service worker rewrite (precache + runtime strategies + versioned invalidation + offline page).
- [ ] 6.2 Image pipeline: native lazy-load, srcset, fetchpriority; drop lazysizes.
- [ ] 6.3 Manifest polish + install prompt affordance ("Add to home screen" hint in Profile).
- [ ] 6.4 (Stretch) Offline check-in queue with Background Sync.
- [ ] 6.5 Acceptance: Lighthouse PWA installable, Performance ≥ 90 mobile, app opens instantly from home screen with cached shell offline.

### Phase 7 — QA & release
- [ ] 7.1 Cross-device pass (iOS Safari standalone quirks: safe areas, `100dvh`, no pull-to-refresh conflicts; Android Chrome).
- [ ] 7.2 Template test-suite updates (`pytest` covers views/templates today — keep green each phase).
- [ ] 7.3 Before/after metrics vs Phase 0 baseline; screenshots for README/manifest.

## 7. Resolved by reference screenshots (batch 2)

- **Movies is a top-level tab** with the same Watchlist/Upcoming segments as Shows (IMG_7935–7937); movie cards show `runtime • genres`, no progress bars in grid.
- **Yellow is the primary-action accent** (CTA pill, notification bell) in addition to progress bars — tokenized as `--color-accent`.
- **Profile is a hub screen** (IMG_7939/7940): hero header, stat tiles, lists, horizontal shelves; statistics/lists/settings hang off it. This resolves where secondary nav lives.
- **Empty states** are a first-class pattern: headline + illustration + hint + single yellow CTA.
- **Statistics** (batch 3, IMG_7943–7947) is a per-media-type card stack: big-number cards with 7-day deltas, weekly bar charts, ranked tables (genres, networks, scores), swipeable number⇄chart carousels. Mapped card-by-card in §4.1; requires the Phase 0 `Item` metadata schema change. Social cards (character votes, comments, likes) are omitted — no social graph in Yamtrack.
- **Detail screens** (batch 4, IMG_7953–7958, mapped in §4.2): episode detail is a swipeable sheet with per-episode pager; movie detail is a full page with hero, INFO/ALTRO tabs, trailer, cast and recommendations shelves. TMDB provider **already fetches** cast, recommendations, and `watch/providers` — "Dove guardare" is render-only work; trailer needs a one-line `videos` append. Ratings/reactions/favorite-character/comments per episode are omitted (social features).

## 8. Open questions (for upcoming reference material)

1. **Accent palette** — go full TV Time yellow, or keep Yamtrack indigo for actions and use yellow only for progress? (Tokenized either way — one-line change.)
2. **Remaining 6 media types** (anime, manga, games, books, comics, boardgames) — fold into Shows/Movies tabs by "episodic vs one-shot", give Profile shelves only, or a configurable tab? Current sidebar is per-type and user-configurable (`get_sidebar_media_types`).
3. **Upcoming scope** — tracked media only (TV Time behavior) or all calendar events?
4. **Light theme** — ship in phase 0–1 or defer? TV Time reference is light; Yamtrack userbase may expect dark default.
5. **Social row** (following/followers/comments on Profile) — Yamtrack has no follow graph; list collaborators are the closest concept. Omit, or show lists/collaborators counts instead?
6. **Per-episode ratings** — TV Time rates each episode (stars). Yamtrack scores only media/seasons; adding `Episode.score` is a small schema change but a real feature decision. In scope?
7. Screenshots still welcome: Discover/Esplora tab and notifications are the only screens left without a reference.
