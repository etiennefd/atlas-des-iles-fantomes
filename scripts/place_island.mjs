#!/usr/bin/env node
/**
 * Where can this island sit without lying on real land?
 *
 * Some islands cannot go where their chart puts them — Ortelius draws
 * Groclant on top of Ellesmere. Moving one is a liberty, and the liberty has
 * three knobs: centre, `--turn`, `--scale`. This searches them together and
 * prints the trace_outline flags for each placement that clears.
 *
 *   node scripts/place_island.mjs groclant --lon -76,-52 --lat 68,80
 *   node scripts/place_island.mjs groclant --turn -40,-20,5 --scale 0.85,1.0,0.03
 *
 * ROTATION ORIGIN IS THE TRAP. trace_outline rotates about the mask's
 * bounding-box centre in the chart frame, not about the island's centroid or
 * its current position. Searching with a different origin gives placements
 * that are 20-40 km off once written, which is enough to ground a 600 km
 * island. This works from the island's own stored `turned_deg`/`scaled_by`,
 * so the geometry it tests is what trace_outline will actually write.
 *
 * Sampling matters too: edges every 6 km plus an interior grid. An earlier
 * version tested only the ~100 outline vertices, 25 km apart on a big island,
 * and peninsulas slipped between them — it declared 700 clear placements that
 * were not.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import * as d3 from 'd3-geo';
import * as topojson from 'topojson-client';

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const R = 6371, D = Math.PI / 180;

const argv = process.argv.slice(2);
const id = argv.find(a => !a.startsWith('--'));
const opt = (n, d) => { const i = argv.indexOf('--' + n); return i < 0 ? d : argv[i + 1]; };
if (!id) { console.error('usage: node scripts/place_island.mjs <id> [--lon a,b] [--lat a,b] [--turn a,b,step] [--scale a,b,step] [--top n]'); process.exit(1); }

const F = JSON.parse(fs.readFileSync(path.join(ROOT, `src/data/outlines/${id}.geojson`), 'utf8'));
const P = F.properties;
const C = P.centre, BT = P.turned_deg || 0, BS = P.scaled_by || 1;
const chartAt = P.centre_from_chart || C;

const rng = (s, dflt) => { if (!s) return dflt; const p = s.split(',').map(Number); return p.length === 3 ? p : [p[0], p[1], p[1] - p[0] || 1]; };
const [lon0, lon1] = (opt('lon') || `${C[0] - 6},${C[0] + 6}`).split(',').map(Number);
const [lat0, lat1] = (opt('lat') || `${C[1] - 4},${C[1] + 4}`).split(',').map(Number);
const [t0, t1, ts] = rng(opt('turn'), [BT, BT, 1]);
const [s0, s1, ss] = rng(opt('scale'), [BS, BS, 1]);
const TOP = +opt('top', 12);

// --- land raster, cached: building it is the slow part
const cacheDir = path.join(ROOT, '.cache');
fs.mkdirSync(cacheDir, { recursive: true });
const S = 0.07;
const key = `land_${lon0 - 8}_${lon1 + 8}_${lat0 - 5}_${lat1 + 5}_${S}.json`.replace(/[^\w.-]/g, '_');
const cache = path.join(cacheDir, key);
let G;
if (fs.existsSync(cache)) G = JSON.parse(fs.readFileSync(cache, 'utf8'));
else {
  process.stderr.write('building land raster (cached after this)... ');
  const topo = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/land-50m.json'), 'utf8'));
  const land = topojson.feature(topo, topo.objects.land);
  const LON0 = lon0 - 8, LAT0 = lat0 - 5;
  const NX = Math.round(((lon1 + 8) - LON0) / S), NY = Math.round(((lat1 + 5) - LAT0) / S);
  const r = new Uint8Array(NX * NY);
  for (let j = 0; j < NY; j++) { const la = LAT0 + j * S + S / 2;
    for (let i = 0; i < NX; i++) if (d3.geoContains(land, [LON0 + i * S + S / 2, la])) r[j * NX + i] = 1; }
  G = { LON0, LAT0, S, NX, NY, r: Array.from(r) };
  fs.writeFileSync(cache, JSON.stringify(G));
  process.stderr.write('done\n');
}
const r = Uint8Array.from(G.r);
const hit = (lo, la) => { const i = Math.floor((lo - G.LON0) / G.S), j = Math.floor((la - G.LAT0) / G.S);
  return (i < 0 || i >= G.NX || j < 0 || j >= G.NY) ? 1 : r[j * G.NX + i]; };

const fwd = (a, b, lo, la) => { const p0 = b * D, p1 = la * D, dl = (lo - a) * D;
  let c = Math.sin(p0) * Math.sin(p1) + Math.cos(p0) * Math.cos(p1) * Math.cos(dl);
  c = Math.acos(Math.max(-1, Math.min(1, c))); const k = Math.abs(c) < 1e-12 ? 1 : c / Math.sin(c);
  return [k * Math.cos(p1) * Math.sin(dl) * R, k * (Math.cos(p0) * Math.sin(p1) - Math.sin(p0) * Math.cos(p1) * Math.cos(dl)) * R]; };
const ivp = (a, b, x, y) => { const p0 = b * D; x /= R; y /= R; const rho = Math.hypot(x, y);
  if (rho < 1e-12) return [a, b]; const c = rho;
  const la = Math.asin(Math.cos(c) * Math.sin(p0) + y * Math.sin(c) * Math.cos(p0) / rho);
  const lo = a * D + Math.atan2(x * Math.sin(c), rho * Math.cos(c) * Math.cos(p0) - y * Math.sin(c) * Math.sin(p0));
  return [lo / D, la / D]; };

const rings = F.geometry.type === 'MultiPolygon'
  ? F.geometry.coordinates.map(p => p[0]) : [F.geometry.coordinates[0]];
const km = rings.map(g => g.slice(0, -1).map(p => fwd(C[0], C[1], p[0], p[1])));
const pts = [];
for (const g of km) {
  for (let i = 0; i < g.length; i++) { const a = g[i], b = g[(i + 1) % g.length];
    const d = Math.hypot(b[0] - a[0], b[1] - a[1]), n = Math.max(1, Math.ceil(d / 6));
    for (let t = 0; t < n; t++) pts.push([a[0] + (b[0] - a[0]) * t / n, a[1] + (b[1] - a[1]) * t / n]); }
}
const main = km.reduce((a, b) => a.length > b.length ? a : b);
const ins = (x, y) => { let c = false;
  for (let i = 0, j = main.length - 1; i < main.length; j = i++)
    if ((main[i][1] > y) !== (main[j][1] > y) &&
        x < (main[j][0] - main[i][0]) * (y - main[i][1]) / (main[j][1] - main[i][1]) + main[i][0]) c = !c;
  return c; };
const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
for (let x = Math.min(...xs); x <= Math.max(...xs); x += 14)
  for (let y = Math.min(...ys); y <= Math.max(...ys); y += 14) if (ins(x, y)) pts.push([x, y]);

const clear = (lon, lat, T, sc) => { const t = (T - BT) * D, cs = Math.cos(t), sn = Math.sin(t), f = sc / BS;
  for (const [x, y] of pts) { const q = ivp(lon, lat, (x * cs - y * sn) * f, (x * sn + y * cs) * f);
    if (hit(q[0], q[1])) return false; } return true; };

const out = [];
for (let T = t0; T <= t1 + 1e-9; T += ts)
  for (let sc = s1; sc >= s0 - 1e-9; sc -= ss)
    for (let lon = lon0; lon <= lon1 + 1e-9; lon += 0.25)
      for (let lat = lat0; lat <= lat1 + 1e-9; lat += 0.25)
        if (clear(lon, lat, T, sc))
          out.push({ T: +T.toFixed(2), sc: +sc.toFixed(3), lon: +lon.toFixed(2), lat: +lat.toFixed(2),
                     moved: Math.round(d3.geoDistance([lon, lat], chartAt) * R) });

console.log(`${id}: ${pts.length} sample points, ${out.length} clear placements`);
if (!out.length) { console.log('none — widen --lon/--lat, turn further, or scale down'); process.exit(0); }
// prefer: least scaled down, then least turned from the chart, then least moved
out.sort((a, b) => (b.sc - a.sc) || (Math.abs(a.T) - Math.abs(b.T)) || (a.moved - b.moved));
console.log(`\nchart put it at ${chartAt.map(v => v.toFixed(2))}; current file is turn ${BT}, scale ${BS}\n`);
console.log(`  ${'turn'.padStart(7)}${'scale'.padStart(8)}${'centre'.padStart(20)}${'moved'.padStart(8)}   flags`);
for (const o of out.slice(0, TOP))
  console.log(`  ${String(o.T).padStart(7)}${String(o.sc).padStart(8)}${`[${o.lon}, ${o.lat}]`.padStart(20)}${String(o.moved + ' km').padStart(8)}   --turn ${o.T} --scale ${o.sc} --centre=${o.lon},${o.lat}`);
