#!/usr/bin/env node
/**
 * Draw an island where it actually is, with any overlap on real land marked.
 *
 *   node scripts/preview_island.mjs groclant
 *   node scripts/preview_island.mjs groclant --turn -32.5 --scale 0.91 --centre=-67.75,73.95
 *   node scripts/preview_island.mjs hy-brasil --out /tmp/hb.png --scale-px 3000
 *
 * ALWAYS DOTS THE LAND OVERLAP, which is the reason this exists. An island is
 * a thin burgundy outline and the basemap a dark fill, so where the outline
 * runs onto a coast it disappears into the fill and the shape still reads as
 * sitting in open water. Groclant was rendered, looked at and approved three
 * times while lying across Ellesmere, by both of us, from pictures I drew
 * without this.
 *
 * With --turn/--scale/--centre it previews a placement *before* writing it,
 * using the same geometry trace_outline would produce. Needs a python3 with
 * Pillow: set PYTHON=/path/to/python3 if the default lacks it.
 */
import fs from 'fs';
import os from 'os';
import path from 'path';
import { spawnSync } from 'child_process';
import { fileURLToPath } from 'url';
import * as d3 from 'd3-geo';
import * as topojson from 'topojson-client';

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const R = 6371, D = Math.PI / 180;
const argv = process.argv.slice(2);
const id = argv.find(a => !a.startsWith('--'));
const opt = (n, d) => { const i = argv.indexOf('--' + n); return i < 0 ? d : argv[i + 1]; };
if (!id) { console.error('usage: node scripts/preview_island.mjs <id> [--turn t] [--scale s] [--centre lon,lat] [--out f.png] [--scale-px n]'); process.exit(1); }

const topo = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/land-50m.json'), 'utf8'));
const land = topojson.feature(topo, topo.objects.land);
const all = JSON.parse(fs.readFileSync(path.join(ROOT, 'public/data/islands.geojson'), 'utf8'));
const F = JSON.parse(fs.readFileSync(path.join(ROOT, `src/data/outlines/${id}.geojson`), 'utf8'));
const P = F.properties, C = P.centre, BT = P.turned_deg || 0, BS = P.scaled_by || 1;

const fwd = (a, b, lo, la) => { const p0 = b * D, p1 = la * D, dl = (lo - a) * D;
  let c = Math.sin(p0) * Math.sin(p1) + Math.cos(p0) * Math.cos(p1) * Math.cos(dl);
  c = Math.acos(Math.max(-1, Math.min(1, c))); const k = Math.abs(c) < 1e-12 ? 1 : c / Math.sin(c);
  return [k * Math.cos(p1) * Math.sin(dl) * R, k * (Math.cos(p0) * Math.sin(p1) - Math.sin(p0) * Math.cos(p1) * Math.cos(dl)) * R]; };
const ivp = (a, b, x, y) => { const p0 = b * D; x /= R; y /= R; const rho = Math.hypot(x, y);
  if (rho < 1e-12) return [a, b]; const c = rho;
  const la = Math.asin(Math.cos(c) * Math.sin(p0) + y * Math.sin(c) * Math.cos(p0) / rho);
  const lo = a * D + Math.atan2(x * Math.sin(c), rho * Math.cos(c) * Math.cos(p0) - y * Math.sin(c) * Math.sin(p0));
  return [lo / D, la / D]; };

const T = opt('turn') !== undefined ? +opt('turn', BT) : BT;
const SC = +opt('scale', BS);
const CEN = opt('centre') ? opt('centre').split(',').map(Number) : C;
let shown = F, label = `${id} — as written · turn ${BT} · scale ${BS}`;
if (T !== BT || SC !== BS || CEN[0] !== C[0] || CEN[1] !== C[1]) {
  const t = (T - BT) * D, cs = Math.cos(t), sn = Math.sin(t), f = SC / BS;
  const move = g => g.map(([lo, la]) => { const [x, y] = fwd(C[0], C[1], lo, la);
    return ivp(CEN[0], CEN[1], (x * cs - y * sn) * f, (x * sn + y * cs) * f); });
  shown = { type: 'Feature', properties: {}, geometry: F.geometry.type === 'MultiPolygon'
    ? { type: 'MultiPolygon', coordinates: F.geometry.coordinates.map(p => p.map(move)) }
    : { type: 'Polygon', coordinates: F.geometry.coordinates.map(move) } };
  label = `${id} — PREVIEW · turn ${T} · scale ${SC} · centre [${CEN}]`;
}

const bb = d3.geoBounds(shown);
const hits = [];
const sx = Math.max((bb[1][0] - bb[0][0]) / 70, 0.02), sy = Math.max((bb[1][1] - bb[0][1]) / 70, 0.02);
for (let x = bb[0][0]; x <= bb[1][0]; x += sx)
  for (let y = bb[0][1]; y <= bb[1][1]; y += sy)
    if (d3.geoContains(shown, [x, y]) && d3.geoContains(land, [x, y])) hits.push([x, y]);
const area = Math.round(d3.geoArea(shown) * R * R);
console.log(`${id}: ${area} km2 | bounds ${JSON.stringify(bb.map(p => p.map(v => +v.toFixed(2))))}`);
console.log(hits.length ? `  ON LAND at ${hits.length} sampled points — marked in orange`
                        : '  clear of land');
if (d3.geoArea(shown) > Math.PI * 2) console.log('  WINDING INVERTED — this will render as the whole planet');

const W = 900, H = 750;
const c0 = d3.geoCentroid(shown);
const ring = (proj, f) => { const o = []; let cur = [];
  const s = proj.stream({ point(x, y) { cur.push([x, y]); }, lineStart() { cur = []; },
    lineEnd() { if (cur.length > 1) o.push(cur); }, polygonStart() {}, polygonEnd() {}, sphere() {} });
  d3.geoStream(f, s); return o; };
const others = all.features.filter(f => f.properties.id !== id);
const views = [];
for (const [tag, k] of [['in context', 900], ['close', +opt('scale-px', 2600)]]) {
  const proj = d3.geoOrthographic().rotate([-c0[0], -c0[1]]).translate([W / 2, H / 2]).scale(k).clipAngle(90);
  views.push({ label: `${label}   —   ${tag}`, sphere: ring(proj, { type: 'Sphere' }),
    land: ring(proj, land), island: ring(proj, shown),
    others: others.flatMap(f => ring(proj, f)), hits: hits.map(p => proj(p)) });
}
const out = opt('out', path.join(os.tmpdir(), `preview-${id}.png`));
const scene = path.join(os.tmpdir(), `scene-${id}.json`);
fs.writeFileSync(scene, JSON.stringify({ W, H, out, views }));
const py = process.env.PYTHON || 'python3';
const r = spawnSync(py, [path.join(ROOT, 'scripts/_preview_draw.py'), scene], { stdio: 'inherit' });
if (r.status !== 0) console.error(`\ndrawing failed — needs a python3 with Pillow; try PYTHON=/path/to/python3`);
