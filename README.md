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
projection, D3, ~33 kB gzipped. Hover (or first tap on touch) reveals the
island's name and lifespan; click navigates. Wheel/pinch zooms to 8x.

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
