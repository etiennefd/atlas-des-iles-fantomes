# Atlas des îles fantômes

A bilingual literary atlas of islands that were believed to exist and did not.
Astro, static output, French and English.

Full spec in [`PLAN.md`](./PLAN.md).

## Run it

```sh
npm install
npm run dev      # http://localhost:4321 → redirects to /fr/
npm run build
```

## What's here

The content structure and the story page. **The map is not built yet** — the
homepage has a placeholder where it will mount.

Five islands are seeded to exercise every rendering state:

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

Body text is Spectral, loaded from Google Fonts. Display is **Faune**
(Alice Savoie / CNAP, free) — it is *not* on Google Fonts. Download the woff2
files and drop them in `public/fonts/`:

```
public/fonts/Faune-Text-Regular.woff2
public/fonts/Faune-Text-Italic.woff2
```

Until then it falls back to Spectral and everything still works.

## Publish to GitHub

```sh
cd atlas-des-iles-fantomes
git init -b main
git add .
git commit -m "Content structure and story page"

gh repo create atlas-des-iles-fantomes --private --source=. --push
# or, without the gh CLI: create the repo on github.com, then
# git remote add origin git@github.com:USER/atlas-des-iles-fantomes.git
# git push -u origin main
```

Then point Cloudflare Pages at the repo: build command `npm run build`, output
directory `dist`.

## The map

`src/components/PhantomMap.astro` + `src/components/map.ts`. Van der Grinten
projection, D3, ~35 kB gzipped. Hover (or first tap on touch) reveals the
island's name and lifespan; click navigates. Wheel/pinch zooms to 8x.

### Wrapping

Dragging left or right goes on forever: there is no edge, and the Pacific can
sit whole in the middle of the frame instead of being split down both sides.

Van der Grinten is a *round* projection — the world lands in a circle — so it
can't be tiled sideways the way a cylindrical one can. Copies placed edge to
edge would show circular seams. Horizontal panning therefore changes the
**central meridian** (`projection.rotate`) rather than translating the map.
`HOME_LON` sets the meridian the map opens on and returns to — change it to
`-160` to open on the Pacific.

d3-zoom supplies the scale and the raw gesture deltas; **position is entirely
ours**. Its own `x`/`y` never reach the transform and `translateExtent` is
unbounded, because x is the rotation channel and any vertical correction would
otherwise be overwritten by the next event's `t.y`. The transform is
`translate(offX, offY) scale(k)`, with the scale anchored at the frame centre
— without that anchor it grows away from x = 0 and the map walks off to the
right. `clampPan()` holds the vertical so the map always covers the frame.

### Zoom anchoring

Zoom holds the point under the cursor, and the correction is made in
**degrees, not pixels**. Two traps, both of which look like "zoom is slightly
drifty" until measured:

- Van der Grinten isn't cylindrical, so nudging longitude also moves a point
  *vertically*, and the vertical fix moves it back horizontally. One pass
  cannot converge; the loop iterates until the error is under a quarter pixel.
- Pixels-per-degree is not a constant, so a pixel-scaled nudge overshoots and
  the loop oscillates. Asking `invert()` what is actually under the cursor and
  shifting the meridian by the difference in longitude converges in two or
  three passes.

Measured drift over six successive zoom steps is 2–9 px, roughly a pixel per
step, holding at 83°N and in the mid-Pacific alike.

Because rotation changes the geometry, every path is regenerated per frame
(coalesced to one reprojection per rAF; measured 60 fps while dragging).
Island anchors and label sizes come from `geoCentroid`/`geoBounds` rather than
`path.centroid`/`getBBox`, which both misbehave for a shape the antimeridian
has cut into two pieces at opposite edges of the frame.

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
