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

## Next

1. Coordinates for the remaining islands (see PLAN.md §11).
2. The map: Van der Grinten, D3, Voronoi hit-testing, halos, zoom.
3. Migrate the 28 stories.
