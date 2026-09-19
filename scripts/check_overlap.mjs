#!/usr/bin/env node
/**
 * Does an island sit on real land?
 *
 * The map cannot answer this. An island is a thin burgundy outline and the
 * basemap is a dark fill, so where the outline crosses a coast it vanishes
 * into that fill and the shape still reads as enclosing water. Groclant was
 * placed, looked at, and approved three times while overlapping Ellesmere.
 *
 *   node scripts/check_overlap.mjs groclant      # one island
 *   node scripts/check_overlap.mjs               # all of them
 *
 * Samples the outline every 5% of each edge plus an interior grid, and tests
 * each point against Natural Earth 50m. Prints one line per island; anything
 * above 0 is touching. Takes a few seconds per island.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import * as d3 from 'd3-geo';
import * as topojson from 'topojson-client';

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const topo = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/land-50m.json'), 'utf8'));
const land = topojson.feature(topo, topo.objects.land);
const fc = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/islands.geojson'), 'utf8'));

const want = process.argv.slice(2);
const targets = want.length
  ? fc.features.filter(f => want.includes(f.properties.id))
  : fc.features;
if (want.length && targets.length !== want.length) {
  const got = targets.map(f => f.properties.id);
  console.error('unknown island(s):', want.filter(w => !got.includes(w)).join(', '));
  process.exit(1);
}

let anyHit = false;
for (const f of targets) {
  if (f.geometry.type === 'Point') continue;          // reefs are dots
  const polys = f.geometry.type === 'MultiPolygon'
    ? f.geometry.coordinates : [f.geometry.coordinates];
  const pts = [];
  for (const poly of polys) for (const ring of poly) {
    for (let i = 0; i < ring.length - 1; i++) {
      const [a, b] = [ring[i], ring[i + 1]];
      for (let t = 0; t < 1; t += 0.05)
        pts.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
    }
  }
  const bb = d3.geoBounds(f);
  const stepX = Math.max((bb[1][0] - bb[0][0]) / 40, 0.02);
  const stepY = Math.max((bb[1][1] - bb[0][1]) / 40, 0.02);
  for (let x = bb[0][0]; x <= bb[1][0]; x += stepX)
    for (let y = bb[0][1]; y <= bb[1][1]; y += stepY)
      if (d3.geoContains(f, [x, y])) pts.push([x, y]);
  const bad = pts.filter(p => d3.geoContains(land, p));
  const pct = (100 * bad.length / pts.length).toFixed(1);
  if (bad.length) anyHit = true;
  const flag = bad.length ? 'ON LAND' : 'clear  ';
  console.log(`${flag}  ${f.properties.id.padEnd(18)} ${String(bad.length).padStart(5)} / ${String(pts.length).padEnd(6)} (${pct}%)`);
}
process.exit(anyHit && want.length ? 1 : 0);
