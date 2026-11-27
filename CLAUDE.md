# Atlas des îles fantômes

A bilingual literary atlas: a world map of islands that were believed to exist
and did not, each linking to a short story. Fiction, not reference — the
stories are the point; the cartography is the frame.

Written by Étienne Fortier-Dubois. Stories originate on his French blog, now
a static archive at `etiennefd.com/archive/cartographier/`; the old
`etiennefd.com/cteniq/{slug}/` URLs redirect there (308), so `source:` links
still resolve. The WordPress install and its REST API are gone — known, no
need to report it.
28 stories written of ~50 planned.

## Commands

```sh
npm run dev        # localhost:4321, redirects to /fr/ (prefixed layout; see Current state)
npm run build
npm run preview

npm run geo        # rebuild island geometry AND copy it to public/ — see Traps
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
  lib/hosts.mjs           where each language lives; url() builds every link
  components/map.ts       the D3 map
  components/PhantomMap.astro
  i18n/ui.ts              ~30 UI strings
  pages/[lang]/{index,liste}.astro, pages/[lang]/iles/[slug].astro
public/data/              runtime copies of islands.geojson + land-50m.json
scripts/                  seed_islands.py, build_geojson.py
vercel.json               per-host rewrites and redirects — see Hosting and URLs
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

  The map's box is **square**, sized to the screen's height less the header
  and story count, up to 900 px (`.pmap-wrap`). It used to be the flat map's
  1200 x 640, which held the globe to 624 px on any screen with the reset
  button stranded at the box's far corner. Étienne, November 2026, chose the
  900 px cap over filling the whole height. Phones are unchanged: the box is
  the screen's width.
- **One canonical French slug per island**, used in both languages:
  `phantomislands.etiennefd.com/iles/ile-des-demons/`. No slug lookup table.
- **Stories are many-to-many with islands.** Three existing posts cover more
  than one island (`crocker-land` + `bradley-land`, `juan-de-lisboa` +
  `dos-romeiros`, and the reefs post). Availability is derived at build time.
- **Island names render in italic** on the map. Cartographic convention sets
  hydrography in italic — so italicising the phantoms quietly says "this is
  water." Keep it.
- **The page background is the ocean.** No panel chrome floating over the map.
- **A survey of the island beats a chart depiction of it**, where one exists.
  `nakanotorishima` is traced from the sketch Yamada Teizaburō signed in 1908
  as its discoverer: contour lines, four named hills and flats, transects and
  marginal figures in *ken*. That is not the most influential depiction and is
  meant not to be — for an island that never existed, the invention drawn in
  detail by its inventor is a better source than anyone else's copy of it.
- **An island's shape comes from the most famous or influential depiction**,
  not the earliest. For Antillia the two coincided anyway: Pizzigano 1424 is
  both first and the one everyone copied. Where they differ, influence wins.
  The plate that illustrates the story is a candidate like any other, often a
  strong one — but not the default: it was picked as an illustration, not
  vetted as a source, so it goes in the line-up with the others. An earlier
  version of this note said "*not* the story's plate", and that was read as
  excluding it; Étienne, October 2026: "the map included in the story is a
  strong candidate."

## Data model

### Island (`src/content/islands/{id}.yaml`)

Filename is the id. `kind` drives rendering:

- `island` — a polygon, or a MultiPolygon where the source draws the island's
  satellites too (`frisland` has 23 parts)
- `reef` — a Point in the data, drawn as **a cluster of four to six
  irregular rocks**, filled even at rest (`rockCluster` in `map.ts`, seeded
  by id so no two reefs match). A 100 m reef is a thousandth of a pixel even
  at 8x, so the cluster is a stand-in, laid out on the ground at `REEF_KM`
  (4 km) per unit: ~60 km across, which is ~2 px at world zoom and ~15 px
  at 8x. It scales with the zoom and takes its halo like any small island.
  Étienne, November 2026, picked the cluster out of four mock-ups: a plain
  dot (read as a pin), the cluster, the cluster inside a dotted danger ring
  (too close to the dashed "no story" outline), and the cluster with *E.D.*
  lettered beside it (the only text on the globe at rest). The mock-ups drew
  it at a fixed ~8 px on screen; trying it, he had it scale with the zoom
  instead: "They're reefs, we don't really need to see them that much."
  It used to be geoPath's default point circle, a 30 px disc at high zoom.
  `?at=lon,lat,k` opens the map on a fixed view, for renders; the language
  switch also uses it to carry the current view across, and the map drops it
  from the address bar once read.
- `misdrawn` — a *real place wrongly charted* (Corée, Californie). **The
  basemap is replaced where its chart disagreed**, permanently, not on hover:
  the atlas simply does not carry the real California. Étienne, September
  2026: *"we won't see the real California ever. This is fine, we don't
  really care about the real land on this map."* Once the basemap is cut, a
  misdrawn island needs no special styling at all — outline at rest, burgundy
  on hover, like every other phantom. See **Replacing the basemap** below.
  That supersedes the older suspension of the question.
- `coast` — an **open shore**, seen from a ship or a sledge and never
  reached (`terre-de-davis`, `crocker-land`, `bradley-land`). A LineString
  with the land on its right — several where the chart breaks the shore —
  plus any islets as polygons, in one GeometryCollection. **It follows the same rules
  as every island, with a fade standing in for the coast nobody saw**: at
  rest only the line, solid or dashed by state; on hover the land behind it
  fills as **a band that follows the shore**, solid against it and fading out
  inland and into both ends — full burgundy for a story here, soft rose at
  0.55 otherwise. Étienne, October 2026, chose the land side over a sea-side
  shade like the chart's hatching, then made it hover-only and solid at the
  shore: "it is the equivalent of filling the island with color." The first
  version, linear gradients over a box behind the shore, he called ugly; of
  three replacements he picked the band ("B is clearly best") over an
  island-shaped fade deepest in the middle and over fading echo lines with
  no fill. The band is 0.285 of the shore's chord deep — 75 km on Davis
  Land — since a fixed depth turns Bradley Land's 30-50 km brackets into
  long bars. See **Open coasts** below.

`coords_confidence` is one of `attested | approximate | conjectural | unknown`,
with `coords_note` recording provenance. **Six islands are `conjectural`** —
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

### Replacing the basemap, for `misdrawn` islands

A misdrawn island is not an invention, it is real land drawn wrong, so showing
what its chart claimed means **removing the real coastline there**. Two things
took a while to understand and are worth not rediscovering.

**Erasing the island's own footprint is not enough.** Baja is land in both
readings; the claim is that the *isthmus is a strait*. So water has to be
opened east of the phantom coast as well, or nothing has changed. The pieces:

```sh
python3 scripts/build_misdrawn.py      # -> public/data/misdrawn.geojson
```

It writes two rings per island — the island's footprint, grown a little, and
the strait — and `map.ts` cuts the land layer with an SVG `<mask>` built from
them. A mask rather than painting water over the top, because paint would also
cover the island outlines and halos that fall inside the region.

**The strait is built as a ring**, not as a region to subtract: the island's
east shore going south, across the mouth of the Gulf, then the chart's own
mainland coast coming back north. Carving only that plus the footprint leaves
the real mainland *real* — its coast east of the channel is the genuine one,
with no seam where a patch would have ended.

**Grow the footprint** (70 km for Californie) or small real islands survive
just outside the traced outline — Cedros, the Channel Islands, specks of
Baja's shore — and sit in dark grey under the phantom. Do it on a raster: a
vertex-by-vertex offset self-intersects on every concave bay and leaves
unerased shards stranded in the new sea.

**Where no chart reaches, borrow a coastline.** Californie's strait has to
meet the real Oregon coast and no chart of the island goes there — Vinckeboons
and the 1650 French sheet stop near 41.4 N, Senex runs his off the plate. That
is ~900 km with no source, and a smooth arc across it looks exactly like what
it is. `scripts/borrow_coast.mjs` lifts a real stretch out of Natural Earth
and `build_misdrawn.py` lays its *roughness* along a path of our choosing. It
is a fabrication either way; this one is at least made of coastline, and it is
committed as data with its own provenance in `src/data/borrowed/`.

**Where the chart draws no mainland, erase the real country.** Korea is the
second case and the opposite one: Teixeira runs the island straight off the top
of his frame and draws no continent to cut a strait against. But the claim is
plain — the real peninsula is not there — and the real peninsula is exactly
North plus South Korea. `scripts/lift_country.mjs korea -- 408 410` lifts them
from `countries-50m` into `src/data/borrowed/korea.json`, and a spec with
`countries=` erases them grown 6 km, plus the island's footprint grown 30 km.
The new mainland shore is then the real Yalu–Tumen border, which is where a
strait would have had to run; only the island's north tip, poking ~90 km into
China, gets an invented shore. No borrowed coast was needed.

Four traps, all paid for:

- **The land and country layers disagree on islets.** Baengnyeong-do is in
  `land-50m` and in no country of `countries-50m`, so erasing South Korea left
  it standing alone in the new Yellow Sea. `lift_country.mjs` now takes any
  land polygon no country covers whose nearest country is one being lifted.
  Check by testing every land polygon near the region against the erase rings;
  a render at world zoom does not show a 59 km² island.
- **Stop following the chart's mainland before its head.** Vinckeboons bends
  that coast east to −111.5, so carrying it to the top opened a 370 km swathe
  of water across the north and a bay that served nothing. Above
  `mainland_to_lat` the shore is a collar offset from the island instead.
- **Orient an outward offset by testing the polygon, not by pointing away from
  the centroid.** On a 2200 km island the centroid is hundreds of km south of
  the northern tip, so "away from the centroid" sends the whole collar due
  north and the strait came out 1300 km wide.
- **De-mean a borrowed coastline before using it.** The Oregon stretch bulges
  one way by up to 108 km with a 44 km bias; laid raw against a 200 km collar
  it pushes the shore clean across the strait and folds the ring inside out.
  Take the roughness, not the bend.

### Island states, resolved in `lib/atlas.ts`

**Every island is an outline until the cursor reaches it**, and a dashed
outline means the story is not available *here*. Written only in the other
language and not written at all are deliberately indistinguishable — they are
the same thing to a reader standing in front of the map, and an earlier
attempt to separate them by line weight was rejected.

| state | condition | at rest | on hover |
|---|---|---|---|
| `available` | non-draft story in the current language | solid burgundy outline | fills burgundy |
| `translated` | story only in the other language | **dashed** burgundy outline | fills soft rose, 0.55 |
| `planned` | no story, or draft only | **dashed** burgundy outline | fills soft rose, 0.55 |

`translated` adds a cross-language note on the island's page; `planned` labels
it *à venir*. The distinction lives in the words, not in the drawing.

All of this is in `.pmap__island` in `src/styles/tokens.css`, driven by
`fill-opacity` rather than `fill: none`, because a transition *from* `none`
does not animate.

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

**Natural Earth still carries a phantom as land.** `land-50m` has Sandy
Island (`ile-de-sable`): a 6-point polygon of 71 km2 at 159.93-159.98 E,
19.12-19.33 S, inherited from the same World Vector Shoreline that kept the
island alive until 2012. `public/data/land-50m.json` is therefore no longer
a plain copy of world-atlas's: `node scripts/build_basemap.mjs`
rewrites it with that polygon taken out, and refuses unless each box drops
exactly one polygon of the expected area. Dropped from the file rather than
masked on the globe so that `check_overlap`, `place_island` and
`lift_country` see the same basemap. Run it again after any world-atlas
upgrade, and check a new island's spot for a basemap copy of itself:
`check_overlap` reporting a phantom "on land" in open ocean is the tell.

**And it lacks a real island a phantom is placed by.** Bouvet is in no
polygon of `land-50m`, and Thompson Island is set by its offset from Bouvet
on Norris's chart, so it sat alone in empty sea. The same script adds
Bouvet from `land-10m` (54.5 km2, 18 points), re-quantized onto land-50m's
grid (about 230 x 190 m there): one 10m polygon in a 50m basemap, by
Étienne's choice (November 2026), and the only exception to the
one-resolution rule. Each addition's box must hold exactly one 10m polygon
of the expected area, which also skips land-10m's three degenerate
whole-sphere polygons. Check a new island's real neighbours exist at 50m
before placing it against them.

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

**Typography is applied at build time, and Astro caches it per story.**
`src/lib/typo.mjs` sets French spacing (non-breaking spaces at : ; ! ? « »,
with units, thousands, abbreviations and the dialogue dash), and raises
ordinals: XXᵉ siècle with the numeral in small caps, Élisabeth Iʳᵉ in
capitals, 17ᵉ. One rehype plugin for the bodies, `typesetMarkdown` for
notices, captions and notes. The markdown keeps plain spaces and "XXe" on
purpose. Astro re-renders only stories whose file changed, so after editing
`typo.mjs` run `npx astro build --force`, or unchanged stories keep the old
output and look as if the rule did not fire. A lone roman letter with a bare
"e" is only raised before "siècle": "Le" is L + e.

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

## Adding an island

Done thirty-three times: `antillia`, `bermeja`, `nakanotorishima`, `frisland`,
`kianida`, `hy-brasil`, `groclant`, `californie`, `coree`, `mayda`,
`saint-brendan`, `buss`, `juan-de-lisboa`, `dos-romeiros`, `ile-des-demons`,
`saint-mathieu`, `bacalao`, `los-jardines`, `zanara`, `elizabeth`, `thule`,
`ile-aux-vaches`, `maria-de-lajara`, `phelipeaux-et-pontchartrain` (the
first island with no story, four islands in one entry), `satanazes` and
`royllo` (Antillia's neighbours, each placed by its offset from Antillia on
its own chart), `iles-de-la-compagnie-royale` (Arrowsmith 1814, three
islets placed by the sheet's own Mercator graticule), `ile-de-sable` (no
chart at all: the World Vector Shoreline's polygon, lifted unchanged),
`pepys` (Moll's 1711 inset, two islands with the channel the colourist
washed over cut back out), `thompson` (its discoverer's own chart, placed
by its offset from Bouvet on it), and `terre-de-davis`,
`crocker-land` and `bradley-land` as open coasts. `bacalao`, `los-jardines` and `zanara` were done
in October 2026 in a run Étienne asked to go "without my input": every source
and placement choice in them is Claude's, and their notes say so.
Read this before the next — it is written so Étienne does not have to explain the
project again.

A phantom island's shape is a claim, not a fact, so it carries provenance of
its own in `outline_note` — often citing a *different* chart from the one the
position came from.

### How to work on one

**One gate, not five — revised September 2026**, after Kianida, Hy-Brasil and
Groclant: *"I think we have learned quite a bit on the process and I can let
you be more autonomous."* The gate is **the source**. Bring two or three
candidates with crops and pixel sizes, and let him pick — that one earns its
keep, because he has overruled the recommendation twice and the shape changed
materially both times. After that, run to completion: trace, scale, position,
verify, notes, commit. Report the finished island with its numbers and an
explicit list of any liberties taken.

Come back mid-way for exactly two things: **a genuine taste call** (the
shrink-versus-turn question on Groclant), and **an island that cannot be
placed without lying on real land**. Nothing else.

The older rule was one approval per step — *"You need to validate with me each
big step, because we're wasting time and work by doing the whole thing at once
and getting it wrong."* It was right while the process was still being learned
and the failures were unknown. The three scripts below now catch the failures
that made it necessary.

**Put every render in the chat**, with SendUserFile. A file path is not a
render. *"can you actually put the final image in the chat so I can see it?
it's hard for me to give feedback."* And never draw an annotation over the
thing under discussion — a circle marking the bay he is trying to look at
makes the image useless.

**Ask whenever taste is involved** rather than deciding and defending:
*"You don't have good intuitions to give self-criticism so whenever you try
something where taste might be involved, ask me."* Which depiction, how big,
how smooth, whether an islet belongs, what colour anything is — all his. Give
him the measurements and a recommendation, then stop.

**Change only what he asked about.** Fixing a bay he approved while fixing the
one he didn't is not a bonus.

### The tools

Three scripts exist because each was hand-written three times, badly, before
it was written once properly. Use them; the failures they catch are silent.

```sh
# which mode and threshold? and is a line cutting the island in half?
python3 scripts/probe_extraction.py --image ~/scratch/charts/x.jpg \
    --bbox 980,100,1800,740

# where can it sit without lying on real land, and at what turn and scale?
node scripts/place_island.mjs groclant --turn -35,-25,2.5 --scale 0.88,0.96,0.02

# draw it, with any overlap on land dotted in orange — before writing it
node scripts/preview_island.mjs groclant --turn -32.5 --scale 0.91 \
    --centre=-67.75,73.95

# and afterwards, the bare question
node scripts/check_overlap.mjs groclant
```

`probe_extraction.py` reports a d-prime per mode against the frame's border,
sweeps the threshold, and prints the plateaux — the ranges where the extent
stops moving, which is where the answer is. Its **SPLIT** warning is the one
to read: it fires when the largest connected part holds under 98% of the mask,
which is what a line drawn across an island does.

`place_island.mjs` searches centre, `--turn` and `--scale` together against a
cached land raster and prints the exact trace_outline flags. It works from the
island's own stored `turned_deg`/`scaled_by`, so it tests the geometry that
will actually be written — rotating about the wrong origin is a 20-40 km error,
enough to ground a large island.

`preview_island.mjs` always dots the land overlap, which is why it exists.

Three flags on `trace_outline.py` earn a mention, all added for Californie and
all general:

- `--seed x,y` names which landmass you want, in source pixels, when it is not
  the largest one sharing a wash. Vinckeboons paints the phantom island and
  the American mainland the same green and the mainland is bigger, so the
  default quietly traces the wrong continent.
- `--satellites MIN,MAX` keeps the chart's smaller islands as extra parts of
  the same feature — a phantom archipelago is more interesting than a phantom
  blob. Components touching the crop edge are skipped, being clipped mainland
  rather than islands.
- `--islet x,y` keeps an islet the wash never reached — S. Matheo's is a
  pale core in an open ink ring. It seals the ring as the plate path seals
  Frisland's islets and adds the core as a satellite. Radii 4-6 only: the
  sealing keeps the largest core it finds, and a wider closing fuses nearby
  sea hatching into a ring of its own.
- `--dots N` keeps the **portolan ring of rock dots** as islets, found on
  their own terms rather than by the island's threshold, which either loses
  the darker dots or fuses them to the coast and lifts rhumb lines with
  them: dark, compact, red, 12-150 px, within N px of the coast, split where
  they touch. Farther out are ships; lettering close in can pass, so paint
  it out. Added for Piri Reis' Isle of Cows, 13 dots.
- `--drop-parts i,j` discards satellites the georeference lands on real
  ground. Every part's centroid is printed so the choice is auditable. Two of
  Vinckeboons' Gulf islands come out 200 km inland in Arizona.
- `--channel x,y;x,y` cuts back out water the colourist washed over as land:
  Moll runs Pepys Island's coastal yellow straight across the channel
  between its two islands. From each point it floods through the pixels the
  engraver left unhatched (ink covering at most 10% of a 7 px window),
  inside the island, and removes them; remnants under 200 px are dropped.
  Paint out lettering written across the channel first ("Bay"), keeping the
  box off both shores: a box 4 px too far south opened the flood into the
  south island's interior.
- `--join R` closes the mask with `disk(R)` *before* the largest piece is
  chosen, for an outline sketched in separate strokes: Norris drew Thompson's
  Island in four, with gaps up to 25 px, and without it the trace was one
  stroke. It also smooths over bays narrower than 2R; at 2.5 km nothing
  that small shows.
- `--cut "x,y x,y ..."` draws water by hand, 7 px wide, where the engraving
  crowds a channel shut (a coast line's end and a tree symbol, at Pepys'
  north-east outlet). A liberty, like `--seal`.

### The steps

1. **Choose the source** — see the rules below on which depiction wins. Show
   him the candidates and let him pick; he has overruled the default rule at
   least once, for Nakanotorishima.
2. **Fetch the raster at full resolution.** Ask the Commons API for the real
   URL: hand-built `upload.wikimedia.org` paths return 2 kB error pages that
   look like successful downloads. Put it in the scratchpad — rasters are
   **deliberately not committed**, being 3–17 MB of pure input that the source
   URL reproduces.
3. **Write `scripts/charts/{chart}.json`** — name, source URL, licence, and a
   `note` saying why this depiction and not another. Landmarks go here if the
   chart carries real coastline; so do `plate` parameters if it is an
   engraving.
4. **Trace, then look at the mask drawn over the source.** Every real fault so
   far was invisible in the summary statistics and obvious in the overlay.
   Show him that overlay and the bare silhouette.
5. **Scale, then place** — as separate steps, in that order, each on the
   globe. `size_km` in the outline file is a control, not a readout: edit it,
   re-run `npm run geo`, and the island changes size.
6. **Record the reasoning** in `coords_note` and `outline_note`, including the
   value you moved away from and why. These notes are the reason a later
   session can tell a decision from an accident.
7. **Verify in the browser**, then commit. `.claude/launch.json` defines a
   `dev` server on 4321 for the preview pane. Two things to know: the pane's
   screenshots can serve a stale frame, so read computed styles and DOM
   attributes rather than trusting a picture that looks unchanged; and the
   map's own render loop rewrites island classes every frame, so a class you
   add by hand is stripped before a CSS transition finishes — set
   `style.transition = 'none'` and read the value in the same tick.

### The worked examples

```sh
# Antillia — a flat colour wash on a portolan, squared bays
python3 scripts/trace_outline.py antillia --chart canepa \
    --image ~/scratch/charts/canepa-full.jpg \
    --mode dark --threshold 115 --open 7 --se square --closing 3 \
    --tolerance 3 --bbox 1000,5950,1560,7250 \
    --height-km 593 --centre=-35.2,35.5

# Bermeja — an islet left blank inside hachured shoal rings
python3 scripts/trace_outline.py bermeja --chart gulf-english \
    --image ~/scratch/charts/bermeja-a.jpg --mode dark --bright \
    --upsample 4 --smooth 2 --height-km 10 --centre=-91.37,22.55

# Nakanotorishima — a survey sketch, neatline close to the coast
python3 scripts/trace_outline.py nakanotorishima --chart yamada \
    --image ~/scratch/charts/naka-dedicated.gif \
    --mode dark --threshold 115 --closing 3 --blank-rows 10,21 \
    --despeckle 1200 --tolerance 1.5 --height-km 10 --centre=154.42,30.75

# Frisland — an engraved plate; everything else lives in the chart JSON
python3 scripts/trace_outline.py frisland --chart frisland-1562 \
    --image ~/scratch/charts/frisland-1562.jpg \
    --tolerance 1.5 --centre=-29.0,63.02

# Kianida — a woodcut ink band; the sheet's own landmarks give scale AND place
python3 scripts/trace_outline.py kianida --chart ulm-1482 \
    --image ~/scratch/charts/ulm-1482-nona-europe.jpg \
    --mode dark --threshold 75 --closing 3 --tolerance 1.5 \
    --bbox 3570,1660,3900,1930

# Hy-Brasil — a violet wash the other modes cannot see
python3 scripts/trace_outline.py hy-brasil --chart catalan-atlas \
    --image ~/scratch/charts/catalan-f6-atlantic.jpg \
    --mode magenta --threshold 7 --smooth 16 --closing 20 \
    --tolerance 1.5 --bbox 1450,620,1960,1150 \
    --height-km 73 --centre=-15.0,51.5

# Mayda — gold leaf on the same panel; yellow is blue --bright
python3 scripts/trace_outline.py mayda --chart catalan-atlas \
    --image ~/scratch/charts/catalan-f6-mayda.jpg \
    --mode blue --bright --threshold=-40 --smooth 3 --closing 5 \
    --tolerance 1.5 --bbox 200,50,850,650 \
    --height-km 59.6 --centre=-20.0,47.0

# Saint-Brendan (San Borondón) — every real Canary on the sheet, so fully
# georeferenced; a paper fold crosses the island and needs --closing 30
python3 scripts/trace_outline.py saint-brendan --chart canarias-1760 \
    --image ~/scratch/charts/sb-canarias-1760.jpg \
    --mode dark --threshold 130 --smooth 6 --open 9 --closing 30 \
    --tolerance 2 --bbox 180,2300,720,3300

# Buss — bare paper both sides; the sea flooded in, walled by the coast band
python3 scripts/trace_outline.py buss --chart seller-1670 \
    --image ~/scratch/charts/buss-seller-1670-draught.jpg \
    --mode density --threshold 0.35 --window 15 --open 30 --closing 120 \
    --relief-box 200,700,1500,1850,120 \
    --blank-box "2545,1420,3090,1760;2780,2243,3150,2290" \
    --satellites 10000,40000 --tolerance 3 --bbox 200,700,3272,2950 \
    --height-km 165.0 --centre=-30.64,57.98

# Juan de Lisboa and Dos Romeiros — hatched islets on one georeferenced
# chart; smoothing makes the hatching solid, an opening strips rhumb lines
python3 scripts/trace_outline.py juan-de-lisboa --chart linschoten-1596 \
    --image ~/scratch/charts/jl-linschoten-rumsey.jpg \
    --mode dark --threshold 75 --smooth 2.5 --open 6 --closing 6 \
    --tolerance 1.5 --bbox 5560,6580,5760,6710
python3 scripts/trace_outline.py dos-romeiros --chart linschoten-1596 \
    --image ~/scratch/charts/jl-linschoten-rumsey.jpg \
    --mode dark --threshold 75 --smooth 2.5 --open 9 --closing 6 \
    --tolerance 1.5 --bbox 7780,6980,7980,7100

# Groclant — a polar projection, and an island moved because it hit real land
python3 scripts/trace_outline.py groclant --chart ortelius-1570 \
    --image ~/scratch/charts/ortelius-north.jpg \
    --mode blue --bright --threshold=-45 --smooth 3 --closing 5 \
    --tolerance 1.5 --bbox 980,100,1800,740 \
    --turn -32.5 --scale 0.91 --centre=-67.75,73.95

# Corée — no colour separates it, so flood from inside, stopped by the coast
python3 scripts/trace_outline.py coree --chart hondius-iaponia \
    --image ~/scratch/charts/coree-iaponia-1619.jpg \
    --mode ink --threshold 130 --closing 16 --tolerance 3 \
    --bbox 3100,560,4600,6300 --blank-box 3598,5465,3668,5698 \
    --seed "3700,2500;3600,5300;3630,5600;3719,5737;3598,5779;3730,5814"

# Île des Démons — the flood walled by the coast's hatch band; the demons on
# the north shore stand across the coast, so that stretch is sealed by hand.
# Placed by the story (Harrington Harbour), not by the charts, at 10 km.
python3 scripts/trace_outline.py ile-des-demons --chart gastaldi-1556 \
    --image ~/scratch/charts/demons-gastaldi-1556.jpg \
    --mode band --threshold 0.25 --window 15 --closing 6 --grow 3 \
    --seed 3000,1150 --seal "3045,640 3090,645 3125,648 3175,652 3220,655 3245,655" \
    --blank-box "2848,1040,2965,1230;3058,585,3228,800" \
    --tolerance 1.5 --bbox 2600,540,3460,1540 \
    --height-km 10 --centre=-59.45,50.49

# Saint-Mathieu — a clean orange wash; the landmark fit is poor (RMS 201 km)
# out here, so the centre is anchored on Annobón at the graticule's scale
python3 scripts/trace_outline.py saint-mathieu --chart ortelius-africa-1572 \
    --image ~/scratch/charts/sm-ortelius-1572.jpg \
    --mode red --threshold 40 --closing 3 --tolerance 1 \
    --bbox 3720,4700,3960,4960 --islet 3824,4752 --centre=-5.08,-1.35

# Bacalao — the same Gastaldi sheet; its lettering sits on the south shore
python3 scripts/trace_outline.py bacalao --chart gastaldi-1556 \
    --image ~/scratch/charts/demons-gastaldi-1556.jpg \
    --mode band --threshold 0.25 --window 15 --closing 6 --grow 3 \
    --seed 3050,2170 --blank-box 2990,2192,3125,2256 \
    --tolerance 1.5 --bbox 2820,2080,3360,2380 \
    --height-km 87 --centre=-51.3,48.2

# Los Jardines — two islets blank inside hatching; ring sealing, not a threshold
python3 scripts/trace_outline.py los-jardines --chart ortelius-pacific-1589 \
    --image ~/scratch/charts/lj-bnf-1589.jpg \
    --mode ring --seed "1357,2291;1396,2285" --tolerance 0.75 \
    --bbox 1310,2250,1450,2320 --height-km 52.6 --centre=145.3,10.6

# Zanara — solid coastal shading; scale from the latitude border, not a fit
python3 scripts/trace_outline.py zanara --chart mercator-tuscia-1589 \
    --image ~/scratch/charts/zan-tuscia-ia.jpg \
    --mode band --threshold 0.4 --window 15 --closing 6 --grow 3 \
    --seed 7250,8960 --tolerance 1.5 --bbox 7130,8840,7540,9110 \
    --height-km 5.0 --centre=10.990,42.298

# Elizabeth — a drawing from Drake's voyage, south-up, so turned 180; the
# stream joins the pool to the coast and is painted out so the pool fills
python3 scripts/trace_outline.py elizabeth --chart fletcher-elizabeth \
    --image ~/scratch/charts/eliz-nuttall-0360.png \
    --mode ink --threshold 110 --closing 3 --seed 1000,1450 \
    --blank-box 1000,926,1032,1045 --tolerance 1.5 \
    --bbox 600,820,1420,1650 --turn 180 --height-km 48.3 --centre=-70.0,-57.0

# Thule — the Carta Marina's Tile, separate from Iceland, which stays; a road
# on the north shore is painted out; the west islet sealed with --islet
python3 scripts/trace_outline.py thule --chart carta-marina-1539 \
    --image ~/scratch/charts/thule-cartamarina-1539.png \
    --mode band --threshold 0.4 --window 15 --closing 6 --grow 3 \
    --seed 1316,4732 --blank-box 1415,4552,1665,4583 \
    --islet 1282,4640 --islet-threshold 130 --tolerance 1.5 \
    --bbox 1100,4330,2080,5060 --height-km 120 --centre=-11.0,60.0

# Île aux Vaches — a red wash on Piri Reis 1513, ringed by rock dots kept as
# 13 islets; a word of lettering beside the coast painted out
python3 scripts/trace_outline.py ile-aux-vaches --chart piri-reis-1513 \
    --image ~/scratch/charts/vaches-pr-a.jpg \
    --mode red --threshold 75 --smooth 2 --open 3 --closing 3 --dots 30 \
    --blank-box 985,1298,1013,1318 --tolerance 1 \
    --bbox 930,1300,1110,1470 --height-km 352 --centre=-35.0,6.2

# María de Lajara — an engraved outline with no wash, crossed by two rhumb
# lines as thin as its coast: fill first, then strip the lines (--strip)
python3 scripts/trace_outline.py maria-de-lajara --chart anson-1748 \
    --image ~/scratch/charts/lajara-anson-1748-rmg.png \
    --mode dark --threshold 145 --strip 3 --closing 2 --tolerance 0.75 \
    --bbox 4750,775,4825,835 --height-km 52.2 --centre=-140.0,27.0

# Phélipeaux et Pontchartrain — four islands on one sheet, each traced on
# its own (--mode band, seeded inside, walled by the lake's hatching), then
# merged into one MultiPolygon; nine landmarks round Lake Superior fit at
# RMS 41 km. Phélipeaux's lettering is painted out in seven boxes cut to the
# shore, from a 5 px grid zoom: one box across the text cut the island in
# two, a larger one let the flood out through the coast
python3 scripts/trace_outline.py phel-phel --chart bellin-1744 \
    --image ~/scratch/charts/bellin1744-thumb.jpg \
    --mode band --threshold 0.25 --window 8 --closing 3 --grow 2 \
    --seed "700,726;855,676" --islet 627,718 --tolerance 1 \
    --blank-box "699,709,712,730;704,706,745,742;747,692,767,723;768,690,790,715;790,672,814,710;814,662,840,701;840,668,850,696" \
    --bbox 590,615,900,780
# likewise phel-pont (--seed 1120,525 --bbox 1040,470,1215,585), phel-maur
# (--seed 1235,370 --bbox 1140,290,1325,455), phel-anne (--seed 1205,720
# --bbox 1160,675,1260,780); then the four merged by hand, the temporary
# outlines deleted, and two islands moved off land (see the trap below)

# Satanazes — Pizzigano's blue wash, crossed by name cartouches that run to
# within a pixel of the shore: at a plain threshold the island breaks along
# them and loses its south-west lobe. A light smoothing at a low threshold
# keeps the rims. Placed by its offset from Antillia on the same fit, laid
# off from Antillia's chosen position — the fit read raw is an extrapolation
python3 scripts/trace_outline.py satanazes --chart pizzigano \
    --image ~/scratch/charts/antil/Pizzigano.jpg \
    --mode blue --threshold 10 --smooth 2 --closing 6 --tolerance 1.5 \
    --bbox 1080,1000,1380,1340 --centre=-34.43,42.94

# Royllo — Canepa's faded grey "Roillo", at the scale Antillia inherits on
# that sheet (593 km over 1022 px) and at its offset from Antillia there
python3 scripts/trace_outline.py royllo --chart canepa \
    --image ~/scratch/charts/antil/Portolan_chart_by_Albino_de_Canepa_1489.jpg \
    --mode dark --threshold 110 --smooth 1.5 --open 2 --closing 3 \
    --tolerance 1.5 --bbox 800,6600,1080,6880 \
    --height-km 105.6 --centre=-37.604,35.26

# Îles de la Compagnie Royale — three engraved islets on a Mercator sheet
# with no real coast near: centre and km/px read off its own graticule
# (294.1 px per degree of longitude, 0.2455 km/px at 49.6 S), sheet scale kept
python3 scripts/trace_outline.py iles-de-la-compagnie-royale \
    --chart arrowsmith-1814 --image ~/scratch/charts/rci/arr-13258002.jp2 \
    --mode dark --threshold 110 --closing 2 --satellites 150,3000 \
    --tolerance 1 --bbox 12645,11600,12775,11750 \
    --height-km 27.50 --centre=142.911,-49.561

# Île de Sable — no tracing: the World Vector Shoreline's polygon, the one
# Google Earth drew until 2012, lifted from GSHHS 2.2.0 (2011) as GMT shipped
# it. One closed segment, written untouched and wound clockwise (GSHHS winds
# land counterclockwise, which d3-geo reads as the planet minus the island)
python3 -I scripts/extract_gshhs.py ile-de-sable \
    --cdf ~/scratch/gshhs/gmt-gshhs-2.2.0/share/coast/binned_GSHHS_f.cdf \
    --bbox 159.8,-19.5,160.1,-19.0 --chart gshhs-2.2.0
node scripts/build_basemap.mjs   # Natural Earth has it as land too

# Pepys — Moll's 1711 inset of the drawing from Cowley's voyage. The
# colourist's yellow coastal wash is the shore (the north-east flanks have no
# engraved coast); it also fills Admiralty Bay, which is cut back out, and
# the channel's crowded north-east end is opened by hand. 50 km across the
# pair by Étienne's choice: the larger island is 19.8 km tall
python3 scripts/trace_outline.py pepys --chart moll-1711 \
    --image ~/scratch/charts/pepys/moll-1711-rumsey.jpg \
    --mode blue --bright --threshold=-30 --smooth 2 --closing 3 \
    --blank-box 6368,6806,6432,6834 --channel "6455,6792;6360,6835" \
    --cut "6498,6780 6514,6762 6527,6742 6535,6722" \
    --tolerance 1.5 --bbox 6260,6650,6800,6950 \
    --height-km 19.8 --centre=-61.035,-47.496

# Thompson — Norris's own chart (1825, printed by the RGS in 1928), the
# island in four open strokes; the parallel and meridian across it painted
# out, the strokes joined into one ring. Chart scale; the centre is its
# offset from Bouvet on the chart, laid off from the real Bouvet
python3 scripts/trace_outline.py thompson --chart norris-1825 \
    --image ~/scratch/charts/thompson/norris-1825-chart.png \
    --mode dark --threshold 100 --join 14 --closing 3 \
    --blank-box "2000,660,2180,672;2101,672,2110,830" \
    --tolerance 1 --bbox 2000,670,2180,830 --height-km 2.28 --centre=3.847,-54.108

# Terre de Davis — an OPEN coast (trace_coast.py, not trace_outline.py):
# Vaugondy's shore placed by his own graticule, the lettering and the
# graticule's lines painted out; Moll 1701's islet carried across
python3 scripts/trace_coast.py terre-de-davis --chart vaugondy-1750 \
    --image ~/scratch/charts/davis/vaugondy-1750.jpg \
    --bbox 690,3060,960,3330 --land 700,3320 --blank-box 848,3115,1035,3218 \
    --islet-chart moll-1701 --islet-image ~/scratch/charts/davis/moll-1701.png \
    --islet 1162,1394 --islet-coast-bbox 1040,1300,1220,1470 \
    --islet-land 1060,1450 --overlay /tmp/davis-overlay.png

# Crocker Land — Peary's dashed shore across a polar graticule: scanned by
# rays from inside the crescent, the graticule's lines ignored
python3 scripts/trace_coast.py crocker-land --chart peary-1907 \
    --image ~/scratch/charts/crocker/peary-1907-detail.jpg \
    --radial 668,770,55,105,10,150 --threshold 180 --rule-width 2 --tolerance 1

# Bradley Land — Balch's two dashed brackets, one --radial spec each
python3 scripts/trace_coast.py bradley-land --chart balch-1912 \
    --image ~/scratch/charts/crocker/balch-1912.jpg \
    --radial "795,1917,15,52,-95,115;765,2052,25,75,-95,118" \
    --blank-box 700,1850,790,1890 --threshold 130 --rule-width 6.5 --tolerance 1.5

npm run geo    # rebuild geometry AND copy it to public/ — both, always
node scripts/check_overlap.mjs groclant   # and check it is not sitting on land
```

Traced outlines live in `src/data/outlines/{id}.geojson`; `build_geojson.py`
prefers one over a blob, so **one island is a complete unit of work**.

**Islands nobody drew** — `scripts/describe_island.py`. Where every chart
draws a dot and the report is text, the report still gives *something*: a
length, a bearing, a high end and a low end, "a group", "three low islands
within one reef". That script lays those facts out as geometry and writes an
outline file like any tracing, marked `described`, with what the report said
in `scale_source` and everything else listed as invented. Done for
`dougherty` (5.5 nm NE-SW, wider at the NE bluff), `emerald` (30 nm NE-SW),
`nimrod` (a group: four islets, count and sizes invented) and `tuanaki` (an
atoll: a reef ring with a passage, its rim widening on the lagoon side at
three islets), and `rupes-nigra`, which no one drew from above: Mercator
draws a cliff in profile, so it is a round rock 46.7 km across from the 33
leagues round his 1595 sheet writes beside it, and `saxemberg`, from
Captain Long's 1809 log as Flinders quotes it (4 leagues NW-SE by 2 1/2
miles, a bluff at the NW end), laid at Lindeman's charted position of 1670
rather than Long's own, 830 km west. Étienne, November 2026, chose "sized, groups as groups" over
sized blobs; the older line below, that an island nobody agreed on should
look vague, still holds for its *coastline*, which is invented here and says
so. The atoll is 60 km across by his choice — at a plausible 25 km it was a
6 px ring at 8x and did not read — the same stand-in size as the reefs'
rock cluster. Something smaller than a few km (Jacquet, half a mile) is
drawn as a reef.

**An island at a pole** cannot be laid out in the script's usual plane, which
scales by cos(latitude); `describe_island.py` switches to an azimuthal plane
above 89.5 and winds the ring by longitude (westward round the north pole,
as d3's own `geoCircle` does). Two things then break downstream, both
handled in `map.ts` for this case only: `geoBounds` reports a ring round the
pole as running from -90 to 90, so the halo's half-height comes from the
radius instead; and the apparent size, measured northward from the centroid
and clamped at 89, would have measured a degree *south* of the pole, so it
measures southward there. `check_overlap` is unaffected.

Check the report before the secondary literature: the
second search found Emerald's captain was Nockells, not Elliot, and that
Jacquet had been placed 265 km off on a 1904 newspaper's word.

**Open coasts** — `scripts/trace_coast.py`. Some phantoms were never islands
on their charts: Vaugondy draws Davis Land as a shore with hatching on the
sea side and nothing behind, which is what Wafer saw from the deck. Closing
it would invent the far side, so it is written as a line with the land on its
right, and the land behind it is shaded on hover.

**The shade is 32 stacked translucent layers, not a gradient or a blur.**
Each layer runs along the shore from one end to the other and closes inland
a little deeper than the last, so all of them overlap at the shore — solid
along its whole length — and they thin out inland. Each layer's opacity is
set so the total at depth x is 0.97 (1 − smoothstep(x)), which leaves the
outermost too faint to read as an edge. The inland edges follow a *smoothed*
shore, not every bay (which made a zigzag), and taper into both ends.
`build_geojson.py` writes only each stretch's two edges — `near` on the
shore, `far` at full depth, and per point the depth fraction where a layer
first clears the shore — and `map.ts` builds the layers, because 32 copies
of the shore took islands.geojson from 310 kB to 1 MB. Depth is `shade_km`
in the outline file if set, else 0.285 of the chord.

Two dead ends, so nobody walks into them again. Linear gradients in screen
space — one across the shore, one along it through a mask — draw a fuzzy
rectangle with straight sides, which is what got called ugly. A blur
(`feGaussianBlur`) can keep the shore hard only by clipping, and wherever
that clip runs through open sea past the shore's ends it shows as a straight
cut; making the fill fade out before the ends removes the cut but leaves the
last fifth of the shore bare. Layers need neither. Pointing at the shade
(the deepest layer) counts as pointing at the island.

The coast is the land-side edge of the hatch band: ink density, the band's
outline split at its two farthest-apart points, and the half nearer `--land`
kept. The sheet's graticule does the georeferencing, from a `graticule` block
in the chart JSON (each line fitted as a quadratic on the engraving, rms
under 1.2 px); `--rule-width` paints those same lines out first, since a
meridian runs within 10 px of Davis Land's north tip. Check the graticule's
reading against the real islands on the sheet before trusting it.

An islet from a second chart keeps its own chart's relation to the shore,
measured in a frame laid on the shore's **chord**: a fraction along it and a
distance seaward of the shore. Not by the local tangent — at 0.72 of
Vaugondy's shore the coast runs due east along the back of a bay, and an
offset "seaward" from there put Moll's islet straight back on the shore.
Moll's islet core is 10 x 6 px, too small for `--islet` (which refuses cores
under 60 px), and does not need sealing: it is simply the pale component
under the seed, stable from grey 90 to 110.

**A dashed shore across a graticule defeats every band threshold**, which is
how Peary drew Crocker Land and Balch drew Bradley Land. The sheet's lines
cut the dashes into pieces, and painting the lines out cuts them again: on
Peary the band came back as whichever fragment lay between two meridians.
`--radial` scans rays from a centre on the shore's concave, land side and
takes the middle of the outermost run of ink on each, skipping the
graticule's own lines and dropping outliers against a running median. One
spec per stretch, so Bradley Land's two brackets — Cook's "distinct break
for 15 or 20 miles" — stay two. Both sheets are polar, georeferenced with
the same `polar` block trace_outline.py reads, fitted by least squares on
the graticule's crossings (`pole_px`, `k`, `lon0`, equidistant on both).
Check the result against what the chart writes: Balch labels Bradley
84 20' to 85 11' and the trace gives 84.35 to 85.21. Widen `--rule-width`
until the trace stops spiking where a line crosses the shore — 6.5 on
Balch, whose lines are thick and fitted to 3 px.

`--edge x,y` and `--parts N` exist for band-traced shores whose drawn coast
is the band's sea-side edge, or which come in pieces.

Headless Chrome renders the real map at 2x for mock-ups (a temporary page in
`public/` that drives the globe from an iframe), but it never captures the
hover transition; force `is-active` and kill transitions for the hover frame.

**Eight extraction modes, because charts differ.** A flat colour wash
(Pizzigano's Antillia is solid red) is picked out by `--mode red|blue|green`.
A *violet* wash needs `--mode magenta`, which is `(R+B)/2 - G`: the Catalan
Atlas draws its sea in blue hatching exactly as dark as the wash and its rhumb
lines in red ink that scores higher on redness than the island does, so
neither `dark` nor `red` separates Brasil at all, while magenta clears both at
7 sigma. Note also that `--mode blue --bright` is the negated blue score, i.e.
*yellow* — that is how Ortelius' Groclandt comes out, no new mode required.
An outlined coast round a pale interior (Canepa) needs `--mode dark` to catch
the ink band, which is then closed and filled — the interior is the same
parchment as the ocean, so it cannot be selected directly.

A **hand-coloured engraving** can defeat every hue mode at once. Hondius washes
Corea pale green and then tints the sea along every coast blue-green too, so
nothing scored above d-prime 0.5. `--mode ink` floods outward from `--seed`
points inside the island and stops at the engraved coastline, which is
continuous where the sea's stipple and hatching are not. Three things to know.
A river drawn from the coast is ink too, and the flood runs up it as a long
inlet unless `--closing` is wider than the river (16 on Corea; at 8 three
rivers came out as inlets). A town symbol or a river that cuts off a peninsula
needs a seed of its own, and so does every islet you want kept. And lettering
written *across* a coast walls off whatever lies beyond it, broken into dozens
of pockets between the strokes that no number of seeds will collect — paint it
out with `--blank-box`, keeping the box clear of the coastline itself.

A **plate with no wash at all, in a toned facsimile** (Seller's Buss, from
Lucas 1898) defeats both colour and the ink flood: the paper reads as dark as
the island, and the relief hatching is too broken to wall a flood from
inside. `--mode density` floods the *sea* in from the frame instead, walled
by the coast band — Seller shades his shore as a thick hatched band, ink
density > 0.35 over 15 px, which no single rhumb line reaches — plus a coarse
core eroded well inside the island to stop leaks. The trap it replaced: a
density threshold on its own needs a window wider than the inlets, and it
filled every harbour the chart is known for. Relief drawn up to the shore has
no band, so `--relief-box x0,y0,x1,y1,r` closes the hills' blank sunlit faces
inside one box only. `--satellites MIN,MAX` keeps the chart's islets, with the
plate path's compactness rule (0.75) to leave the sea lettering behind; the
hand-scaled path then writes a MultiPolygon, scaled on the main island alone.
Its morphology runs at quarter scale; at full size a
120 px closing on a 3000 px crop runs for minutes and was killed twice.

A **woodcut whose interior is as busy as its sea** (Gastaldi's Isola de
Demoni, 1556) defeats the ink flood from both sides. From inside, a hut, a
tree, birds, an archer and long ground strokes running coast to coast cut the
island into 126 pockets; from outside, the sea is wave lines with paper
between them, and the flood walks through the coast wherever its line breaks.
`--mode band` floods from `--seed` inside, walled by the hatching cut hard
against the shore — ink at density > 0.25 over 15 px, which marks that band
and very little else — then `--grow 3` moves the edge out onto the drawn line.
Figures that touch the coast (the tree, the demons) come out as notches, not
holes, so paint them out first. Where the woodcutter drew no coast at all —
the demons stand across Demoni's north shore — `--seal "x,y x,y ..."` draws
band by hand. A seal *is* the outline there, so it is a liberty: say so in
`outline_note`. The flood refuses to finish if it reaches the crop edge.

An **islet left blank inside hatching** whose strokes run out to the open
sea (Ortelius' Los Iardinos, 1589) leaks every brightness threshold: the pale
gaps between strokes connect the islet to the sea at any smoothing. `--mode
ring` closes the ink round each `--seed` and keeps the pale core, the plate
path's sealing applied locally; it is stable across closing radii 2-8 there.
`--islet x,y` is the same sealing for an islet beside an island traced in
another mode (colour, band or ink); `--islet-threshold` sets its ink level,
and a core too big for the 80 px window is retried in a 160 px one. The
first `--seed` is the main island.

An **engraved outline with no wash, crossed by rhumb lines as thin as its
coast** (Seale's Donna Maria Lazara, Anson 1748) defeats `--open`, which
erases the coast with the lines, and `--mode ink`, whose flood stops at every
hatched patch of the interior — it lost the head and the toe, 24 x 22 px of a
35 x 28 px island. `--strip R` on a colour mode (here `dark`) fills holes
*first*, so the outline goes solid while the lines stay lines, and only then
opens with `disk(R)`. And beware a colourist's wash on another copy of the
same plate: it is a brush, not the engraving. On the Geographicus copy the
green dab cuts the toe short and runs over the coast; the engraved line is
the shape.

**Choose the treatment and the source together** where a phantom shares a
place with real land. Thule on a Ptolemaic sheet *is* the island at Iceland's
place, so tracing it there would mean erasing Iceland, as Californie erases
California; the Carta Marina draws Tile and Islandia side by side, so with
that source Iceland stays and Thule moves to where Olaus put it. Étienne chose
the second (October 2026).

An **engraved plate** (Frisland 1562) has neither: land is bare parchment and
so is the sea, so there is nothing to threshold *for*. A chart with a `plate`
block in its JSON takes a different path — the sea is flooded inward from the
border, since its hatch strokes are short and disconnected while the coastline
is continuous, and everything the flood cannot reach is land. Its parameters
live with the chart, not the island, because they describe the plate.

**The hatching round a coast is water, not land.** This is the single biggest
thing to get right on an engraved plate, and it is easy to miss: the flood
stops at the *outer* edge of the hatch band, so every island comes out wearing
its own sea — 14% too much area on Frisland's main island, and far more
proportionally on a small one, since the band is a fixed ~35 px however small
the island. `--reach` strips it back inward *from the sea, through the band
itself*, stopping where the band stops. It has to be measured that way and not
as a fixed erosion: the same convention draws hills inland, so a straight-line
strip eats the interior (it took the northern half of DVI), and a plain
erosion eats a small island whole. `--grow 4` then puts the edge on the drawn
shoreline rather than a few px inside it.

**Islets are drawn open and have to be sealed.** The main island's coastline is
one continuous line, so the flood handles it; a small island's outline has
gaps, and what comes out is its ring of hatching rather than its body. The fix
is to close that ring until it encircles something, then take the pale core
inside — which is the island. Where even that fails, `plate.seeds` in the
chart JSON names a point inside the island by hand. One islet on the Frisland
plate resists everything and is simply absent; that is recorded rather than
faked.

**Lettering in the sea fills exactly like a small island.** "Bmi" came out as a
phantom island between two real ones. Only compactness separates them — real
islets score 0.8–0.98 solidity, labels 0.4–0.67 — so small parts below 0.75
are dropped.

**Some decorations can be painted out and some cannot.** The cartouche, the
great ship and the pencilled shelfmarks are safely blanked before extraction.
The sea monster and three boats touch the coast, so blanking them cuts a
channel and the flood drains the whole island; those are discarded after the
fact by `plate.drop` instead. Check each one: the failure is silent and total.

**An island the plate's own rules cut off** is completed by reflecting the
visible part across the cut. Reflect a wedge and you get an arrowhead, so the
completion is smoothed at 0.18 x the island's width at the cut — and *unioned*
with the original, never substituted for it, or the rounding pulls the drawn
coast in with it.

**Atlas sheets draw real islands oversized, so their scale is not the
island's.** Ortelius' Africa draws Annobón ~8x its real length and São Tomé
and Príncipe ~4x; S. Matheo, at the sheet's scale, is 104 km. That scale is
still what every traced island uses, and Étienne kept it for S. Matheo
(October 2026). The first time it was put to him the question came with no
numbers and he answered at random — so ask it WITH them: the drawn size, the neighbours'
real sizes against their drawn ones, what each option looks like on the
globe, and the precedent. A question he cannot answer is not a gate.

**A landmark fit can turn spacing errors into a rotation.** On Mercator's
Tuscia the five points round Monte Argentario fit at RMS 5 km — across a
20 km cluster — with the chart rotated 35 degrees, on a sheet that is plainly
north-up: Mercator spreads Giglio and Giannutri to twice their real distance,
and a similarity transform can only absorb that as a turn. Check the fitted
rotation against the sheet's own graticule; where they disagree, take scale
and north from the graticule and place by interpolating between the real
neighbours the chart draws.

**Scale and position come from georeferencing where the chart can support it.**
Portolans carry real coastlines beside their invented islands, so landmarks fit
a similarity transform giving km/pixel and the chart's own rotation. Six
landmarks on Pizzigano fitted to RMS 47 km. But that only holds *inside the
surveyed region*: everything west of the Canaries on these charts is imagined,
and extrapolating a transform out there produced a confidently wrong answer
(Antillia east of the Azores). Anchor on the nearest thing the chart actually
drew instead.

**A polar projection needs the `polar` block, not landmarks.** Ortelius and
Mercator draw the Arctic on a polar azimuthal projection whose pole falls off
the sheet, and a similarity transform cannot represent it. At Groclandt's spot
on Ortelius 1570 geographic north lies **54.6 degrees off page-up**, so placing
the island by its centre and an isotropic scale sets it down rotated by that
much. A chart JSON carrying a `polar` block — pole pixel, radial scale k,
reference meridian, law — takes a path that inverts every vertex through the
projection instead. Fit it by least squares on landmarks (twelve on Ortelius,
RMS 208 km; stereographic beat equidistant, 208 against 227).

**A drawing can be upside down.** Fletcher draws Elizabeth Island south-up —
the pool "in the south part" sits at the top, and his map of the region in the
same manuscript is south-up too. `--turn 180` on the hand-scaled path stands it
north-up and records `turned_deg`; that turn is a reading, not a liberty. Any
turn but a half turn writes `size_km_measured` rather than `size_km`, for the
Groclant reason below. Check orientation on every hand drawing.

**`--turn` and `--scale` exist for when the island has to be moved, and both
are liberties.** They rotate and resize about the island's own centre in a
spherical azimuthal-equidistant plane, so a turn is a rigid rotation *on the
ground* rather than in degrees — at 74 N those are very different things. Both
are recorded in the outline as `turned_deg` and `scaled_by` and printed as
"liberties" at trace time, so they cannot be taken quietly. Say why in
`coords_note`.

**The `polar` path deliberately does not emit `size_km`.** That key is a
control: `build_geojson` rescales the island until its latitude span matches
it. But a rotated island's pixel height is not its latitude span, and feeding
the measured size back in inflated Groclant by 35%. It writes
`size_km_measured` instead, and its geometry passes through untouched.

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

**A neatline the coast runs close to will bridge to it.** On Yamada's
Nakanotorishima sketch the north coast passes 14 px from the frame rule; the
closing joined the two, and `fill_holes` then flooded the water between them as
if it were interior. `--blank-rows y0,y1` paints the rule out first.

**Survey stations are symbols, not headlands.** A circle and a triangle drawn
*on* Nakanotorishima's coastline were absorbed by the fill and came out as
warts. `--despeckle N` removes only the residue an opening strips, and only the
pieces under N px, so the rest of the coast is left byte-identical — verify by
diffing against the mask you approved, not by eye.

**Settlement cartouches are labels, not lakes.** Names written on the island
are holes in the colour wash and must be filled.

**A line drawn across an island truncates it, and the result looks like a
coastline.** A paper fold does the same (San Borondón, where the crease
scuffed the wash: above threshold ~140 the southern third vanished behind a
straight chord on the fold). This has now cost time on two charts running — a green rhumb line
over Brasil on the Catalan Atlas, the graticule over Groclandt on Ortelius —
with an identical signature both times. The line depresses the score along its
path, the mask splits, the largest-component step silently discards the
smaller piece, and what comes back is a smaller island **with a straight chord
where the line crossed**, which reads perfectly well as a real coast. The tell
is that *the complete island is the LARGER mask*, which inverts the usual
instinct that a tighter threshold is a safer one. Fixes: enough smoothing to
erase the line (sigma 16 on Brasil, where the extent then stopped moving from
sigma 12 to 24), or a threshold low enough to keep the darkened wash (-45 on
Groclandt, a flat plateau at every sigma). Sweep the parameter and take the
range where the extent stops changing.

**Look at the mask, not the numbers.** Every real fault here was invisible in
the summary statistics and obvious the moment the mask was rendered.

**An island the fit sets on land goes into open water, not just off the
land.** Bellin's lake is not the real one's shape, so the landmark fit put
Maurepas half on the north-east shore and Phélipeaux's end on the Keweenaw.
The first fix searched for the smallest move that cleared land by 3 km, and
Étienne called the result plainly wrong: 3 km is under a pixel even at 8x,
so the islands still read as touching the coast. He asked for each island to
be placed on its own, its arrangement with the others mattering less. The
placement that stuck is the centre of the open water in the island's own
part of the lake, found by maximising its least distance to any shore within
that part: Phélipeaux at the midpoint of the Isle Royale–Keweenaw channel
where Bellin draws it (17 km from both), Maurepas in the north-east quarter
(36 km). Within the part, not the whole lake: unconstrained, the search
carries an island to the widest water, far from where its chart put it.
`check_overlap.mjs` counts a point in a Great Lake as water.

**The map cannot show you an overlap with real land**, so run
`node scripts/check_overlap.mjs <id>`. An island is a thin outline and the
basemap a dark fill, so where the outline crosses a coast it disappears into
that fill and the shape still reads as sitting in water. Groclant was
rendered, inspected and approved three times while lying across Ellesmere.

## Design

```css
--water: #EDEFF0;  --land: #383D40;  --phantom: #74202F;
--phantom-soft: #B08089;  --ink: #16191B;  --rule: #C7CCCF;
```

**Piazzolla throughout** (Huerta Tipográfica), body and display alike,
**self-hosted** from `public/fonts/` with its optical-size axis, so titles and
labels each get the right cut on their own. `--display` is set to
`var(--body)` and kept only as the seam where a display face would go.

```sh
python3 scripts/build_fonts.py   # -> public/fonts/piazzolla-{normal,italic}.woff2 + OFL.txt
```

The script fetches the full files from google/fonts into `~/scratch/fonts`
(not committed, like the chart rasters), keeps weights up to 700 (the default
master is 100 and cannot be moved, so 100-700), the whole optical-size axis,
Latin only and every OpenType feature: 86 + 91 kB. It refuses to write a file
that has lost `smcp` or `onum`. The OFL licence travels with the fonts.

**Why self-hosted: Google Fonts strips small caps and old-style figures** from
everything it serves — checked on nine families. The site uses
`all-small-caps` throughout (labels, nav, lifespans, first lines), so with
Google's files they were faked from shrunk capitals. Piazzolla's own `smcp`
and `c2sc` now draw them. Its old-style figures work too but are a hybrid,
barely different from its default figures (the 9 dips 81 units below the
line, the 1 is 72 shorter), so at text size they read almost as lining.

**No Cyrillic, by choice.** The one or two places it occurs (Ernest-Legouvé's
caption and note) fall back to Georgia. Étienne, November 2026: "having an
exception like Georgia for the 1-2 places where it occurs is totally fine."

**How it got here, over the apostrophe.** Spectral, the face from August,
draws ’ as a straight tapered wedge that reads as a prime (′) — "I hate the
apostrophe" — and has no alternate in any of its six stylistic sets. The first
replacement was Newsreader (Production Type), chosen from Spectral, Spectral
with only ’ borrowed from Newsreader, Literata, Source Serif 4, Crimson Pro
and Alegreya. Newsreader has no small caps or old-style figures even in its
full files, and Étienne was "not attached" to it, so six faces that have both
were rendered self-hosted at their real sizes: Brygada 1918 (93 kB),
Baskervville (95), Alegreya (142), Piazzolla (189 before trimming the weights
to 700), Source Serif 4 (291) and Literata (318). The recommendation was
Brygada 1918; he picked Piazzolla: "seems to be the nicest". Specimens are
easy to rebuild: a static page in `public/`, rendered at 2x with headless
Chrome — delete it afterwards.

**A second family was tried and rejected** in August 2026 — don't re-propose
one casually. Faune (Alice Savoie / Cnap) was picked in the first design
session on an unverified premise: the notes described it as commissioned for
the Muséum national d'Histoire naturelle and as drawn from natural-history
engraving. It was in fact commissioned by the Centre national des arts
plastiques with the Imprimerie Nationale, and — decisively — its upright is a
flared humanist **sans**, not the engraved serif the story implied. Against
Spectral's serif body it read as a clash. EB Garamond, Playfair Display,
Bodoni Moda, Libre Bodoni and Theano Didot were compared on the real site;
Spectral alone won (and was itself replaced, above, for one glyph rather
than for its character).

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

**Live in French at <https://ilesfantomes.etiennefd.com/> and in English at
<https://phantomislands.etiennefd.com/>** since 21 November 2026. Vercel,
imported from the GitHub repo, redeploys on every push to `main`. Build
`npm run build`, output `dist`, no adapter (static).

### Hosting and URLs

**Two subdomains of etiennefd.com, one per language, each serving from its
root**: `ilesfantomes.etiennefd.com/iles/antillia/`,
`phantomislands.etiennefd.com/iles/antillia/`. Étienne, November 2026, chose
subdomains over buying a domain (`ilesfantomes.com` and the rest were free;
`phantomislands.com` was taken), and clean URLs over keeping `/fr/` and `/en/`
after the hostname. The path stays French in English too (`/iles/`, `/liste/`),
following the one-canonical-slug decision.

- **The build is unchanged**: it still writes `dist/fr/` and `dist/en/`.
  `vercel.json` does the rest, by host: it rewrites `/…` on each subdomain onto
  its folder, redirects (308) any `/fr/…` or `/en/…` path to the clean URL on
  the right host, and sends the old `atlas-des-iles-fantomes.vercel.app`
  addresses to the new hosts, so links shared before the move still work.
- **Only the production build links that way.** `src/lib/hosts.mjs` switches on
  `VERCEL_ENV=production` (or `ATLAS_SPLIT_HOSTS=1` locally). Dev,
  `npm run preview` and Vercel's preview deployments keep one host with `/fr/`
  and `/en/`, so **every internal link goes through `url(lang, path, from)`**,
  never a hand-written `` `/${lang}/…` ``: same-language links come out as
  `/liste/`, cross-language ones as the other host's full address. Links inside
  a story's markdown are written relative (`../frisland/`), which works in
  both layouts.
- **Vercel applies a rewrite only where no file exists**, so the production
  build must write no root `index.html`, or `/` would serve Astro's redirect
  page instead of the French home. That is why `src/pages/index.astro` is gone
  and `astro.config.mjs` adds the `/` → `/fr/` redirect outside production
  only.
- **DNS**: etiennefd.com's zone is at WHC (`ns*.whc.ca`). Each subdomain is a
  CNAME to the same Vercel target, and both are listed under the project's
  Settings → Domains, connected to Production. Vercel picks the site by
  hostname, so the shared target is normal.

Checking it: `ATLAS_SPLIT_HOSTS=1 npx astro build --outDir <tmp>` shows the
production links locally, but the host rules run only on the real hosts — not
under `npm run dev`, not on preview deployments, not in `vercel dev`. Verify
with `curl` against the live subdomains after each change to `vercel.json`;
if the Mac's resolver has not caught up with a DNS change, pin the address
with `--resolve host:443:<ip from dig>`.

Two things went wrong during the move, both worth not repeating:

- **A permanent redirect is remembered by the browser.** The old config sent
  `/` to `/fr/` with a 308 and the new one sends `/fr/` back to `/`, so a
  browser that saw the old redirect on a new host would loop. Hence: don't
  open a new host until the deploy that serves it is live. Link previews
  (Slack, iMessage) also cache what they fetched; a stale French preview of
  the English site was that, not a bug.
- **Several sessions share this checkout, and a force-push to `main` lost a
  commit.** The subdomain commit was pushed at 15:43 and overwritten at 15:45
  by a force-push from elsewhere, which put production back on the old config
  — both hosts redirected to French and every clean URL returned 404. It was
  re-applied as `e0d51e8`. Never force-push `main`; when a push is rejected,
  `git pull --rebase`, and after pushing, check `git log origin/main` still
  holds the commit.

### The atlas

- 43 islands with coordinates; 14 attested, 23 approximate, 6 conjectural
- 33 outlines from depictions (three of them open coasts, one of four
  islands, and `ile-de-sable` lifted from a digital coastline rather than
  traced), 6 shapes built from
  reports (`dougherty`, `emerald`, `nimrod`, `tuanaki`, `saxemberg`, and
  `rupes-nigra` from Mercator's text — see *Islands nobody drew*), 3 reefs (`jacquet` among them), and `aurora` as three
  blobs at attested positions; 30 chart records in `scripts/charts/`
- `californie` and `coree` replace the basemap rather than drawing over it
- **31 of 35 written in French** — all 28 blog posts imported verbatim,
  47,269 words, with the 36 map plates from the posts in `public/iles/`
- **8 written in English** (`aurora`, `bermeja`, `frisland`, `groclant`,
  `ile-des-demons`, `kianida`, `los-jardines`, `tuanaki`), so 23 islands sit
  in `translated` state there
- 2 partial drafts (`nakanotorishima`, `nimrod`) with notices
- **No island is a default blob any more** (November 2026). The five left
  became shapes built from their reports, four of them moved onto primary
  sources on the way: `jacquet` (Purdy's 46 55 N 39 30 W, ~265 km east of
  a 1904 newspaper's position, and now a reef), `emerald` (the island, not
  Nockells' ship), `nimrod` (Eilbeck's figures) and `tuanaki` (the charted
  26 30 S 160 25 W, ~400 km SW, a 60 km atoll). `dougherty` stayed put. The
  default blob is still what a new island gets until it is traced or
  described. The four moved islands' coordinate notes were rewritten from
  the primary text; the old ones followed secondary sources. Two notice
  slips were fixed in the story files the same way: Émeraude's captain is
  Nockells, not Elliot, and Keates saw Dougherty in 1859, not 1860.
  Jacquet's "1728" stays in its notice and its hover date, unconfirmed —
  the earliest evidence found is Bowles' map of 1779.
- Traced: `antillia` (Canepa 1489), `frisland`
  (1562 plate, 23 parts — the first MultiPolygon), `bermeja`
  (19th-c. English Gulf chart), `nakanotorishima` (Yamada's own 1908 survey
  sketch — see below), `kianida` (Ulm 1482, fully georeferenced from the
  sheet's landmarks), `hy-brasil` (Catalan Atlas 1375 — a circle, 0.992 aspect
  and 3.5% out of round, which is the point of that island) and `groclant`
  (Ortelius 1570, on a fitted polar projection, then moved into Baffin Bay),
  `californie` (Vinckeboons c. 1650) and `coree` (Teixeira 1595, traced from
  Hondius' re-engraving; the real Korea is erased whole) and `mayda` (the
  gilded crescent "Insula de mam" on the Catalan Atlas, Hy-Brasil's panel)
  and `saint-brendan` (San Borondón, from a c. 1760 Canaries chart,
  georeferenced on the seven real islands) and `buss` (Seller's 1670
  draught, placed from his own 1673 chart), and `juan-de-lisboa` and
  `dos-romeiros` (both from Linschoten 1596, georeferenced on the Mascarenes
  and Madagascar), and `ile-des-demons` (Gastaldi 1556, the story's plate),
  and `saint-mathieu` (Ortelius' Africa 1570, anchored on Annobón — which
  moved it ~880 km east of the story's "1000 km north of Ascension"), and,
  unreviewed, `bacalao` (Gastaldi 1556 again, moved off the real bays it is
  drawn over), `los-jardines` (Ortelius' Maris Pacifici 1589, at Saavedra's
  1528 latitude rather than the 21 N position struck in 1973) and `zanara`
  (Mercator's Tuscia 1589, its origin), and `elizabeth` (Fletcher's own
  drawing from Drake's voyage, turned north-up, 48 km), and `thule`
  (Olaus Magnus' Carta Marina 1539, moved off Iceland, which stays), and
  `ile-aux-vaches` (Piri Reis 1513, with its ring of rock dots as islets),
  and `terre-de-davis` (Vaugondy 1750's open shore, with Moll 1701's islet),
  and `crocker-land` (Peary's own 1907 map, its dashed shore) and
  `bradley-land` (Balch 1912, the story's plate, in two stretches), and
  `maria-de-lajara` (Seale's engraving of the Covadonga's galleon chart,
  Anson 1748, 52 x 68 km at the sheet's scale, position unchanged), and
  `phelipeaux-et-pontchartrain` (Bellin 1744, the four islands Charlevoix
  named in Lake Superior, as one entry; two moved off real land into open
  water, the first island added with no story), and Antillia's neighbours
  `satanazes` (Pizzigano 1424, its name cartouches filled as land) and
  `royllo` (Canepa 1489's "Roillo"), each placed by its offset from
  Antillia on its own chart, no story yet, and `iles-de-la-compagnie-royale`
  (Arrowsmith 1814, the sheet Bellingshausen searched by, three islets at
  the sheet's scale, 13 x 28 km the largest; no story), and `ile-de-sable`
  (Sandy Island: the World Vector Shoreline's polygon from GSHHS 2.2.0,
  6.3 x 27.6 km, unchanged; no story; Natural Earth's own copy of it dropped
  from the basemap), and `pepys` (Moll's 1711 inset of the drawing from
  Cowley's voyage, two islands with Admiralty Bay between them, 50 km across
  by Étienne's choice, placed off Patagonia by Moll's main map; no story),
  and `thompson` (George Norris's own chart from the Sprightly's log, 1825,
  printed in the Geographical Journal in 1928, 2.5 x 2.3 km at its scale,
  46 km NE of Bouvet by its offset on that chart; no story). Bouvet was not
  on the globe at all, Natural Earth 50m having no polygon for it, so it is
  added from land-10m by `build_basemap.mjs` (see Traps)
- **Île des Démons is placed by its story, not its charts.** The charts put it
  off the northern tip of Newfoundland, near Quirpon, and Gastaldi draws it
  ~470 km tall — read against Terra Nova on the same sheet it is nearly
  Newfoundland's size, and no size from 47 to 470 km fits near Quirpon
  without moving east of the Strait of Belle Isle. Étienne, October 2026:
  *"based on the story it's near harrington harbour and is very small."* So
  it is 10 km tall off Harrington Harbour on the Côte-Nord, where tradition
  puts Marguerite de La Rocque's marooning. He said the shape matters less to
  him than that; Gastaldi's was kept because it was already traced. At 10 km
  it is 3 x 4 px even at full zoom — a dot inside its halo, as Bermeja is.
- **Saint Brendan's island is one entry, placed in the Canaries.** It was
  briefly split in October 2026 into Mercator's placement west of Ireland and
  the Canarian San Borondón, on the claim that they were two phantoms sharing
  a name. The sources say otherwise — one legendary island, localised in the
  Canaries and moved north by Mercator — so the split was undone and the
  Canarian position kept, by Étienne's choice. Check that a "second island"
  is a second legend, not a second placement, before adding one.
- Map verified in production: globe mounts, 634 landmasses, 34 islands, hover,
  tap-to-reveal on touch, rotate, tilt, zoom to 8×, reset. Rechecked on the
  new hosts in November 2026: globe mounts with 34 islands linking to
  `/iles/…`, map data, fonts and plates load, every redirect lands.

### Known blemishes — fixed October 2026

- **Story images that do not exist are skipped, not shown broken.** The story
  template checks each frontmatter image against `public/` at build time,
  drops a missing one and prints `[stories] <id>: missing image …, figure
  skipped` in the build log. Two plates are missing today and their pages show
  no figure until they arrive: `/iles/nakanotorishima-pacifique-1941.png`
  (`fr/nakanotorishima`) and `/iles/nimrod-perthes-1906.png` (`fr/nimrod`).
  Hy-Brasil's, the third once listed here, was already resolved by the import.
- **`/` redirects** from `vercel.json` (on hosts other than the two
  subdomains), instead of Astro's static
  redirect page, which is a two-second meta refresh. That page still builds and
  is what `npm run preview` serves.
- **`site` is the French host**, `ORIGIN.fr` in `src/lib/hosts.mjs`.

## Next, roughly in order

1. ~~Migrate the 28 stories~~ **Done**, by `scripts/import_posts.py`, which
   read the WordPress REST API rather than the rendered page so the prose
   arrived verbatim — no model in the loop. **That API no longer exists**: the
   blog is now the static archive, so `fetch()` cannot run as written and the
   files in this repo are the working text. `parse()` still handles the
   archive's markup (its post bodies keep the same `<p>`/`<ul>` structure;
   checked November 2026 on six posts), so a one-off re-import would need
   only a new fetch that takes the post body out of
   `/archive/cartographier/{slug}/` — title and date come from the page too.
2. **Trace real outlines** — see *Adding an island*. Thirty-one done:
   `antillia`, `bermeja`, `nakanotorishima`, `frisland`, `kianida`,
   `hy-brasil`, `groclant`, `californie`, `coree`, `mayda`, `saint-brendan`,
   `buss`, `juan-de-lisboa`, `dos-romeiros`, `ile-des-demons`,
   `saint-mathieu`, `bacalao`, `los-jardines`, `zanara`, `elizabeth`, `thule`,
   `ile-aux-vaches`, `terre-de-davis`, `crocker-land`, `bradley-land`,
   `maria-de-lajara`, `phelipeaux-et-pontchartrain`, `satanazes`, `royllo`,
   `iles-de-la-compagnie-royale`, `ile-de-sable`, `pepys`, `thompson`. The rest are built from their reports or drawn as
   reefs (November 2026), so no default blob is left; a new island starts as
   one. An island nobody agreed on the shape of should still look vague in
   its coastline, which a described shape invents and says so.
   **`aurora` is three placeholder blobs at the Atrevida's three positions**
   (October 2026), not a tracing: a time-boxed search found no depiction with
   a coastline — the 1800 Spanish hydrographic chart, the story's Spruner
   plate and every atlas sheet draw dots. The positions are firm, from
   Espinosa y Tello's *Memorias* (1809), longitudes west of Cádiz. The one
   lead left is Museo Naval Ms. 634 ff. 11r–14v, the Atrevida's own extract;
   a sketch there would replace the blobs.
   **The other six blobs were searched the same way in November 2026**, and
   only `maria-de-lajara` had a coastline. A second search later that month
   reached the leads listed below and found none either, but did find the
   reports' sizes, so the five became shapes built from those reports —
   see *Islands nobody drew*. What follows is the first search's record. `dougherty`, `nimrod`, `tuanaki`
   and `jacquet` are dots or rings on every chart checked (Bartholomew 1905,
   Davis' Nimrod track 1909, Admiralty 5098 of 1914, Stieler, the Stanford
   Polynesia, Bowles 1779, the Dépôt's Cartes réduites of 1738-1786, Bellin
   and Sayer & Bennett on the Banks, which stop west of Jacquet). `emerald`
   is a hachured stock small-island figure on the Admiralty's Chart of the
   South Polar Sea (1839, Rumsey 364749, 23 x 49 px), not drawn from the
   report. Leads still unreached: Le Gros' lost sketch of Jacquet's profile
   (Norie/Imray archives, Jersey Heritage); the Admiralty's *Pacific
   Islands* vol. 3 (1900) for Stannard's own words; Stommel's *Lost
   Islands* (1984), lending-only; the Admiralty's Cook Islands charts.
   Outstanding on `antillia`: its scale is inherited from a Pizzigano
   measurement because `scripts/charts/canepa.json` has no landmarks yet.
   Outstanding on `frisland`: longitude is chosen, not derived — the Zeno map
   fits at RMS 231 km and cannot support one.
3. **Add the islands that have no story yet** — gradually, and never as a
   blob: each arrives traced or built from its report. Étienne's list,
   November 2026 (from his Obsidian note, revised): **yes** — ~~Satanazes~~ and
   ~~Royllo~~ (done November 2026, from Pizzigano 1424 and Canepa 1489),
   ~~Îles de la Compagnie Royale~~ (done November 2026, from Arrowsmith
   1814; Espinosa y Tello's 1812 original is in Spain's Biblioteca Virtual
   de Defensa, unreachable from here, and worth comparing if Étienne gets it), ~~Île de Sable~~
   (Sandy Island, done November 2026, from the World Vector Shoreline's
   polygon, chosen over the 1908 Admiralty chart), ~~Phélipeaux et Pontchartrain~~ (done November 2026, from
   Bellin 1744, on the Great Lakes `scripts/build_lakes.py` cuts out of the
   land), ~~Rupes Nigra~~ (done November 2026, the rock only, round from
   Mercator's 33 leagues; Étienne weighed leaving it out, as cosmology
   rather than a charting error, and kept it for the story; the four polar
   islands are not drawn, since they reach 78 N across the real Arctic),
   ~~Saxemberg~~ (done November 2026, Long's 1809 description at
   Lindeman's 1670 position, both by Étienne's choice), ~~Pepys~~ (done
   November 2026, from Moll's 1711 inset, two islands, 50 km),
   ~~Thompson~~ (done November 2026, from Norris's own 1825 chart, 2.5 km,
   46 km NE of Bouvet), Sannikov Land, Isla Grande (La Roché, 1675); **probably** —
   Middle Island (Powell 1822), Colunas, Willoughby's Land and Matsyn;
   **not sure** — Candyn, Récif Schjetman, Sarah Ann, Podesta and Yosemite
   Rock, Petermannland, Victoria (Pacific); **maybe**, for the story they
   would carry — Taprobane, and Wak-Wak (from the *Thousand and One
   Nights*), which was looked at in November 2026 and **skipped**: on
   Idrisi's maps Waqwaq is chiefly *land*, the far end of the southern
   continent he stretches east from Africa past Sofala (the round world map,
   MS Pococke 375, names no Waqwaq island at all); three islands labelled
   *wāqwāq* appear only on the sectional maps (seen in Miller's 1928
   reconstruction), as stock ovals beside al-Sīla, east of China. No shape
   to recover and nothing to place the coast against, so it is a story
   rather than an island.
   He gives a premium to an island with a legend or an inventor behind it
   over the 19th-century captain's speck. **No** to Gillis Land, almost
   certainly Kvitøya, and to Jave la Grande. Wikipedia's list has grown since his note; the
   entries not on it were compared in November 2026.
4. Verify the conjectural coordinates against Étienne's own research.
5. Story-page inset map (same component, zoomed to one island).
6. ~~A real domain~~ **Done**, as two subdomains of etiennefd.com (see
   *Hosting and URLs*).

## Open questions

- **Whether the real land should ghost through in pale grey at rest**, hidden
  on hover, so the disagreement can be seen. Étienne raised it in September
  2026 and has not decided. Arguments made at the time: it inverts the hover
  convention, which everywhere else *adds* rather than removes; it only
  applies to two islands out of thirty-four, so it is discoverable by
  accident; it needs a fifth value in a four-value palette; and at world zoom
  it is invisible. Alternatives floated were ghosting *on* hover instead, or
  putting the comparison on the story page inset rather than the globe.
- **The map's resting weight.** Every island is now an unfilled outline, by
  decision — the map is a chart of coastlines rather than a field of shapes,
  and at world zoom nothing is solid. That was the answer to the older
  "possibly too quiet" question, and it went further in that direction rather
  than back. Worth re-examining once more islands have real outlines, since a
  traced coastline reads very differently from a placeholder blob.
- `kianida` (Black Sea) and `zanara` (Tyrrhenian) sit in enclosed seas, which
  reads oddly on a world map framed for oceans.
- Whether the reefs post splits into separate island entries or stays one
  story covering a region.

## Working preferences

Étienne is technical and writes for *Asterisk*, *Works in Progress* and his own
Substack. Explain reasoning, flag uncertainty rather than papering over it, and
prefer showing a diff to handing over a pile of files.

**Verify; don't assert.** Measure rendering and performance in the real
browser. The winding-order bug was invisible until the map was screenshotted;
a font specimen praised a face that had silently fallen back to Times; a zoom
drift was "measured" in the wrong coordinate space and the number was
meaningless. Computed styles and `geoArea` beat confident description.

**He decides.** *"I decide, not you."* Present the options, measure them
honestly, recommend one — then wait. Don't remove or replace an option he is
still weighing, however conclusive the data looks. This applies to anything
where taste is in play, which on this project is most things.

**Land one step, show it, stop.** Don't chain research into a change into a
commit. The full version of this, and the quotes behind it, is in *Adding an
island* — it is the working rhythm for the whole project, not just for
tracing.

**Corrections are cheap; defending a wrong claim is not.** Twice I told him a
chart was at fault when the fault was mine, and he had to insist. If he says
the drawing shows something, look again before disagreeing.
