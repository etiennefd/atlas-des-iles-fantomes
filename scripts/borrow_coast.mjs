#!/usr/bin/env node
/**
 * Lift a stretch of real coastline out of the basemap, to stand in where no
 * chart will.
 *
 *   node scripts/borrow_coast.mjs oregon -- -124.2,40.6  -124.7,48.3
 *
 * California's strait has to reach the real Oregon coast, and the charts do
 * not go there: Vinckeboons and the 1650 French sheet both stop around
 * 41.4 N, Senex runs his off the edge of the plate. That leaves roughly 900 km
 * of shore with no source at all, and a smooth arc across it looks exactly
 * like what it is.
 *
 * So the shape is borrowed rather than invented. A real coastline of the same
 * length and the same part of the world carries the right roughness at every
 * scale, which no amount of hand-drawn wobble does. It is a fabrication either
 * way; this one is at least a fabrication made of coastline, and the
 * provenance is written down in the island's `outline_note`.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import * as d3 from 'd3-geo';
import * as topojson from 'topojson-client';

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2).filter((a) => a !== '--');
const [name, aStr, bStr] = args;
if (!name || !aStr || !bStr) {
  console.error('usage: node scripts/borrow_coast.mjs <name> -- lon,lat lon,lat');
  process.exit(1);
}
const A = aStr.split(',').map(Number), B = bStr.split(',').map(Number);

const topo = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/land-50m.json'), 'utf8'));
const land = topojson.feature(topo, topo.objects.land);
const polys = land.features
  ? land.features.flatMap((f) => (f.geometry.type === 'MultiPolygon'
      ? f.geometry.coordinates : [f.geometry.coordinates]))
  : land.geometry.coordinates;

// the ring that passes closest to both anchors
let ring = null, score = Infinity;
for (const poly of polys) {
  const r = poly[0];
  let da = Infinity, db = Infinity;
  for (const p of r) {
    da = Math.min(da, d3.geoDistance(p, A));
    db = Math.min(db, d3.geoDistance(p, B));
  }
  if (da + db < score) { score = da + db; ring = r; }
}
const near = (P) => ring.reduce((best, p, i) =>
  d3.geoDistance(p, P) < d3.geoDistance(ring[best], P) ? i : best, 0);
const i = near(A), j = near(B);
const fwd = i <= j ? ring.slice(i, j + 1) : ring.slice(i).concat(ring.slice(0, j + 1));
const rev = i >= j ? ring.slice(j, i + 1).reverse()
                   : ring.slice(j).concat(ring.slice(0, i + 1)).reverse();
const seg = fwd.length <= rev.length ? fwd : rev;

let km = 0;
for (let n = 1; n < seg.length; n++) km += d3.geoDistance(seg[n - 1], seg[n]) * 6371;
const out = path.join(ROOT, 'src/data/borrowed', `${name}.json`);
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, JSON.stringify({
  name,
  note: 'A real coastline, lifted from Natural Earth 50m to stand in where no chart reaches. Grafted elsewhere by build_misdrawn.py; see the island\'s outline_note.',
  from: A, to: B, length_km: Math.round(km), points: seg.length,
  coordinates: seg.map((p) => [+p[0].toFixed(4), +p[1].toFixed(4)]),
}, null, 1));
console.log(`${name}: ${seg.length} vertices, ${Math.round(km)} km  -> ${path.relative(ROOT, out)}`);
