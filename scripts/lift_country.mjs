#!/usr/bin/env node
/**
 * Lift whole countries out of Natural Earth, as the region a misdrawn island
 * erases.
 *
 *   node scripts/lift_country.mjs korea -- 408 410
 *
 * California's chart has a mainland coast of its own to cut against, so its
 * erase region is built from the chart. Korea's does not: Teixeira runs the
 * island off the top of the frame and says nothing about what lies north. But
 * the claim is plain enough — the real peninsula is not there, the thin
 * island is — and the real peninsula is exactly North plus South Korea. Erase
 * those, and the new mainland shore is the Yalu–Tumen border: a real line,
 * and the one place where a strait would have had to run.
 *
 * Ids are ISO 3166 numeric, as world-atlas carries them. Writes
 * src/data/borrowed/<name>.json; build_misdrawn.py reads it.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import * as d3 from 'd3-geo';
import * as topojson from 'topojson-client';

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2).filter((a) => a !== '--');
const [name, ...ids] = args;
if (!name || !ids.length) {
  console.error('usage: node scripts/lift_country.mjs <name> -- <iso numeric id> ...');
  process.exit(1);
}

// countries-50m, to match the land-50m basemap it is cut out of
const topo = JSON.parse(fs.readFileSync(
  path.join(ROOT, 'node_modules/world-atlas/countries-50m.json'), 'utf8'));
const feats = topojson.feature(topo, topo.objects.countries).features
  .filter((f) => ids.includes(String(f.id)));
if (feats.length !== ids.length) {
  console.error(`found ${feats.length} of ${ids.length} ids`);
  process.exit(1);
}
const flat = (g) => (g.type === 'MultiPolygon' ? g.coordinates : [g.coordinates]);
const polys = feats.flatMap((f) => flat(f.geometry));

// The land and country layers do not agree on every islet. Baengnyeong-do is
// in land-50m but in no country of countries-50m, so erasing South Korea left
// it standing alone in the new Yellow Sea. Take any land polygon no country
// covers whose nearest country is one of ours.
const all = topojson.feature(topo, topo.objects.countries).features;
const landTopo = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/land-50m.json'), 'utf8'));
const land = topojson.feature(landTopo, landTopo.objects.land);
const landPolys = land.features ? land.features.flatMap((f) => flat(f.geometry)) : flat(land.geometry);
const [[w, s], [e, n]] = d3.geoBounds({ type: 'MultiPolygon', coordinates: polys });
const orphans = [];
for (const p of landPolys) {
  const c = d3.geoCentroid({ type: 'Polygon', coordinates: p });
  if (c[0] < w - 2 || c[0] > e + 2 || c[1] < s - 2 || c[1] > n + 2) continue;
  if (all.some((f) => d3.geoContains(f, c))) continue;
  let best = null, bd = Infinity;
  for (const f of all) {
    const [[fw, fs_], [fe, fn]] = d3.geoBounds(f);
    if (c[0] < fw - 3 || c[0] > fe + 3 || c[1] < fs_ - 3 || c[1] > fn + 3) continue;
    for (const poly of flat(f.geometry)) for (const q of poly[0]) {
      const dd = d3.geoDistance(q, c);
      if (dd < bd) { bd = dd; best = f; }
    }
  }
  if (best && ids.includes(String(best.id))) {
    orphans.push(p);
    console.log(`  + orphan islet at ${c.map((v) => v.toFixed(2))}, nearest ${best.properties.name}, `
      + `${Math.round(bd * 6371)} km`);
  }
}
polys.push(...orphans);
const round = (r) => r.map((p) => [+p[0].toFixed(4), +p[1].toFixed(4)]);

const out = path.join(ROOT, 'src/data/borrowed', `${name}.json`);
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, JSON.stringify({
  name,
  note: 'Whole countries from Natural Earth 50m (world-atlas countries-50m), lifted as the region a misdrawn island erases from the basemap. See build_misdrawn.py and the island\'s outline_note.',
  countries: feats.map((f) => `${f.id} ${f.properties.name}`),
  orphan_islets: orphans.length,
  type: 'MultiPolygon',
  coordinates: polys.map((p) => p.map(round)),
}));
console.log(`${name}: ${feats.map((f) => f.properties.name).join(' + ')}, `
  + `${polys.length} polygons  -> ${path.relative(ROOT, out)}`);
