#!/usr/bin/env python3
"""
Trace an OPEN coast: land seen from a ship and never sailed round.

Some phantoms were never islands on the charts that carried them. Davis Land
is a stretch of shore with hatching on its sea side and nothing behind it:
the engraver drew what the ship saw and stopped. Closing it into a polygon
would invent the far side, so this writes a line instead, with land on its
RIGHT as you walk along it (the same sense as a d3 exterior ring, so the
shade build_geojson lays behind it winds correctly for free).

    python3 scripts/trace_coast.py terre-de-davis --chart vaugondy-1750 \
        --image ~/scratch/charts/davis/vaugondy-1750.jpg \
        --bbox 690,3060,960,3330 --land 700,3320

The coast is the land-side edge of the hatch band. The band is found as ink
density (grey < --threshold, averaged over --window px, above --density), its
outline is split at the two tips — the farthest-apart pair of points on it —
and the half facing the --land point is kept. The sea-side half is the outer
edge of the hatching, which is water.

Georeferenced by the sheet's own graticule, so position and scale both come
from the chart: a `graticule` block in the chart JSON (meridians as
x = poly(y), parallels as y = poly(x), fitted on the engraved lines), or a
`polar` block for a polar azimuthal sheet, in the same form trace_outline.py
reads (pole_px, k, lon0, law).

Two flags for charts that draw the coast otherwise than Vaugondy:

  --edge x,y   keep the half of the outline facing this point instead of the
               land. Peary shades Crocker Land as a crescent of high ground and
               dashes its near shore: the coast is the band's SEA-side edge.
  --parts N    keep the N largest pieces as separate stretches of coast.

And one for a shore drawn as a DASHED LINE across a graticule, where every
band threshold fails: the sheet's own lines cut the dashes into pieces, and
painting the lines out cuts them again. Peary's Crocker Land and Balch's
Bradley Land are both like this.

  --radial cx,cy,r0,r1,a0,a1[;...]
               scan rays from a centre on the shore's concave (land) side,
               every degree from a0 to a1 (0 = east on the page, 90 = down),
               between radii r0 and r1, and take the middle of the outermost
               run of ink on each — ignoring the graticule's own lines.
               Outliers (lettering, a hachure inside the dashes) are dropped
               against a running median. One spec per stretch of coast: Balch
               draws Bradley Land as two brackets, with Cook's "distinct
               break for 15 or 20 miles" between them. The land is taken to
               be on the centre's side unless --land says otherwise.

An islet from another chart can ride along (--islet-chart): it is traced as
the pale core inside its ring of hatching, and keeps the relationship to the coast its own
chart gives it — the same fraction along the shore and the same distance off
it in km. That is a composite, and it is recorded as one.
"""
import argparse, json, math, os

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_fill_holes, label as ndlabel, uniform_filter
from skimage.measure import approximate_polygon, find_contours, label, regionprops

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUTDIR = os.path.join(ROOT, "src", "data", "outlines")
CHARTS = os.path.join(HERE, "charts")
R_KM = 6371.0


def band(gray, thr, window, density, blank, rules=None, parts=1):
    """The hatch band, filled, as the largest piece of ink density — or the
    `parts` largest, as a list. `rules` is a boolean mask of graticule lines
    to paint out first: a meridian is ink as dense as the hatching and runs
    straight through the band."""
    g = gray.copy()
    for x0, y0, x1, y1 in blank:
        g[y0:y1, x0:x1] = 255
    if rules is not None:
        g[rules] = 255
    m = uniform_filter((g < thr).astype(float), window) > density
    lab = label(m)
    if lab.max() == 0:
        raise SystemExit("no ink band found — lower --threshold or --density")
    big = sorted(regionprops(lab), key=lambda r: -r.area)
    if parts == 1:
        return binary_fill_holes(lab == big[0].label)
    if len(big) < parts:
        raise SystemExit(f"--parts {parts}: only {len(big)} pieces of band found")
    return [binary_fill_holes(lab == r.label) for r in big[:parts]]


def radial_arc(gray, ox, oy, rules, spec, thr):
    """The shore along rays from a centre of curvature on its land side: the
    middle of the outermost ink run on each ray, in source px, ordered by
    angle. `gray` and `rules` cover the source from (ox, oy)."""
    from scipy.ndimage import map_coordinates, median_filter
    cx, cy, r0, r1, a0, a1 = spec
    r = np.arange(r0, r1, 0.5)
    got = []
    for th in np.arange(a0, a1 + 0.5, 1.0):
        t = math.radians(th)
        x, y = cx + r * math.cos(t) - ox, cy + r * math.sin(t) - oy
        ink = map_coordinates(gray, [y, x], order=1) < thr
        if rules is not None:
            ink &= map_coordinates(rules.astype(float), [y, x], order=0) == 0
        idx = np.nonzero(ink)[0]
        if not len(idx):
            continue
        end = idx[-1]
        start = end
        while start - 1 in set(idx) and end - start < 40:
            start -= 1
        got.append((th, r[(start + end) // 2]))
    if len(got) < 5:
        raise SystemExit(f"--radial {spec}: almost no ink found — check the centre and radii")
    got = np.array(got)
    med = median_filter(got[:, 1], 9, mode="nearest")
    got = got[np.abs(got[:, 1] - med) < 3]
    rr = median_filter(got[:, 1], 5, mode="nearest")
    return np.column_stack([cx + rr * np.cos(np.radians(got[:, 0])),
                            cy + rr * np.sin(np.radians(got[:, 0]))])


def orient(arc, land_xy):
    """Order the arc so the land is on its right (in a y-up frame)."""
    lx, ly = land_xy
    mid = arc[len(arc) // 2]
    dx, dy = arc[-1, 0] - arc[0, 0], -(arc[-1, 1] - arc[0, 1])
    vx, vy = lx - mid[0], -(ly - mid[1])
    return arc[::-1] if dx * vy - dy * vx > 0 else arc


def land_arc(mask, land_xy, origin, tolerance, edge_xy=None):
    """The half of the band's outline that faces the land (or `edge_xy`, when
    the drawn shore is the band's other edge), ordered so the land is on the
    right walking along it (image y down, so 'right' is computed in a y-up
    frame). Returns (points as [(x, y)] in source px, tips)."""
    ox, oy = origin
    c = max(find_contours(mask.astype(float), 0.5), key=len)       # (row, col)
    pts = np.column_stack([c[:, 1] + ox, c[:, 0] + oy])
    if (pts[0] == pts[-1]).all():
        pts = pts[:-1]
    # tips: the farthest pair. O(n^2) on a few thousand points is fine.
    sub = pts[:: max(1, len(pts) // 1500)]
    d = ((sub[:, None, :] - sub[None, :, :]) ** 2).sum(-1)
    i, j = np.unravel_index(np.argmax(d), d.shape)
    a = int(np.argmin(((pts - sub[i]) ** 2).sum(1)))
    b = int(np.argmin(((pts - sub[j]) ** 2).sum(1)))
    if a > b:
        a, b = b, a
    arc1 = pts[a:b + 1]
    arc2 = np.vstack([pts[b:], pts[:a + 1]])
    ex, ey = edge_xy if edge_xy is not None else land_xy
    near = lambda arc: np.min(np.hypot(arc[:, 0] - ex, arc[:, 1] - ey))
    arc = arc1 if near(arc1) < near(arc2) else arc2
    simp = approximate_polygon(orient(arc, land_xy), tolerance)
    return simp, (pts[a], pts[b])


# --- georeference ---------------------------------------------------------
class Graticule:
    """Bilinear inversion inside the graticule cell bracketing a point, on
    lines fitted to the engraving. Exact at every fitted intersection."""

    def __init__(self, g):
        self.prime = g["prime_meridian_greenwich"]
        self.east = g.get("counted", "east") == "east"
        self.mer = sorted((float(k), np.array(v)) for k, v in g["meridians"].items())
        self.par = sorted((float(k), np.array(v)) for k, v in g["parallels"].items())
        self.south = g.get("hemisphere", "S") == "S"

    def rules(self, bb, width):
        """Pixels within `width` of any fitted line, over the crop `bb`."""
        x0, y0, x1, y1 = bb
        ys, xs = np.mgrid[y0:y1, x0:x1]
        m = np.zeros(xs.shape, bool)
        for _, c in self.mer:
            m |= np.abs(xs - np.polyval(c, ys)) <= width
        for _, c in self.par:
            m |= np.abs(ys - np.polyval(c, xs)) <= width
        return m

    def lonlat(self, x, y):
        for _ in range(3):
            xs = [np.polyval(c, y) for _, c in self.mer]
            i = max(0, min(len(xs) - 2, int(np.searchsorted(xs, x)) - 1))
            u = (x - xs[i]) / (xs[i + 1] - xs[i])
            lon = self.mer[i][0] + u * (self.mer[i + 1][0] - self.mer[i][0])
            ys = [np.polyval(c, x) for _, c in self.par]
            j = max(0, min(len(ys) - 2, int(np.searchsorted(ys, y)) - 1))
            v = (y - ys[j]) / (ys[j + 1] - ys[j])
            lat = self.par[j][0] + v * (self.par[j + 1][0] - self.par[j][0])
        glon = (lon if self.east else -lon) + self.prime
        glon = (glon + 180) % 360 - 180
        return glon, (-lat if self.south else lat)


class Polar:
    """A polar azimuthal sheet with the pole on it: longitude is the angle
    about the pole, latitude a function of the radius. The same `polar` block
    trace_outline.py reads; fitted by least squares on the engraved lines."""

    def __init__(self, p):
        self.x0, self.y0 = p["pole_px"]
        self.k, self.lon0 = p["k"], p["lon0"]
        self.stereo = p.get("law", "stereographic").startswith("stereo")

    def lonlat(self, x, y):
        dx, dy = x - self.x0, y - self.y0
        r = math.hypot(dx, dy)
        co = 2 * math.degrees(math.atan(r / self.k)) if self.stereo else r / self.k
        lon = (self.lon0 + math.degrees(math.atan2(dx, dy)) + 180) % 360 - 180
        return lon, 90.0 - co

    def rules(self, bb, width, step_lon=5, step_lat=1):
        """Pixels within `width` of a meridian every `step_lon` degrees or a
        parallel every `step_lat`, over the crop `bb`."""
        if self.stereo:
            raise SystemExit("--rule-width: only the equidistant law is supported")
        x0, y0, x1, y1 = bb
        ys, xs = np.mgrid[y0:y1, x0:x1]
        dx, dy = xs - self.x0, ys - self.y0
        r = np.hypot(dx, dy)
        lon = self.lon0 + np.degrees(np.arctan2(dx, dy))
        dlon = np.abs((lon / step_lon + 0.5) % 1 - 0.5) * step_lon
        co = r / self.k
        dlat = np.abs((co / step_lat + 0.5) % 1 - 0.5) * step_lat
        return (np.radians(dlon) * r <= width) | (dlat * self.k <= width)


def aeqd_fwd(lon0, lat0, lon, lat):
    p0, p1, dl = map(math.radians, (lat0, lat, lon - lon0))
    c = math.acos(max(-1, min(1, math.sin(p0) * math.sin(p1) +
                              math.cos(p0) * math.cos(p1) * math.cos(dl))))
    k = 1 if abs(c) < 1e-12 else c / math.sin(c)
    return (k * math.cos(p1) * math.sin(dl) * R_KM,
            k * (math.cos(p0) * math.sin(p1) - math.sin(p0) * math.cos(p1) * math.cos(dl)) * R_KM)


def aeqd_inv(lon0, lat0, x, y):
    p0 = math.radians(lat0)
    rho = math.hypot(x, y) / R_KM
    if rho < 1e-12:
        return lon0, lat0
    c = rho
    lat = math.asin(math.cos(c) * math.sin(p0) + (y / R_KM) * math.sin(c) * math.cos(p0) / rho)
    lon = math.radians(lon0) + math.atan2((x / R_KM) * math.sin(c),
                                          rho * math.cos(c) * math.cos(p0) -
                                          (y / R_KM) * math.sin(c) * math.sin(p0))
    return math.degrees(lon), math.degrees(lat)


class Chord:
    """A frame laid on the shore's chord, tip to tip, in a y-up km plane:
    `t` runs along it as a fraction of its length, and `n` is distance
    seaward (to the left of travel, the land being on the right).

    An islet is carried from one chart's shore to another's in this frame and
    not by the local tangent, which on a wiggly coast points anywhere: at
    0.72 of Vaugondy's shore the coast runs due east along the back of a bay,
    and an offset 'seaward' from there put Moll's islet back on the shore."""

    def __init__(self, arc):
        self.a = arc[0]
        v = arc[-1] - arc[0]
        self.len = float(np.hypot(*v))
        self.u = v / self.len
        self.n = np.array([-self.u[1], self.u[0]])
        self.tn = np.column_stack([(arc - self.a) @ self.u / self.len, (arc - self.a) @ self.n])

    def shore(self, t):
        """The shore's seaward-most crossing of the chord normal at t."""
        best = None
        for (t0, n0), (t1, n1) in zip(self.tn[:-1], self.tn[1:]):
            if (t0 - t) * (t1 - t) <= 0 and t0 != t1:
                n = n0 + (n1 - n0) * (t - t0) / (t1 - t0)
                best = n if best is None else max(best, n)
        if best is None:
            raise SystemExit(f"no shore at {t:.2f} of the chord")
        return best

    def to_frame(self, q):
        t = float((q - self.a) @ self.u / self.len)
        return t, float((q - self.a) @ self.n) - self.shore(t)

    def from_frame(self, t, off):
        return self.a + self.u * t * self.len + self.n * (self.shore(t) + off)


def pale_core(gray, seed, thr, up):
    """The pale pixels joined to `seed`, on a crop upsampled `up` times so a
    core a few px across still has a shape. Moll's islet is 10 x 6 px: too
    small for trace_outline's ring sealing, which refuses cores under 60 px,
    and it does not need it — the hatching round it is solid at this size, so
    the core is simply the pale component under the seed. It holds the same
    bounding box at every threshold from 90 to 110."""
    im = Image.fromarray(gray.astype(np.uint8))
    big = np.asarray(im.resize((im.width * up, im.height * up), Image.BICUBIC), dtype=float)
    lab, _ = ndlabel(big > thr)
    l = lab[seed[1] * up + up // 2, seed[0] * up + up // 2]
    if l == 0:
        raise SystemExit("--islet: the seed is not on a pale core — move it")
    core = binary_fill_holes(lab == l)
    if core[0].any() or core[-1].any() or core[:, 0].any() or core[:, -1].any():
        raise SystemExit("--islet: the core leaks to the window edge — lower --islet-ink")
    return core


def islet(a, chart_json):
    """Trace the islet on its own chart and say where it sits against that
    chart's own coast: fraction along, km off, and its ring in km about its
    centre (east, north)."""
    ch = json.load(open(os.path.join(CHARTS, chart_json + ".json"), encoding="utf-8"))
    eq = ch["equirectangular"]
    img = Image.open(os.path.expanduser(a.islet_image)).convert("RGB")
    cb = [int(v) for v in a.islet_coast_bbox.split(",")]
    gray = np.asarray(img.convert("L").crop(cb), dtype=float)
    sx, sy = [int(v) for v in a.islet.split(",")]
    # the islet's own hatching is part of the band; its pale core is not ink
    mask = band(gray, a.islet_coast_threshold, a.islet_coast_window,
                a.islet_coast_density, [])
    arc, _ = land_arc(mask, [float(v) for v in a.islet_land.split(",")],
                      (cb[0], cb[1]), a.tolerance)
    lat_mid = eq["lat_at_y0"] + (sy - eq["y0"]) / eq["px_per_deg_lat"] * -1
    kx = 111.32 * math.cos(math.radians(abs(lat_mid))) / eq["px_per_deg_lon"]
    ky = 111.0 / eq["px_per_deg_lat"]
    pad, up = 30, 4
    box = (sx - pad, sy - pad, sx + pad, sy + pad)
    core = pale_core(np.asarray(img.convert("L").crop(box), dtype=float),
                     (pad, pad), a.islet_ink, up)
    c = max(find_contours(core.astype(float), 0.5), key=len) / up   # back to source px
    ring = approximate_polygon(c, a.islet_tolerance)
    ys, xs = np.nonzero(core)
    ys, xs = ys / up, xs / up
    cx, cy = xs.mean() + box[0], ys.mean() + box[1]
    # distances in km: Moll's plate is equirectangular, so x and y scales differ
    arc_km = np.column_stack([arc[:, 0] * kx, -arc[:, 1] * ky])
    frac, dist = Chord(arc_km).to_frame(np.array([cx * kx, -cy * ky]))
    ring_km = [((col + box[0] - cx) * kx, -(row + box[1] - cy) * ky) for row, col in ring]
    w = (xs.max() - xs.min() + 1 / up) * kx
    h = (ys.max() - ys.min() + 1 / up) * ky
    return dict(chart=ch, arc=arc, centre=(cx, cy), frac=frac, off_km=dist,
                ring_km=ring_km, size_km=(w, h), core_px=round(core.sum() / up ** 2),
                ring_px=[(col + box[0], row + box[1]) for row, col in ring])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("island")
    ap.add_argument("--chart", required=True)
    ap.add_argument("--image", required=True)
    ap.add_argument("--bbox", help="x0,y0,x1,y1 round the coast (not with --radial)")
    ap.add_argument("--land", help="x,y: any point on the land side")
    ap.add_argument("--radial", help="cx,cy,r0,r1,a0,a1[;...]: trace a dashed shore "
                                     "by rays from a centre on its land side")
    ap.add_argument("--edge", help="x,y: keep the outline's half facing this point "
                                   "instead of the land (the band is on the land side)")
    ap.add_argument("--parts", type=int, default=1,
                    help="keep this many pieces of band, as separate stretches of coast")
    ap.add_argument("--threshold", type=float, default=140, help="grey below = ink")
    ap.add_argument("--window", type=int, default=11, help="density window, px")
    ap.add_argument("--density", type=float, default=0.15)
    ap.add_argument("--blank-box", dest="blank_box",
                    help="x0,y0,x1,y1;... painted out first (lettering, rules)")
    ap.add_argument("--rule-width", dest="rule_width", type=float, default=3,
                    help="paint out the graticule's own lines, this many px each "
                         "side of the fit (0 = keep them)")
    ap.add_argument("--tolerance", type=float, default=1.5, help="simplify, px")
    ap.add_argument("--islet-chart")
    ap.add_argument("--islet-image")
    ap.add_argument("--islet", help="x,y on the islet's pale core, on its chart")
    ap.add_argument("--islet-coast-bbox", dest="islet_coast_bbox")
    ap.add_argument("--islet-land", dest="islet_land", help="x,y on that chart's land side")
    ap.add_argument("--islet-coast-threshold", dest="islet_coast_threshold", type=float, default=140)
    ap.add_argument("--islet-coast-window", dest="islet_coast_window", type=int, default=9)
    ap.add_argument("--islet-coast-density", dest="islet_coast_density", type=float, default=0.2)
    ap.add_argument("--islet-ink", dest="islet_ink", type=float, default=100,
                    help="grey above = the islet's pale core")
    ap.add_argument("--islet-tolerance", dest="islet_tolerance", type=float, default=0.3)
    ap.add_argument("--overlay", help="write the traced line over the source here")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    chart = json.load(open(os.path.join(CHARTS, a.chart + ".json"), encoding="utf-8"))
    G = Polar(chart["polar"]) if "polar" in chart else Graticule(chart["graticule"])
    src = Image.open(os.path.expanduser(a.image)).convert("RGB")
    if a.radial:
        specs = [[float(v) for v in sp.split(",")] for sp in a.radial.split(";")]
        reach = max(sp[3] for sp in specs) + 4
        bb = [int(min(sp[0] for sp in specs) - reach), int(min(sp[1] for sp in specs) - reach),
              int(max(sp[0] for sp in specs) + reach), int(max(sp[1] for sp in specs) + reach)]
    else:
        if not (a.bbox and a.land):
            raise SystemExit("--bbox and --land are needed without --radial")
        bb = [int(v) for v in a.bbox.split(",")]
    blank = []
    if a.blank_box:
        for b in a.blank_box.split(";"):
            x0, y0, x1, y1 = [int(v) for v in b.split(",")]
            blank.append((x0 - bb[0], y0 - bb[1], x1 - bb[0], y1 - bb[1]))
    gray = np.asarray(src.convert("L").crop(bb), dtype=float)
    rules = G.rules(bb, a.rule_width) if a.rule_width else None
    if a.radial:
        for x0, y0, x1, y1 in blank:
            gray[y0:y1, x0:x1] = 255
        arcs = []
        for sp in specs:
            arc = radial_arc(gray, bb[0], bb[1], rules, sp, a.threshold)
            land = [float(v) for v in a.land.split(",")] if a.land else sp[:2]
            arcs.append(approximate_polygon(orient(arc, land), a.tolerance))
        masks = [np.zeros(1)]
    else:
        masks = band(gray, a.threshold, a.window, a.density, blank, rules, a.parts)
        masks = masks if a.parts > 1 else [masks]
        land = [float(v) for v in a.land.split(",")]
        edge = [float(v) for v in a.edge.split(",")] if a.edge else None
        arcs = [land_arc(m, land, (bb[0], bb[1]), a.tolerance, edge)[0] for m in masks]
    arcs.sort(key=lambda q: q[:, 1].mean())          # north of the sheet first
    lines = [[G.lonlat(x, y) for x, y in arc] for arc in arcs]
    allp = [p for line in lines for p in line]

    # a local km plane about the coast's middle, for lengths and for the islet
    lon0 = sum(p[0] for p in allp) / len(allp)
    lat0 = sum(p[1] for p in allp) / len(allp)
    kms = [np.array([aeqd_fwd(lon0, lat0, lo, la) for lo, la in line]) for line in lines]
    lengths = [float(np.hypot(*np.diff(km, axis=0).T).sum()) for km in kms]
    lats = [p[1] for p in allp]; lons = [p[0] for p in allp]
    print(f"{chart['name']}")
    print(f"\n{a.island}: open coast, {len(lines)} part(s), "
          f"{' + '.join(f'{v:.0f}' for v in lengths)} km along the shore   (land on the right)")
    for line in lines:
        print(f"  from {line[0][0]:.2f}, {line[0][1]:.2f}  to {line[-1][0]:.2f}, {line[-1][1]:.2f}"
              f"   {len(line)} points")
    print(f"  lon {min(lons):.2f}..{max(lons):.2f}   lat {min(lats):.2f}..{max(lats):.2f}")
    if not a.radial:
        print(f"  band {' + '.join(str(int(m.sum())) for m in masks)} px")

    geoms = [{"type": "LineString",
              "coordinates": [[round(lo, 4), round(la, 4)] for lo, la in line]}
             for line in lines]
    props = {"id": a.island, "traced_from": chart["name"],
             "source_url": chart.get("source_url", ""),
             "georeference": "the sheet's own graticule, fitted on the engraved lines",
             "open_coast": True, "land_side": "right",
             "centre": [round(lon0, 3), round(lat0, 3)],
             "coast_km": [round(v) for v in lengths] if len(lines) > 1 else round(lengths[0])}
    km, arc = kms[0], arcs[0]

    isl = None
    if a.islet_chart:
        isl = islet(a, a.islet_chart)
        # the same fraction along the shore, the same distance off it, seaward
        c = Chord(km).from_frame(isl["frac"], isl["off_km"])
        ring = [aeqd_inv(lon0, lat0, c[0] + ex, c[1] + ny) for ex, ny in isl["ring_km"]]
        ring = [[round(lo, 4), round(la, 4)] for lo, la in ring]
        area = sum(ring[i][0] * ring[(i + 1) % len(ring)][1] -
                   ring[(i + 1) % len(ring)][0] * ring[i][1] for i in range(len(ring)))
        if area > 0:
            ring = ring[::-1]
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        geoms.append({"type": "Polygon", "coordinates": [ring]})
        clon, clat = aeqd_inv(lon0, lat0, *c)
        print(f"\n  islet from {isl['chart']['name']}")
        print(f"    core {isl['core_px']} px, {isl['size_km'][0]:.1f} x {isl['size_km'][1]:.1f} km"
              f" at that chart's scale")
        print(f"    on its chart: {isl['frac']:.2f} of the way along the shore's chord, "
              f"{isl['off_km']:.1f} km seaward of the shore")
        print(f"    placed at {clon:.3f}, {clat:.3f}")
        props["islet"] = {"traced_from": isl["chart"]["name"],
                          "source_url": isl["chart"].get("source_url", ""),
                          "fraction_along_chord": round(isl["frac"], 3),
                          "offshore_km": round(isl["off_km"], 1),
                          "size_km": [round(v, 1) for v in isl["size_km"]],
                          "centre": [round(clon, 3), round(clat, 3)]}

    if a.overlay:
        pad = 80
        crop = src.crop((bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad))
        s = 3
        crop = crop.resize((crop.width * s, crop.height * s), Image.LANCZOS)
        dr = ImageDraw.Draw(crop)
        for arc in arcs:
            q = [((x - bb[0] + pad) * s, (y - bb[1] + pad) * s) for x, y in arc]
            dr.line(q, fill=(200, 30, 60), width=3)
            dr.ellipse([q[0][0] - 7, q[0][1] - 7, q[0][0] + 7, q[0][1] + 7],
                       outline=(0, 120, 220), width=3)
        tiles = [crop]
        if isl:
            bx = [int(v) for v in a.islet_coast_bbox.split(",")]
            ic = Image.open(os.path.expanduser(a.islet_image)).convert("RGB").crop(
                (bx[0] - 30, bx[1] - 30, bx[2] + 30, bx[3] + 30))
            s2 = 4
            ic = ic.resize((ic.width * s2, ic.height * s2), Image.LANCZOS)
            d2 = ImageDraw.Draw(ic)
            d2.line([((x - bx[0] + 30) * s2, (y - bx[1] + 30) * s2) for x, y in isl["arc"]],
                    fill=(200, 30, 60), width=3)
            d2.polygon([((x - bx[0] + 30) * s2, (y - bx[1] + 30) * s2)
                        for x, y in isl["ring_px"]], outline=(200, 30, 60), width=2)
            tiles.append(ic)
        H = max(t.height for t in tiles)
        out = Image.new("RGB", (sum(t.width for t in tiles) + 20 * (len(tiles) - 1), H), "white")
        x = 0
        for t in tiles:
            out.paste(t, (x, 0)); x += t.width + 20
        out.save(a.overlay)
        print(f"  overlay -> {a.overlay}")

    if len(lines) > 1 and isl:
        raise SystemExit("--islet with --parts is not supported")
    feat = {"type": "Feature", "properties": props,
            "geometry": geoms[0] if len(geoms) == 1 else
            {"type": "GeometryCollection", "geometries": geoms}}
    if a.dry_run:
        print("\n(dry run — nothing written)")
        return
    os.makedirs(OUTDIR, exist_ok=True)
    dest = os.path.join(OUTDIR, f"{a.island}.geojson")
    json.dump(feat, open(dest, "w", encoding="utf-8"), indent=1)
    print(f"  -> {os.path.relpath(dest, ROOT)}")


if __name__ == "__main__":
    main()
