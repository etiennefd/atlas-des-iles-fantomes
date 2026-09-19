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
- **A survey of the island beats a chart depiction of it**, where one exists.
  `nakanotorishima` is traced from the sketch Yamada Teizaburō signed in 1908
  as its discoverer: contour lines, four named hills and flats, transects and
  marginal figures in *ken*. That is not the most influential depiction and is
  meant not to be — for an island that never existed, the invention drawn in
  detail by its inventor is a better source than anyone else's copy of it.
- **An island's shape comes from the most famous or influential depiction**,
  not the earliest, and *not* the plate that happens to illustrate its story —
  those were picked as illustrations and Étienne does not endorse them as
  sources. For Antillia the two coincided anyway: Pizzigano 1424 is both first
  and the one everyone copied. Where they differ, influence wins.

## Data model

### Island (`src/content/islands/{id}.yaml`)

Filename is the id. `kind` drives rendering:

- `island` — a polygon, or a MultiPolygon where the source draws the island's
  satellites too (`frisland` has 23 parts)
- `reef` — a Point; a small dot, filled even at rest, always haloed
- `misdrawn` — a *real place wrongly charted* (Corée, Californie). **Currently
  rendered exactly like `island`**, at rest and on hover. It used to be
  outline-only so the true coastline showed through underneath, which was the
  clearest visual statement of the project's thesis — but every island is an
  outline at rest now, and Étienne has explicitly suspended the question:
  *"The misdrawn category I haven't decided what to do with yet, so don't make
  any design choices."* Don't invent a treatment. The open question is that
  hover fills them opaquely, hiding the real coastline they exist to show.

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

## Adding an island

Done seven times: `antillia`, `bermeja`, `nakanotorishima`, `frisland`,
`kianida`, `hy-brasil`, `groclant`. Read
this before the eighth — it is written so Étienne does not have to explain the
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

### The four worked examples

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

# Groclant — a polar projection, and an island moved because it hit real land
python3 scripts/trace_outline.py groclant --chart ortelius-1570 \
    --image ~/scratch/charts/ortelius-north.jpg \
    --mode blue --bright --threshold=-45 --smooth 3 --closing 5 \
    --tolerance 1.5 --bbox 980,100,1800,740 \
    --turn -32.5 --scale 0.91 --centre=-67.75,73.95

npm run geo    # rebuild geometry AND copy it to public/ — both, always
node scripts/check_overlap.mjs groclant   # and check it is not sitting on land
```

Traced outlines live in `src/data/outlines/{id}.geojson`; `build_geojson.py`
prefers one over a blob, so **one island is a complete unit of work**.

**Four extraction modes, because charts differ.** A flat colour wash
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
coastline.** This has now cost time on two charts running — a green rhumb line
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

- 34 islands with coordinates; 10 attested, 14 approximate, 10 conjectural
- 7 traced outlines, 27 placeholder blobs; 8 chart records in
  `scripts/charts/`
- **31 of 34 written in French** — all 28 blog posts imported verbatim,
  47,269 words, with the 36 map plates from the posts in `public/iles/`
- English has only `hy-brasil`, so 30 islands sit in `translated` state there
- 2 partial drafts (`nakanotorishima`, `nimrod`) with notices
- Geometry is placeholder blobs except `antillia` (Canepa 1489), `frisland`
  (1562 plate, 23 parts — the first MultiPolygon), `bermeja`
  (19th-c. English Gulf chart), `nakanotorishima` (Yamada's own 1908 survey
  sketch — see below), `kianida` (Ulm 1482, fully georeferenced from the
  sheet's landmarks), `hy-brasil` (Catalan Atlas 1375 — a circle, 0.992 aspect
  and 3.5% out of round, which is the point of that island) and `groclant`
  (Ortelius 1570, on a fitted polar projection, then moved into Baffin Bay)
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
2. **Trace real outlines** — see *Adding an island*. Seven done: `antillia`,
   `bermeja`, `nakanotorishima`, `frisland`, `kianida`, `hy-brasil`,
   `groclant`. Next best candidates are
   `californie` (a long N–S sliver) and `coree` (a peninsula), the two
   remaining where a placeholder blob actively misleads. Both are `misdrawn`,
   and Étienne has flagged that they will want the fictional outline to
   *replace* the real land rather than sit on top of it — that mechanism does
   not exist yet and is a separate piece of work from tracing them.
   Everything else can stay a blob indefinitely; an island nobody agreed on
   the shape of should look vague.
   Outstanding on `antillia`: its scale is inherited from a Pizzigano
   measurement because `scripts/charts/canepa.json` has no landmarks yet.
   Outstanding on `frisland`: longitude is chosen, not derived — the Zeno map
   fits at RMS 231 km and cannot support one.
3. Verify the conjectural coordinates against Étienne's own research.
4. Story-page inset map (same component, zoomed to one island).
5. A real domain (Vercel is serving `atlas-des-iles-fantomes.vercel.app`
   today; point `site` in `astro.config.mjs` at whatever it becomes).

## Open questions

- **How `misdrawn` should render.** Suspended by Étienne in September 2026;
  they draw as ordinary islands meanwhile. The specific problem: hover fills
  them opaquely, which hides the real coastline they exist to show against.
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
