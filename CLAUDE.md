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
- **An island's shape comes from the most famous or influential depiction**,
  not the earliest, and *not* the plate that happens to illustrate its story —
  those were picked as illustrations and Étienne does not endorse them as
  sources. For Antillia the two coincided anyway: Pizzigano 1424 is both first
  and the one everyone copied. Where they differ, influence wins.

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

`outline_note` records which depiction a traced shape came from — a *separate*
claim from the position, and frequently a different chart. Antillia's position
comes from Pizzigano 1424 and its shape from Canepa 1489. Keep them distinct;
conflating them is how the island ended up east of the Azores.

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

**The story importer must stay deterministic.** `scripts/import_posts.py`
converts HTML to markdown with regexes over the small tag subset these posts
actually use. That is deliberate: routing 47,000 words of literary prose
through a model would risk silent paraphrase. It was validated by
reconstructing Hy-Brasil and diffing against source — 51 paragraphs, 13,087
characters, byte-identical. If you extend it, keep that check.

One real trap it already handles: an asterisk used as a **footnote marker**
followed by italic text converts to `**…*`, which markdown reads as bold-open
and renders wrong (`kianida`). And Wikimedia URLs arrive already
percent-encoded, so re-encoding them turns `%2C` into `%252C` and 404s.

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

## Tracing island shapes

Worked once, on `antillia`. Read this before doing the second one.

A phantom island's shape is a claim, not a fact, so it carries provenance of
its own in `outline_note` — often citing a *different* chart from the one the
position came from.

```sh
python3 scripts/trace_outline.py antillia --chart canepa \
    --image ~/scratch/charts/canepa-full.jpg \
    --mode dark --threshold 115 --open 7 --se square --closing 3 \
    --tolerance 3 --bbox 1000,5950,1560,7250 \
    --height-km 593 --centre=-35.2,35.5
python3 scripts/build_geojson.py && cp src/data/islands.geojson public/data/
```

Traced outlines live in `src/data/outlines/{id}.geojson`; `build_geojson.py`
prefers one over a blob, so **one island is a complete unit of work**. Chart
landmarks and provenance live in `scripts/charts/{chart}.json`. **The chart
rasters are deliberately not committed** — 3 to 17 MB each of pure tracing
input, and the source URL reproduces them.

**Two extraction modes, because charts differ.** A flat colour wash
(Pizzigano's Antillia is solid red) is picked out by `--mode red|blue|green`.
An outlined coast round a pale interior (Canepa) needs `--mode dark` to catch
the ink band, which is then closed and filled — the interior is the same
parchment as the ocean, so it cannot be selected directly.

**Scale and position come from georeferencing where the chart can support it.**
Portolans carry real coastlines beside their invented islands, so landmarks fit
a similarity transform giving km/pixel and the chart's own rotation. Six
landmarks on Pizzigano fitted to RMS 47 km. But that only holds *inside the
surveyed region*: everything west of the Canaries on these charts is imagined,
and extrapolating a transform out there produced a confidently wrong answer
(Antillia east of the Azores). Anchor on the nearest thing the chart actually
drew instead.

**Latitude may be a judgement.** Antillia's is: the charts supported anywhere
from 37 to 41, so 35.5 was chosen for how it reads against real geography.
That is legitimate and recorded as such. Aesthetics are allowed to decide what
the evidence does not.

### Traps, all of which cost real time

**A disk-shaped structuring element cannot preserve a right angle.** Canepa
draws squared bays; every opening radius turned one into a triangle, and no
amount of tuning helped, because a disk rounds corners by construction. Use
`--se square` where the coastline is rectilinear.

**Close with `disk(n)`, not an `n × n` box.** The box is far weaker. A gap left
anywhere in a coast band means `fill_holes` cannot close the interior, and the
island comes out as a **ring** — same bounding box, a third of the pixels, and
invisible unless you diff the mask.

**Image y grows downward, latitude grows upward.** A similarity transform
cannot express a reflection, so without flipping y first the fit absorbs it as
a ~100° rotation and every residual is hundreds of km out. It looks like bad
landmarks rather than bad algebra.

**Settlement cartouches are labels, not lakes.** Names written on the island
are holes in the colour wash and must be filled.

**Look at the mask, not the numbers.** Every real fault here was invisible in
the summary statistics and obvious the moment the mask was rendered.

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
- **31 of 34 written in French** — all 28 blog posts imported verbatim,
  47,269 words, with the 36 map plates from the posts in `public/iles/`
- English has only `hy-brasil`, so 30 islands sit in `translated` state there
- 2 partial drafts (`nakanotorishima`, `nimrod`) with notices
- Geometry is placeholder blobs except `antillia`, traced from Canepa 1489
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

1. ~~Migrate the 28 stories~~ **Done**, by `scripts/import_posts.py`, which
   reads the WordPress REST API rather than the rendered page so the prose
   arrives verbatim — no model in the loop. Re-runnable: `--slug X --dry-run`
   to preview one, `--all --images --force` to redo everything. If a post is
   edited on the blog, re-run rather than hand-patching.
2. **Trace real outlines.** `antillia` is done — see *Tracing island shapes*.
   Next best candidates: `frisland` (the Zeno lozenge), `californie` (a long
   N–S sliver) and `coree` (a peninsula), the three where a placeholder blob
   actively misleads. Everything else can stay a blob indefinitely; an island
   nobody agreed on the shape of should look vague.
   Outstanding on `antillia`: its scale is inherited from a Pizzigano
   measurement because `scripts/charts/canepa.json` has no landmarks yet.
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
