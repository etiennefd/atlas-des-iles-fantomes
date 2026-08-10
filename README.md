# Atlas des îles fantômes

A bilingual literary atlas of islands that were believed to exist and did not.
Astro, static output, French and English.

Live at <https://atlas-des-iles-fantomes.vercel.app/fr/>.

Working notes and decisions: [`CLAUDE.md`](./CLAUDE.md). Coordinate
provenance: [`COORDINATES.md`](./COORDINATES.md). [`PLAN.md`](./PLAN.md) is the
original build plan, kept as history — several of its decisions were later
overturned, so don't read it as a spec.

## Run it

```sh
npm install
npm run dev      # http://localhost:4321 → redirects to /fr/
npm run build
```

## What's here

The content structure, the story page, and the map (see below). 34 islands
have coordinates; 3 stories are written, 2 are partial drafts.

Five of the islands exercise every rendering state:

| Island | State (fr) | State (en) | Why it's here |
|---|---|---|---|
| `hy-brasil` | available | available | The worked example. Real notice from the blog. |
| `crocker-land` | available | translated | Many-to-many: one story, two islands |
| `bradley-land` | available | translated | ″ |
| `coree` | planned | planned | `kind: misdrawn` |
| `thule` | planned | planned | Planned state, and a BCE date |

## Adding a story

1. `src/content/islands/{id}.yaml` — one file per island, filename is the slug.
2. `src/content/stories/fr/{slug}.md` — frontmatter as in `hy-brasil.md`.
3. That's it. States, the counter, and the list page all derive automatically.

Two conventions when migrating from the blog:

- The `//` scene breaks become `***` (a markdown `hr`), which renders as a
  centred `//`.
- The bullet block above the story goes in `notice:` as `{label, body}` pairs.
  Invent labels freely — the schema doesn't constrain them.

## Fonts

**Spectral throughout**, from Google Fonts — body and display both. No
self-hosted fonts, nothing in `public/fonts/`. Spectral carries the site on
real small caps, a proper italic and three weights; hierarchy comes from size,
weight and small caps rather than from a second family.

`--display` still exists as a separate token, set to `var(--body)`. It is the
seam where a display face would go, so adding one later is a one-line change.

### What was tried, and why not

A display face was evaluated and rejected. The candidates were Faune, EB
Garamond, Playfair Display, Bodoni Moda, Libre Bodoni and Theano Didot, all
compared on the real site with a temporary `?font=` switcher.

**Faune** (Alice Savoie / Cnap) had been chosen in the very first design
session and written into the notes as "drawn from natural-history
illustration… a face for cataloguing specimens." Two things were wrong with
that. It was described as commissioned for the Muséum national d'Histoire
naturelle; it was actually commissioned by the Centre national des arts
plastiques with the Imprimerie Nationale, and the natural-history thread is
its *source material* (Buffon, the Description de l'Égypte), not a client. And
the face the story implies — engraved, serifed — is not what Faune is: its
upright is a flared humanist **sans**. Set above Spectral's serif body it read
as a clash rather than a pairing.

Faune's italic is genuinely distinctive and was the strongest argument for
keeping it, but not enough to justify a second family, 83 kB, and a CC BY-ND
credit obligation in the footer.

If a display face is ever revisited: it needs a **real italic cut**, because
map labels are italic by the hydrography convention and a synthesised oblique
looks wrong on a high-contrast face. That alone ruled out Theano Didot, which
ships Regular only.

## Deploy

Live at <https://atlas-des-iles-fantomes.vercel.app/fr/>, on **Vercel**,
imported from `etiennefd/atlas-des-iles-fantomes`. Every push to `main`
redeploys. Static output, no adapter — framework preset Astro, build
`npm run build`, output `dist`. There is no deploy config in the repo because
none is needed.

Vercel serves at the root of a subdomain, which matters: everything here
assumes root paths (`/data/land-50m.json`, `/iles/…`, `/fr/…`). A host that
serves from a subdirectory — GitHub Pages under `/atlas-des-iles-fantomes/` —
would need `base` set and every one of those paths rewritten.

Note that Vercel's Hobby plan is for non-commercial use. If the atlas ever
becomes commercial, that needs Pro, or a host without the restriction.

## The map

`src/components/PhantomMap.astro` + `src/components/map.ts`. An orthographic
globe, D3, ~35 kB gzipped. Hover (or first tap on touch) reveals the island's
name and lifespan; click navigates. Wheel/pinch zooms to 8x.

Dragging turns the globe: horizontally it never runs out, and vertically it
tilts, so the poles are reachable. That is the reason for the globe — the
Southern Ocean phantoms sit in a ring you can look straight down at, and the
Arctic ones likewise. `HOME_LON`/`HOME_LAT` set where it opens and returns to.

A globe shows one hemisphere, so roughly half the atlas is behind the earth at
any moment. `liste` is the complete index.

### How position works

d3-zoom supplies the scale and the raw gesture deltas; **position is entirely
ours**. Its own `x`/`y` never reach the transform and `translateExtent` is
unbounded, because both axes are rotation and any correction we made would be
overwritten by the next event's transform. The SVG transform is
`translate(offX, offY) scale(k)` with the scale anchored at the frame centre —
without that anchor it grows away from the origin and the globe walks off to
the top left.

The far hemisphere is culled explicitly (`geoDistance > π/2`): `projection()`
still returns a point for a location behind the globe, mirrored onto the near
disc, so without the test you can hover an island through the earth.

### Zoom anchoring

Zoom holds the point under the cursor, and the correction is made in
**degrees, not pixels**. Two traps, both of which look like "zoom is slightly
drifty" until measured:

- Nudging longitude also moves a point *vertically*, and the vertical fix
  moves it back horizontally. One pass cannot converge; the loop iterates
  until the error is under a quarter pixel.
- Pixels-per-degree is not a constant — on a sphere it falls away towards the
  limb — so a pixel-scaled nudge overshoots and the loop oscillates. Asking
  `invert()` what is actually under the cursor and shifting by the difference
  in longitude converges in two or three passes.

Within ~75° of the centre the cursor holds to a few pixels (measured 4–10 px
over six successive zoom steps). Past that the globe is degenerate — one pixel
spans a huge angle and `invert()` is ill-conditioned — so it falls back to
scaling about the middle of the disc.

Because rotation changes the geometry, every path is regenerated per frame
(coalesced to one reprojection per rAF; measured 60 fps while dragging).
Island anchors and label sizes come from `geoCentroid`/`geoBounds` rather than
`path.centroid`/`getBBox`, which both misbehave for a shape the antimeridian
has cut into two pieces at opposite edges of the frame.

### Basemap resolution

**Natural Earth 50m**, everywhere, every frame. 110m — the usual default —
contains no small islands at all: no Balearics, no Lesser Antilles, no Azores,
no Malta, no Bermuda, which is a poor look on an atlas about islands. 50m has
them, at 169 kB gzipped against 110m's 20 kB, and it holds 60 fps while
dragging (median 16.7 ms, measured in-browser at world zoom and at 5x).

10m was tried and rejected: **9 fps**, and no amount of culling helps, because
the visible set still contains continents. An idle-swap scheme — coarse while
moving, fine when stopped — was also built and rejected: it worked and held
60 fps, but the pop between resolutions is unpleasant to use.

> If you ever revisit 10m, note that **`world-atlas`'s `land-10m.json` is
> broken as distributed**: it carries 3 degenerate zero-area polygons that
> d3-geo reads as covering the whole sphere, so total land area computes to
> 41.3 sr against a true ~2.9 and the globe renders as a solid disc. Drop
> those 3 of 4061 polygons and it's fine.

Only `land-50m.json` is committed. To get the others back:

```sh
cp node_modules/world-atlas/land-110m.json public/data/
```

Geometry is **placeholder blobs**, generated from each island's coordinates:

```sh
python3 scripts/build_geojson.py
cp src/data/islands.geojson public/data/islands.geojson
```

Re-run that after editing any island's `coords`. Replace blobs with traced
outlines one at a time — nothing else depends on the shapes.

### Winding order

d3-geo reads polygons spherically. A ring wound the wrong way renders as *the
whole planet minus that island* — a solid disc over the map. The build script
forces clockwise. **QGIS and geojson.io export counterclockwise**, so flip
anything you trace. Check with:

```js
import { geoArea } from "d3-geo";        // > 2*PI means inverted
```

## Next

1. Verify the conjectural coordinates (see COORDINATES.md).
2. Migrate the 28 stories.
3. Trace real outlines, starting with californie, coree and frisland — the
   three where a blob actively misleads.
