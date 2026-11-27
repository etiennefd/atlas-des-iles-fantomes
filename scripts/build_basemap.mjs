// Writes public/data/land-50m.json: world-atlas's land-50m, corrected in two
// ways, both listed below with the reason for each.
//
//   node scripts/build_basemap.mjs
//
// The basemap stays Natural Earth 50m (see Traps in CLAUDE.md); this only
// takes out what it wrongly has and puts in what a phantom needs beside it.
// Dropped and added here rather than masked or drawn on the globe, so that
// every script reading the basemap (check_overlap, place_island,
// lift_country) sees the same land as the map.
//
// PHANTOMS: islands Natural Earth still carries as land. Its coastlines
// descend in part from the same World Vector Shoreline that kept Sandy
// Island alive, and world-atlas 2.0.2's land-50m still has it: a 6-point
// polygon of 71 km2 at 159.93-159.98 E, 19.12-19.33 S. Left in, the atlas
// would draw its own phantom as real land. A polygon is dropped only if it
// lies wholly inside its box, and the script refuses unless each box drops
// exactly one polygon of roughly the expected area.
//
// ADDITIONS: real islands land-50m lacks that a phantom is placed by. Bouvet
// is not in land-50m at all, and Thompson Island is set by its offset from
// Bouvet on Norris's chart, so without it Thompson sat alone in open sea.
// Taken from world-atlas's land-10m (54.5 km2), re-quantized onto land-50m's
// grid (about 230 x 190 m there) — one 10m polygon in a 50m basemap, by
// Étienne's choice, November 2026. Each box must hold exactly one 10m
// polygon of roughly the expected area.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as topojson from 'topojson-client';
import { geoBounds, geoArea } from 'd3-geo';

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const SRC = path.join(ROOT, 'node_modules/world-atlas/land-50m.json');
const SRC10 = path.join(ROOT, 'node_modules/world-atlas/land-10m.json');
const DEST = path.join(ROOT, 'public/data/land-50m.json');

const PHANTOMS = [
  { id: 'ile-de-sable', box: [159.8, -19.5, 160.1, -19.0], km2: 71 },
];
const ADDITIONS = [
  { id: 'bouvet', box: [3.2, -54.6, 3.6, -54.3], km2: 54.5 },
];

const R = 6371;
const inBox = ([[x0, y0], [x1, y1]], [bx0, by0, bx1, by1]) =>
  x0 >= bx0 && x1 <= bx1 && y0 >= by0 && y1 <= by1;
const near = (km2, want) => Math.abs(km2 - want) <= 0.2 * want;

const topo = JSON.parse(fs.readFileSync(SRC, 'utf8'));
const geoms = topo.objects.land.geometries;
if (geoms.length !== 1 || geoms[0].type !== 'MultiPolygon') {
  throw new Error('expected land as a single MultiPolygon');
}
const mp = geoms[0];

const drop = new Set();
for (const ph of PHANTOMS) {
  const hits = [];
  mp.arcs.forEach((polyArcs, i) => {
    const f = topojson.feature(topo, { type: 'Polygon', arcs: polyArcs });
    if (inBox(geoBounds(f), ph.box)) hits.push({ i, km2: geoArea(f) * R * R });
  });
  if (hits.length !== 1) throw new Error(`${ph.id}: ${hits.length} polygons in the box`);
  const { i, km2 } = hits[0];
  if (!near(km2, ph.km2)) throw new Error(`${ph.id}: ${km2.toFixed(1)} km2, expected ~${ph.km2}`);
  drop.add(i);
  console.log(`dropped ${ph.id}: land polygon ${i}, ${km2.toFixed(1)} km2`);
}
mp.arcs = mp.arcs.filter((_, i) => !drop.has(i));

// land-10m as distributed carries three degenerate whole-sphere polygons (see
// Traps); the box test skips them, since their bounds are the whole globe.
const t10 = JSON.parse(fs.readFileSync(SRC10, 'utf8'));
const land10 = topojson.feature(t10, t10.objects.land);
const polys10 = land10.features.flatMap(f =>
  f.geometry.type === 'MultiPolygon' ? f.geometry.coordinates : [f.geometry.coordinates]);
const { scale: [sx, sy], translate: [tx, ty] } = topo.transform;
for (const add of ADDITIONS) {
  const hits = polys10.filter(p => inBox(geoBounds({ type: 'Polygon', coordinates: p }), add.box));
  if (hits.length !== 1) throw new Error(`${add.id}: ${hits.length} land-10m polygons in the box`);
  const poly = hits[0];
  const km2 = geoArea({ type: 'Polygon', coordinates: poly }) * R * R;
  if (!near(km2, add.km2)) throw new Error(`${add.id}: ${km2.toFixed(1)} km2, expected ~${add.km2}`);
  const arcIdx = [];
  for (const ring of poly) {
    // quantize onto land-50m's grid, drop repeats, delta-encode
    const q = [];
    for (const [x, y] of ring) {
      const p = [Math.round((x - tx) / sx), Math.round((y - ty) / sy)];
      if (!q.length || p[0] !== q.at(-1)[0] || p[1] !== q.at(-1)[1]) q.push(p);
    }
    if (q[0][0] !== q.at(-1)[0] || q[0][1] !== q.at(-1)[1]) q.push(q[0]);
    const arc = q.map((p, i) => i ? [p[0] - q[i - 1][0], p[1] - q[i - 1][1]] : p);
    arcIdx.push([topo.arcs.length]);
    topo.arcs.push(arc);
  }
  mp.arcs.push(arcIdx);   // one ring per arc: [[outer], [hole], ...]
  const added = topojson.feature(topo, { type: 'Polygon', arcs: mp.arcs.at(-1) });
  const back = geoArea(added) * R * R;
  if (!near(back, add.km2)) throw new Error(`${add.id}: ${back.toFixed(1)} km2 after quantizing`);
  console.log(`added ${add.id}: ${poly[0].length} points from land-10m, ${back.toFixed(1)} km2 on the 50m grid`);
}

fs.writeFileSync(DEST, JSON.stringify(topo));
console.log(`${path.relative(ROOT, DEST)}: ${mp.arcs.length} land polygons`);
