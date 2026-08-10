# Atlas des îles fantômes — build plan (HISTORICAL)

> **Status: superseded. Kept as a record of the original thinking, not as a
> specification.** Written 7 August 2026, before any of it was built.
>
> **Read [`CLAUDE.md`](./CLAUDE.md) and [`README.md`](./README.md) instead** —
> those describe the site as it actually is.
>
> Decisions below that were later overturned, all after building and comparing
> the alternatives:
>
> | This document says | Actually |
> |---|---|
> | Van der Grinten projection | An orthographic **globe**; dragging rotates it |
> | Natural Earth **110m** basemap | **50m** — 110m contains no small islands at all |
> | Display face **Faune** | **Spectral throughout**; Faune's upright is a sans |
> | Hosting: Cloudflare Pages or Netlify | **Vercel**, live and auto-deploying |
> | Fitted to a −62°..84° latitude band | No band; the globe reaches both poles |
>
> What it still gets right, and why it's worth keeping: the content model
> (metadata separate from geometry, many-to-many stories, the open-ended
> `notice` array), the slug decision, and the observation that the real work is
> drawing 50 island polygons rather than building the site.

A bilingual literary atlas: a world map of islands that were believed to exist and
did not, each linking to a short story. 28 stories written, 50 planned.

---

## 1. Decisions already made

| Question | Decision |
|---|---|
| Domain | New domain, TBD. Not decided yet, doesn't block the build. |
| Old blog (`etiennefd.com/cteniq`) | Stays online, untouched. No redirects needed. |
| Migration | Manual, done by hand once the content structure exists. No importer to build. |
| Slugs | One canonical French slug per island, shared across both languages. |
| Launch scope | The 28 written stories + Thule as a single "planned" test case. Remaining islands added over time. |
| Map style | Dark gray land, light gray water, burgundy phantom islands. |

## 2. Stack

- **Astro** — static output, built-in i18n routing, typed content collections. Only the
  map component ships JavaScript.
- **D3** (`d3-geo`, `d3-geo-projection`, `d3-zoom`, `d3-delaunay`, `topojson-client`)
  rendering to inline SVG. No Leaflet, no MapLibre, no tile server.
- **Natural Earth 110m land** as TopoJSON (~100 KB) for the basemap.
- **Hosting:** Cloudflare Pages or Netlify. Static, free.

Total JS budget for the map: under 60 KB gzipped if the D3 imports stay granular
(import from submodules, never `import * from "d3"`).

## 3. Repository structure

```
src/
  content/
    islands/            # one YAML/JSON per island — metadata only
      hy-brasil.yaml
      thule.yaml
    stories/
      fr/hy-brasil.md
      en/hy-brasil.md
  data/
    islands.geojson     # geometry only, keyed by island id
    land-110m.json      # Natural Earth basemap
  components/
    PhantomMap.astro    # wrapper, no JS
    map.ts              # the D3 client island
  pages/
    [lang]/index.astro          # map
    [lang]/liste.astro          # plain text index (accessibility + SEO)
    [lang]/iles/[slug].astro    # story page
    [lang]/a-propos.astro
```

Geometry lives in GeoJSON; everything else lives in the content collection. Keeping
them apart means editing a story never risks corrupting a shape, and the map can load
geometry without pulling in story bodies.

## 4. Data model

### Island (`src/content/islands/{id}.yaml`)

Metadata only. Filename is the id (canonical French slug).

```yaml
name_fr: L'île de Hy-Brasil
name_en: The Island of Hy-Brasil
kind: island              # island | reef | misdrawn
ocean: atlantique-nord
coords: [-15.0, 51.5]     # [lon, lat]
span: [1325, 1865]        # optional, lossy — see below
span_qualifier: vers      # optional
```

`kind` drives rendering:

- **island** — filled burgundy polygon.
- **reef** — a point. Small filled dot, always haloed.
- **misdrawn** — a real place wrongly charted (Corée, Californie). Burgundy
  outline, no fill, so the true coastline shows through. The clearest statement
  of the project's thesis; deserves its own treatment.

### Story (`src/content/stories/{lang}/{slug}.md`)

```yaml
title: L'île de Hy-Brasil
islands: [hy-brasil]        # array — see below
date: 2020-05-31
source: https://etiennefd.com/cteniq/ile-de-hy-brasil/
images:
  - src: /iles/hy-brasil-atlas-catalan.png
    caption: Détails de l'« [atlas catalan](...) » de Cresques Abraham (1375).
notice:
  - label: Où
    body: à l'ouest de l'Irlande
  - label: Quand
    body: apparaît sur les cartes à partir de 1325... la dernière mention
          serait apparemment en 1865, sous le nom de Brasil Rock.
  - label: Pourrait être
    body: le [banc de Porcupine](...), une montagne sous-marine
```

**The notice is an ordered array of `{label, body}`, not fixed fields.** Labels
vary per island and are invented as needed; bodies are markdown and range from
three words to a full paragraph with links and emphasis. Rendering is a
definition list. Fixed keys like `first_recorded` would destroy entries such as
"la dernière mention serait *apparemment* en 1865" — the hedging is the content.

**`span` is a lossy convenience for the map hover only.** Two numbers, either
nullable for an open interval, omitted entirely when the dating is too contested
to reduce. The prose in `notice` is always authoritative.

**Stories are many-to-many with islands.** Three of the 28 existing posts cover
more than one island. Availability is derived at build time: *does any story in
this language list my id?* Two burgundy shapes, both clickable, both landing on
the same page.

### Island states, resolved at build time

| State | Condition | Rendering |
|---|---|---|
| `available` | story exists in current language | solid burgundy, label on hover |
| `translated` | story exists only in the other language | burgundy outline; cross-language note on the page |
| `planned` | no story in any language | thin dusty-rose ring, label reads *à venir* / *forthcoming* |

## 5. Island inventory

31 island entities across the 28 written stories, plus Thule as the planned-state test.

**Coordinates are not filled in yet** — that's a separate research pass and I'd rather
leave them blank than guess. Everything else here is ready to seed.

| id | name (fr) | kind | story slug |
|---|---|---|---|
| tuanaki | Tuanaki | island | tuanaki |
| zanara | Zanara | island | zanara |
| mayda | Mayda | island | mayda |
| saint-mathieu | L'île Saint-Mathieu | island | saint-mathieu |
| maria-de-lajara | L'île María de Lajara | island | maria-de-lajara |
| los-jardines | Los Jardines | island | los-jardines |
| ile-aux-vaches | L'île aux Vaches | island | ile-aux-vaches |
| kianida | Kianida | island | kianida |
| juan-de-lisboa | Juan de Lisboa | island | juan-de-lisboa |
| dos-romeiros | Dos Romeiros | island | juan-de-lisboa |
| jacquet | L'île Jacquet | island | jacquet |
| hy-brasil | Hy-Brasil | island | hy-brasil |
| groclant | Groclant | island | groclant |
| frisland | Frisland | island | frisland |
| ernest-legouve | Récif Ernest-Legouvé | reef | recifs |
| maria-theresa | Récif Maria-Theresa | reef | recifs |
| emerald | L'île Emerald | island | emerald |
| elizabeth | L'île Elizabeth | island | elizabeth |
| dougherty | L'île de Dougherty | island | dougherty |
| ile-des-demons | L'île des Démons | island | ile-des-demons |
| terre-de-davis | La Terre de Davis | island | terre-de-davis |
| crocker-land | Crocker Land | island | crocker-land |
| bradley-land | Bradley Land | island | crocker-land |
| coree | La Corée | misdrawn | coree |
| californie | L'île de Californie | misdrawn | californie |
| buss | L'île Buss | island | buss |
| saint-brendan | L'île de Saint-Brendan | island | saint-brendan |
| bermeja | L'île de Bermeja | island | bermeja |
| bacalao | Bacalao | island | bacalao |
| aurora | Les îles Aurora | island | aurora |
| antillia | Antillia | island | antillia |
| thule | Thulé | island | *(planned — no story)* |

The reefs post mentions "quelques autres objets fantômes de la même région" — check
whether any of those deserve their own entries.

## 6. The map component

### Projection

**Van der Grinten** (`geoVanDerGrinten` from `d3-geo-projection`). Rounded, with the
visible personality of a 1900s atlas plate — appropriate for a project about
cartographic error. Equal Earth is the sober alternative if Van der Grinten's polar
distortion proves distracting once the Arctic islands are placed.

Clip the top and bottom so Antarctica doesn't run away.

### Zoom and pan

```js
d3.zoom()
  .scaleExtent([1, 8])
  .translateExtent(/* recomputed on resize */)
```

- 8× maximum: enough to separate the crowded North Atlantic cluster, not enough to
  invite anyone to look for detail that doesn't exist.
- Zoom applies as a transform on a `<g>`. Do **not** re-project on zoom.
- Counter-scale anything that should stay visually constant: `vector-effect:
  non-scaling-stroke` on all paths, halo radius as `base / k`.
- Wheel, pinch, and double-tap all zoom. Include a discreet reset control.
- Respect `prefers-reduced-motion` on the zoom transition.

### Hit-testing

Islands are a few pixels wide at world scale, so pointer targets can't be the shapes
themselves.

Build a `d3-delaunay` Voronoi over island label anchors in **screen space**. On
`mousemove`, `delaunay.find(x, y)` returns the nearest island in O(1). Apply a ~60 px
distance cutoff so hovering over Kazakhstan doesn't light up Sannikov Land.

Rebuild the Voronoi on `zoom.on("end")` and on resize — never per frame.

### Halos

Systematic, not hand-tuned. Each frame, compute the island's projected bounding-box
diagonal in screen pixels. If under ~14 px, draw a halo:

```
r = max(diagonal * 3, 10) / k
```

Halos therefore appear and vanish automatically with zoom: rings at world view,
gone once the shape can speak for itself. Frisland never gets one; Dougherty always
does. On hover, the **ring** animates — a slight expansion and opacity lift — not
the island.

### Labels

Absolutely positioned HTML over the SVG, not `<text>`. Real typography, no SVG text
pain. Project the anchor, position a div, done.

**Set island labels in italic.** Cartographic convention puts hydrography in italic
and land in roman. Setting every phantom island in italic quietly says: this is water.
It's the cheapest and best joke on the site.

### Mobile

- First tap reveals the label; second tap navigates. Tapping empty water dismisses.
- The Voronoi cutoff widens to ~44 px on coarse pointers.
- A plain list page (`/liste`) is a first-class route, not a fallback: all islands,
  bilingual, with dates and one-line descriptions. Probably how a third of readers
  will actually browse.

## 7. Visual design

The brief fixes the map palette. These tokens extend it without arguing with it.

```css
--water:        #EDEFF0;  /* page background and ocean — one surface */
--land:         #383D40;
--phantom:      #74202F;  /* burgundy */
--phantom-soft: #B08089;  /* planned-state rings */
--ink:          #16191B;
--rule:         #C7CCCF;  /* hairlines */
```

The page background *is* the ocean. No panel chrome floating on top of the map — the
story page should feel like a continuation of the same sheet of paper.

### Type

- **Display: Faune** (Alice Savoie / CNAP, free). A French face commissioned for the
  Muséum national d'Histoire naturelle, drawn from natural-history illustration. A
  typeface for cataloguing specimens, used on a catalogue of specimens that were never
  collected. Used with restraint: island names, story titles.
- **Body: Spectral** (Production Type). Built for screen reading, real italics, real
  small caps, and proper French support including the spacing around « » and : .
- **Utility: Spectral small caps** for map labels, dates, and the counter. No third
  family.

### Signature element

Every island gets a **lifespan**. On hover: the name, then the years — `1906 – 1914`.
An island that appeared on charts for eight years and then stopped. Repeated across
the map, the site reads as a necrology, which is a more interesting thing to have made
than a clickable map.

Islands never formally struck from charts get an open interval: `1325 –`. Planned
islands get the name and `à venir`.

The `28 / 50` counter sits quietly in a corner, small caps. It goes up.

## 8. Story page

Single column, generous measure (~68 characters), no sidebar. Above the story:

- Island name, display face.
- The lifespan, small caps.
- A small inset map — the same projection, zoomed to the island, showing it in
  burgundy against the surrounding real coastlines. Same component, different
  parameters. Reinforces where you are without a breadcrumb.

Below the story: sources, if any; the language switch; previous/next by the island's
`first_recorded` year rather than by publication date, so browsing the atlas walks
chronologically through the history of the error.

For `translated`-state islands, a single quiet line above the fold: *Cette histoire
n'existe qu'en français pour l'instant* — with the link, not an apology.

## 9. Internationalisation

- Routes: `/fr/...` and `/en/...`. French is the default locale; `/` redirects to `/fr`.
- Slugs stay French in both trees: `/en/islands/ile-des-demons`. One slug, no lookup
  table, language switch is always a string swap.
- UI strings in a small `ui.ts` dictionary — there are maybe thirty of them.
- `hreflang` pairs on every story that exists in both languages.

## 10. Build order

1. **Astro skeleton** — i18n routing, both locales, empty pages, tokens and type in place.
2. **Content collections** — schemas for islands and stories, with Zod validation. Seed
   with three islands by hand (Hy-Brasil, Crocker Land + Bradley Land to exercise the
   many-to-many case, Thule for the planned state).
3. **Story page** — get it looking right with real text before touching the map. This is
   where readers spend their time.
4. **List page** — trivial once collections exist, and it makes the site usable end to
   end early.
5. **Static map** — basemap, projection, islands rendered from GeoJSON with placeholder
   circular shapes. No interaction yet.
6. **Interaction** — Voronoi hit-testing, hover labels, halos, click-through.
7. **Zoom and pan** — including all the counter-scaling.
8. **Mobile pass** — tap states, wider cutoff, layout.
9. **Content** — migrate the 28 stories by hand.
10. **Shapes** — replace placeholder circles with traced outlines, one at a time. Ongoing,
    never blocking.

Steps 1–8 are a few focused sessions. Steps 9–10 are the actual project and have no
end date, which is correct for an atlas.

## 11. Open items

- **Coordinates for all 31 islands.** Needs a sourced pass. Position matters much more
  than shape — a wrong position is an error, a rough outline is just provisional.
- **Domain.**
- **Placeholder shape strategy.** Simplest is a circle scaled to the island's reputed
  size. Slightly better: a small library of four or five generic island silhouettes
  rotated randomly per island, so the map doesn't read as a dot-density plot before the
  real tracing is done.
- **English titles** for the islands that don't have obvious ones (Île aux Vaches,
  Kianida, Zanara).
- **Tracing workflow** — QGIS with georeferenced historical rasters for the serious ones,
  geojson.io for the quick ones. Worth documenting once, in this file, after the first
  three.
- **Does the reefs post split** into separate island entries, or stay as one story
  covering a region?
