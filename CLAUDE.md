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
on the site (~33 kB gzipped); everything else ships zero JS.

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
public/data/              runtime copies of islands.geojson + land-110m.json
scripts/                  seed_islands.py, build_geojson.py
```

Metadata and geometry are deliberately separate files: editing a story can
never corrupt a shape, and the map loads geometry without pulling in prose.

## Decisions already made — don't relitigate

- **No Leaflet / MapLibre.** D3 + inline SVG + Natural Earth 110m TopoJSON.
  No tile server, full control of every colour.
- **Van der Grinten projection** (`d3-geo-projection`). Chosen for thematic
  reasons: a project about cartographic error deserves a projection with
  visible historical personality. Fitted to a −62°..84° latitude band so
  Antarctica falls outside the viewBox — every Southern Ocean phantom is
  above −60, so nothing is lost.
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

**`public/data/islands.geojson` is a copy.** The map fetches it at runtime from
`public/`, not from `src/data/`. Regenerating geometry without copying it
across is a silent no-op. Worth wiring into an npm script.

**The map sets `opacity: 0` until it mounts.** A thrown error leaves an
invisible-but-present container, which looks identical to nothing happening.
Check the console before assuming the component didn't render.

**Placeholder blobs shrink above 60° latitude** — otherwise Van der Grinten
stretches Crocker Land (83°N) into a scar across the Arctic.

## Design

```css
--water: #EDEFF0;  --land: #383D40;  --phantom: #74202F;
--phantom-soft: #B08089;  --ink: #16191B;  --rule: #C7CCCF;
```

Display face is **Faune** (Alice Savoie / CNAP, free) — a French typeface drawn
from natural-history illustration, commissioned for the Muséum national
d'Histoire naturelle. A face for cataloguing specimens, on a catalogue of
specimens nobody collected. **Not on Google Fonts**; woff2 files go in
`public/fonts/`, and it falls back to Spectral until they're added. Body text
is Spectral (Production Type — real small caps, proper French spacing).

Signature element: every island gets a **lifespan** on hover — `1906 – 1914`.
Repeated across the map, the site reads as a necrology, which is a more
interesting object than a clickable index.

## Current state

- 34 islands with coordinates; 9 attested, 12 approximate, 10 conjectural
- 3 stories seeded (`hy-brasil` fr+en, `crocker-land` fr) — Hy-Brasil is the
  only one with real prose; the rest are placeholders
- 2 partial drafts (`nakanotorishima`, `nimrod`) with notices and map images
- All geometry is placeholder blobs
- Map verified working: hover, tap-to-reveal on touch, zoom to 8×, reset

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
5. Faune woff2 files.
6. Domain, then Cloudflare Pages (`npm run build`, output `dist`).

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
