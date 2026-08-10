# Atlas des îles fantômes

A bilingual literary atlas: a world map of islands that were believed to exist
and did not, each linking to a short story. Fiction, not reference — the
stories are the point; the cartography is the frame.

Written by Étienne Fortier-Dubois. Stories originate on his French blog at
`etiennefd.com/cteniq` (WordPress, staying online, not being migrated away).
28 stories written of ~50 planned.

## Commands

```sh
npm run dev        # localhost:4321, redirects to /fr/
npm run build
npm run preview

python3 scripts/build_geojson.py                    # regenerate island geometry
cp src/data/islands.geojson public/data/islands.geojson   # ← required, see below
```

## Architecture

Astro 5, static output, French default locale. The map is the only JavaScript
on the site (~35 kB gzipped); everything else ships zero JS.

```
src/
  content.config.ts       Zod schemas for both collections
  content/islands/*.yaml  one file per island — metadata, no prose, no geometry
  content/stories/{fr,en}/*.md
  data/islands.geojson    geometry, generated
  lib/atlas.ts            resolves island states, formats lifespans
  components/map.ts       the D3 map
  components/PhantomMap.astro
  i18n/ui.ts              ~30 UI strings
  pages/[lang]/{index,liste}.astro, pages/[lang]/iles/[slug].astro
public/data/              runtime copies of islands.geojson + land-50m.json
scripts/                  seed_islands.py, build_geojson.py
```

Metadata and geometry are deliberately separate files: editing a story can
never corrupt a shape, and the map loads geometry without pulling in prose.

## Decisions already made — don't relitigate

- **No Leaflet / MapLibre.** D3 + inline SVG + Natural Earth TopoJSON (50m —
  see Traps). No tile server, full control of every colour.
- **An orthographic globe** (`d3-geo`), not a flat projection. This replaced
  Van der Grinten in August 2026 after building both and comparing them side
  by side. Van der Grinten was chosen for thematic reasons — a project about
  cartographic error deserves a projection with visible historical
  personality — and it did look the part, but the globe won on capability:
  it reaches views a fitted flat map cannot. Centring on Antarctica shows
  nine Southern Ocean phantoms at once (Aurora, Dougherty, Elizabeth,
  Emerald, Nimrod, Davis Land, Tuanaki, Ernest-Legouvé, Maria-Theresa); the
  old −62°..84° fit crushed every one of them against the bottom crop. Same
  for the Arctic cluster. Dragging rotates, so there is no edge in any
  direction.

  Known cost, accepted: a globe shows one hemisphere, so about half the
  atlas is behind the earth at any moment (19 of 34 visible at the home
  view). The `liste` page remains the complete index.

  The Van der Grinten implementation is in git history at `170475b` if this
  is ever revisited.
- **One canonical French slug per island**, used in both language trees:
  `/en/iles/ile-des-demons`. No slug lookup table.
- **Stories are many-to-many with islands.** Three existing posts cover more
  than one island (`crocker-land` + `bradley-land`, `juan-de-lisboa` +
  `dos-romeiros`, and the reefs post). Availability is derived at build time.
- **Island names render in italic** on the map. Cartographic convention sets
  hydrography in italic — so italicising the phantoms quietly says "this is
  water." Keep it.
- **The page background is the ocean.** No panel chrome floating over the map.

## Data model

### Island (`src/content/islands/{id}.yaml`)

Filename is the id. `kind` drives rendering:

- `island` — filled burgundy polygon
- `reef` — a Point; small dot, always haloed
- `misdrawn` — a *real place wrongly charted* (Corée, Californie). Outline
  only, no fill, so the true coastline shows through underneath. This is the
  clearest visual statement of the project's thesis.

`coords_confidence` is one of `attested | approximate | conjectural | unknown`,
with `coords_note` recording provenance. **Ten islands are `conjectural`** —
positions I inferred from context. Don't silently "correct" them; flag
uncertainty to Étienne rather than guessing harder. Full table in
`COORDINATES.md`.

`span` is a lossy `[start, end]` pair used **only** for the map hover label.
Either element may be null for an open interval. Omit it entirely where dating
is too contested to reduce to two numbers. The authoritative account always
lives in the story's `notice`.

### Story (`src/content/stories/{lang}/{slug}.md`)

Language is derived from the path, not a frontmatter field.

`notice` is an **ordered array of `{label, body}`**, not fixed fields. Labels
vary per island and are invented freely (*Où*, *Quand*, *Aussi connue sous le
nom de*, *Pourrait être*, *À ne pas confondre avec*, *Inventée par*…). Bodies
are markdown — links and emphasis are expected and rendered inline. Fixed keys
would destroy entries like "la dernière mention serait *apparemment* en 1865";
the hedging is the content.

`draft: true` keeps the notice and images live while leaving the island
`planned` on the map. Used for partial drafts (currently `nakanotorishima`,
`nimrod`).

### Island states, resolved in `lib/atlas.ts`

| state | condition | rendering |
|---|---|---|
| `available` | non-draft story in the current language | solid burgundy |
| `translated` | story only in the other language | burgundy outline, cross-language note on the page |
| `planned` | no story, or draft only | dashed dusty-rose ring, label reads *à venir* |

## Traps

**d3-geo reads polygons spherically.** An exterior ring wound the wrong way
renders as *the whole planet except that island* — a solid burgundy disc over
the entire map. `scripts/build_geojson.py` forces clockwise winding. QGIS and
geojson.io export RFC 7946 counterclockwise, so **anything traced by hand needs
flipping**. Verify with `geoArea(feature) > 2 * Math.PI` → inverted.

**The basemap is Natural Earth 50m and should stay one resolution.** 110m has
no small islands at all, which is wrong for this project; 10m runs at 9 fps
because the globe reprojects everything every frame. Both a 10m basemap and an
idle-swap scheme (coarse while moving, fine when stopped) were built and
rejected — the swap worked but was unpleasant to use. 50m holds 60 fps.

**`world-atlas`'s `land-10m.json` is broken as distributed** — 3 degenerate
zero-area polygons that d3-geo reads as the whole sphere, giving 41.3 sr of
land against a true ~2.9 and rendering the globe as a solid disc. Worth
knowing before blaming your own code.

**`public/data/islands.geojson` is a copy.** The map fetches it at runtime from
`public/`, not from `src/data/`. Regenerating geometry without copying it
across is a silent no-op. Worth wiring into an npm script.

**The map sets `opacity: 0` until it mounts.** A thrown error leaves an
invisible-but-present container, which looks identical to nothing happening.
Check the console before assuming the component didn't render.

**Placeholder blobs shrink above 60° latitude.** `build_geojson.py` divides a
blob's longitude extent by cos(latitude), floored at 0.35, so it stays roughly
circular *on the ground* rather than smearing east-west near the poles. This
is a geographic correction, not a projection workaround, so it survived the
move to the globe — but the 0.35 floor was tuned by eye against Van der
Grinten and has not been re-examined since.

**The far hemisphere must be culled explicitly.** `projection()` still returns
a point for a location behind the globe — it mirrors it onto the near disc —
so without a `geoDistance > π/2` test you can hover an island through the
earth.

## Design

```css
--water: #EDEFF0;  --land: #383D40;  --phantom: #74202F;
--phantom-soft: #B08089;  --ink: #16191B;  --rule: #C7CCCF;
```

**Spectral throughout** (Production Type — real small caps, proper French
spacing), body and display alike. `--display` is set to `var(--body)` and kept
only as the seam where a display face would go.

**A second family was tried and rejected** in August 2026 — don't re-propose
one casually. Faune (Alice Savoie / Cnap) was picked in the first design
session on an unverified premise: the notes described it as commissioned for
the Muséum national d'Histoire naturelle and as drawn from natural-history
engraving. It was in fact commissioned by the Centre national des arts
plastiques with the Imprimerie Nationale, and — decisively — its upright is a
flared humanist **sans**, not the engraved serif the story implied. Against
Spectral's serif body it read as a clash. EB Garamond, Playfair Display,
Bodoni Moda, Libre Bodoni and Theano Didot were compared on the real site;
Spectral alone won.

Two things to carry forward if it's ever revisited. A display face needs a
**real italic cut**, because map labels are italic by the hydrography
convention and a synthesised oblique looks wrong on a high-contrast face —
that ruled out Theano Didot, which ships Regular only. And verify what a face
*looks like* before writing a rationale for it: a computed `font-family` only
reports what was asked for, not what rendered, so measure against generic
serif to catch a silent fallback.

Signature element: every island gets a **lifespan** on hover — `1906 – 1914`.
Repeated across the map, the site reads as a necrology, which is a more
interesting object than a clickable index.

## Current state

**Live at <https://atlas-des-iles-fantomes.vercel.app/fr/>** — Vercel, imported
from the GitHub repo, redeploys on every push to `main`. Build `npm run build`,
output `dist`, no adapter (static). Nothing to configure.

- 34 islands with coordinates; 9 attested, 12 approximate, 10 conjectural
- 3 stories seeded (`hy-brasil` fr+en, `crocker-land` fr) — Hy-Brasil is the
  only one with real prose; the rest are placeholders
- 2 partial drafts (`nakanotorishima`, `nimrod`) with notices
- All geometry is placeholder blobs
- Map verified in production: globe mounts, 634 landmasses, 34 islands, hover,
  tap-to-reveal on touch, rotate, tilt, zoom to 8×, reset

### Known blemishes, live right now

- **Three story images 404.** `/iles/hy-brasil-atlas-catalan.png`,
  `/iles/nakanotorishima-pacifique-1941.png`, `/iles/nimrod-perthes-1906.png`
  are referenced in frontmatter and don't exist, so every story page shows a
  broken image icon — including Hy-Brasil, the one with real prose. Either add
  the files to `public/iles/` or make the template skip a figure whose file is
  missing (worth doing anyway before migrating 28 stories).
- **`/` stalls for two seconds.** `Astro.redirect` in static mode compiles to
  `<meta http-equiv="refresh" content="2;url=/fr/">`. A `vercel.json` 308 fixes
  it. Sharing the `/fr/` URL sidesteps it.
- **`site` is still `https://example.com`** in `astro.config.mjs`, and it is
  already leaking into production as `<link rel="canonical">` on the redirect
  page.

## Next, roughly in order

1. **Migrate the 28 stories** from the blog. Étienne is doing this by hand and
   wants to. Conventions: `//` scene breaks become `***` (renders as a centred
   `//` dinkus); the bullet block becomes `notice:`; keep `source:` pointing at
   the original post.
2. **Trace real outlines**, starting with `californie` (should be a long N–S
   sliver), `coree` (a peninsula) and `frisland` (the Zeno lozenge) — the three
   where a placeholder blob actively misleads. Everything else can stay a blob
   indefinitely.
3. Verify the conjectural coordinates against Étienne's own research.
4. Story-page inset map (same component, zoomed to one island).
5. A real domain (Vercel is serving `atlas-des-iles-fantomes.vercel.app`
   today; point `site` in `astro.config.mjs` at whatever it becomes).

## Open questions

- At world zoom the map is ~31 faint rings and 3 burgundy shapes. Honest, but
  possibly too quiet — the planned state may want more presence. Needs a human
  eye, not a tweak decided in isolation.
- `kianida` (Black Sea) and `zanara` (Tyrrhenian) sit in enclosed seas, which
  reads oddly on a world map framed for oceans.
- Whether the reefs post splits into separate island entries or stays one
  story covering a region.

## Working preferences

Étienne is technical and writes for *Asterisk*, *Works in Progress* and his own
Substack. Explain reasoning, flag uncertainty rather than papering over it, and
prefer showing a diff to handing over a pile of files. Verify rendering changes
by actually running them — the winding-order bug was invisible until the map
was screenshotted.
