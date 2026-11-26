// Writes public/data/land-50m.json: world-atlas's land-50m with the phantom
// islands Natural Earth still carries as land taken out.
//
//   node scripts/drop_basemap_phantoms.mjs
//
// Natural Earth's coastlines descend in part from the same World Vector
// Shoreline that kept Sandy Island alive, and world-atlas 2.0.2's land-50m
// still has it: a 6-point polygon of 71 km2 at 159.93-159.98 E,
// 19.12-19.33 S. Left in, the atlas would draw its own phantom as real land,
// dark grey under the outline. Dropping it from the file, rather than masking
// it on the globe as the misdrawn islands and lakes are, means every script
// that reads the basemap (check_overlap, place_island, lift_country) agrees.
//
// Each entry is a box; a land polygon is dropped only if it lies wholly
// inside its box, and the script refuses to write unless each box drops
// exactly one polygon of roughly the expected area.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as topojson from 'topojson-client';
import { geoBounds, geoArea } from 'd3-geo';

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const SRC = path.join(ROOT, 'node_modules/world-atlas/land-50m.json');
const DEST = path.join(ROOT, 'public/data/land-50m.json');

const PHANTOMS = [
  { id: 'ile-de-sable', box: [159.8, -19.5, 160.1, -19.0], km2: 71 },
];

const R = 6371;
const topo = JSON.parse(fs.readFileSync(SRC, 'utf8'));
const geoms = topo.objects.land.geometries;
if (geoms.length !== 1 || geoms[0].type !== 'MultiPolygon') {
  throw new Error('expected land as a single MultiPolygon');
}
const mp = geoms[0];

const drop = new Set();
for (const ph of PHANTOMS) {
  const [x0, y0, x1, y1] = ph.box;
  const hits = [];
  mp.arcs.forEach((polyArcs, i) => {
    const f = topojson.feature(topo, { type: 'Polygon', arcs: polyArcs });
    const [[bx0, by0], [bx1, by1]] = geoBounds(f);
    if (bx0 >= x0 && bx1 <= x1 && by0 >= y0 && by1 <= y1) {
      hits.push({ i, km2: geoArea(f) * R * R });
    }
  });
  if (hits.length !== 1) throw new Error(`${ph.id}: ${hits.length} polygons in the box`);
  const { i, km2 } = hits[0];
  if (Math.abs(km2 - ph.km2) > 0.2 * ph.km2) {
    throw new Error(`${ph.id}: polygon is ${km2.toFixed(1)} km2, expected ~${ph.km2}`);
  }
  drop.add(i);
  console.log(`${ph.id}: dropped land polygon ${i}, ${km2.toFixed(1)} km2`);
}

mp.arcs = mp.arcs.filter((_, i) => !drop.has(i));
fs.writeFileSync(DEST, JSON.stringify(topo));
console.log(`${path.relative(ROOT, DEST)}: ${mp.arcs.length} land polygons`);
