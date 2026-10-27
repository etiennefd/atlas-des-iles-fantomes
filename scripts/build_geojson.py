#!/usr/bin/env python3
"""
Build src/data/islands.geojson from the island YAML files.

Placeholder shapes only: a deterministic wobbly blob per island, so the map
reads as an archipelago rather than a dot-density plot. Replace island by
island with traced outlines as the research gets done.

Islands with coords_confidence: unknown are skipped and listed at the end.
"""
import os, json, math, glob, hashlib, re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src", "content", "islands")
OUTLINES = os.path.join(HERE, "..", "src", "data", "outlines")
OUT = os.path.join(HERE, "..", "src", "data", "islands.geojson")

# Rough apparent size in degrees, by kind. Deliberately small — these are
# placeholders and shouldn't look authoritative.
RADIUS = {"island": 1.1, "misdrawn": 3.0, "reef": 0.25, "coast": 1.1}


def parse(path):
    """Minimal YAML reader — these files are flat and we control them."""
    d, key = {}, None
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        if line.startswith("  ") and key:
            d[key] = (d[key] + " " + line.strip()).strip()
            continue
        m = re.match(r"^([a-z_]+):\s*(.*)$", line.rstrip("\n"))
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val == ">-":
            d[key] = ""
        else:
            d[key] = val
            key = None
    return d


def blob(lon, lat, r, seed, n=24):
    """Deterministic irregular polygon. Latitude-corrected so it doesn't
    smear near the poles."""
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    coslat = max(math.cos(math.radians(lat)), 0.35)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        # three summed harmonics keep it organic without looking noisy
        w = (
            1.0
            + 0.26 * math.sin(a * 2 + (h % 100) / 15.0)
            + 0.15 * math.sin(a * 3 + ((h >> 7) % 100) / 9.0)
            + 0.08 * math.sin(a * 5 + ((h >> 13) % 100) / 5.0)
        )
        pts.append([
            round(lon + math.cos(a) * r * w / coslat, 4),
            round(lat + math.sin(a) * r * w, 4),
        ])
    return [wind_cw(pts)]


def scale_to_size(f):
    """`size_km` is the control, not a readout. Edit it, rebuild, and the
    island changes size — scaled about its own centre so the position holds.
    Without this the number sat in the file looking authoritative while the
    coordinates quietly disagreed with it."""
    geom = f["geometry"]
    want = f.get("properties", {}).get("size_km")
    if not want:
        return geom
    if geom["type"] == "MultiPolygon":
        # a plate that drew the island's satellites too. Scale the group about
        # the main island's centre so the archipelago keeps its arrangement.
        polys = geom["coordinates"]
        ring = max((p[0] for p in polys), key=len)
        lats = [q[1] for q in ring]; lons = [q[0] for q in ring]
        cy = (min(lats) + max(lats)) / 2; cx = (min(lons) + max(lons)) / 2
        have_km = (max(lats) - min(lats)) * 111.0
        if have_km <= 0:
            return geom
        k = float(want[1]) / have_km
        if abs(k - 1.0) < 1e-9:
            return geom
        return {"type": "MultiPolygon", "coordinates": [
            [[[round(cx + (x - cx) * k, 5), round(cy + (y - cy) * k, 5)]
              for x, y in r] for r in poly] for poly in polys]}
    ring = geom["coordinates"][0]
    lats = [p[1] for p in ring]
    lons = [p[0] for p in ring]
    cy = (min(lats) + max(lats)) / 2
    cx = (min(lons) + max(lons)) / 2
    have_km = (max(lats) - min(lats)) * 111.0
    if have_km <= 0:
        return geom
    k = float(want[1]) / have_km
    if abs(k - 1.0) < 1e-9:
        return geom
    scaled = [[round(cx + (x - cx) * k, 5), round(cy + (y - cy) * k, 5)]
              for x, y in ring]
    return {"type": "Polygon", "coordinates": [scaled]}


def wind_cw(pts):
    """d3-geo reads polygons spherically: an exterior ring wound the wrong way
    means 'the whole planet except this bit', which renders as a disc covering
    the map. Force clockwise in lon/lat, and close the ring."""
    area = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        area += x1 * y2 - x2 * y1
    if area > 0:            # counterclockwise -> flip
        pts = pts[::-1]
    return pts + [pts[0]]


# An open coast's land is shaded behind the line as a band that follows the
# shore, solid there and fading out inland and at both ends. Its depth is in
# proportion to the shore, 0.285 of its chord — 75 km on Davis Land's 263 km —
# since a fixed depth turns short shores (Bradley Land's brackets are 30-50 km
# across) into long bars. `shade_km` in an outline file overrides it.
SHADE_RATIO = 0.285
SHADE_LAYERS = 32
R_KM = 6371.0


def chord_km(line):
    (l1, p1), (l2, p2) = [map(math.radians, q) for q in (line[0], line[-1])]
    return R_KM * math.acos(max(-1.0, min(1.0, math.sin(p1) * math.sin(p2) +
                                          math.cos(p1) * math.cos(p2) * math.cos(l2 - l1))))


def aeqd_fwd(lon, lat, lon0, lat0):
    p, p0, dl = math.radians(lat), math.radians(lat0), math.radians(lon - lon0)
    cc = max(-1.0, min(1.0, math.sin(p0) * math.sin(p) + math.cos(p0) * math.cos(p) * math.cos(dl)))
    c = math.acos(cc)
    k = 1.0 if c < 1e-12 else c / math.sin(c)
    return (R_KM * k * math.cos(p) * math.sin(dl),
            R_KM * k * (math.cos(p0) * math.sin(p) - math.sin(p0) * math.cos(p) * math.cos(dl)))


def aeqd_inv(x, y, lon0, lat0):
    p0 = math.radians(lat0)
    rho = math.hypot(x, y)
    if rho < 1e-9:
        return [lon0, lat0]
    c = rho / R_KM
    lat = math.asin(math.cos(c) * math.sin(p0) + y * math.sin(c) * math.cos(p0) / rho)
    lon = math.radians(lon0) + math.atan2(x * math.sin(c),
                                          rho * math.cos(p0) * math.cos(c) - y * math.sin(p0) * math.sin(c))
    return [round(math.degrees(lon), 4), round(math.degrees(lat), 4)]


def shade(line, km):
    """The land behind an open coast, which trace_coast.py writes with the land
    on its right, as a stack of translucent layers rather than a gradient.

    Each layer runs from one end of the shore to the other along the shore
    itself and closes inland a little deeper than the last, so all of them
    overlap at the shore, which is solid along its whole length, and they thin
    out inland. Each layer's opacity is set so the stack's total at depth x
    (0 at the shore, 1 at the far edge) is 0.97 (1 - smoothstep(x)): the
    outermost layer is too faint to read as an edge. Two things were tried
    first and dropped (October 2026). Linear gradients across and along the
    shore drew a fuzzy rectangle. A blurred fill can only keep the shore hard
    by being clipped, and wherever the clip runs through open sea past the
    shore's ends it shows as a straight cut — unless the fill fades out well
    before the ends, which leaves them bare.

    The inland edges follow a smoothed copy of the shore, not every bay in
    it, and taper into both ends. Built in a frame on an azimuthal-equidistant
    plane centred on the chord's midpoint: s along the chord, t inland."""
    a, b = line[0], line[-1]
    ax, ay = aeqd_fwd(*b, *a)
    m = aeqd_inv(ax / 2, ay / 2, *a)
    pts = [aeqd_fwd(*q, *m) for q in line]
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    L = math.hypot(x1 - x0, y1 - y0)
    u = ((x1 - x0) / L, (y1 - y0) / L)
    n = (u[1], -u[0])
    st = [(x * u[0] + y * u[1], x * n[0] + y * n[1]) for x, y in pts]
    back = lambda s, t: aeqd_inv(s * u[0] + t * n[0], s * u[1] + t * n[1], *m)

    def shore_t(f):
        # the shore's offset from the chord at fraction f along it
        goal = st[0][0] + f * (st[-1][0] - st[0][0])
        i = min(range(len(st) - 1), key=lambda i: abs((st[i][0] + st[i + 1][0]) / 2 - goal))
        (s0, t0), (s1, t1) = st[i], st[i + 1]
        g = 0.0 if s1 == s0 else max(0.0, min(1.0, (goal - s0) / (s1 - s0)))
        return t0 + g * (t1 - t0)

    fs = [i / 80 for i in range(81)]
    ts = [shore_t(f) for f in fs]
    soft = []
    for i in range(81):
        w = [math.exp(-0.5 * ((j - i) / 8) ** 2) for j in range(81)]
        soft.append(sum(p * q for p, q in zip(w, ts)) / sum(w))
    taper = lambda f: max(0.0, 1 - abs(2 * f - 1) ** 4) ** 0.25

    # Every layer runs straight inland from the same points on the shore, so
    # rather than 32 copies of the shore this writes each point's two ends —
    # `near` on the shore, `far` at full depth — and `start`, the fraction of
    # full depth at which a layer's inland edge clears the shore there (the
    # edge follows a smoothed shore, so in a bay it starts behind the coast).
    # map.ts interpolates the layers; `alpha` is each one's opacity.
    N = SHADE_LAYERS
    def total(x):
        return 0.97 * (1 - x * x * (3 - 2 * x))
    O = [total((k - 0.5) / N) for k in range(1, N + 1)] + [0.0]
    alpha = [round(1 - (1 - O[k]) / (1 - O[k + 1]), 4) for k in range(N)]
    near, far, start = [], [], []
    for i, f in enumerate(fs):
        sx = st[0][0] + f * (st[-1][0] - st[0][0])
        span = km * taper(f)
        t_far = max(ts[i], soft[i] + span)
        near.append(back(sx, ts[i]))
        far.append(back(sx, t_far))
        # negative where a headland stands out past the smoothed edge: there
        # even the thinnest layer starts inland of the coast
        start.append(round(min(1.0, (ts[i] - soft[i]) / span), 4) if span > 0 else 1.0)
    return {"km": km, "near": near, "far": far, "start": start, "alpha": alpha}


features, skipped, outlined = [], [], []
for path in sorted(glob.glob(os.path.join(SRC, "*.yaml"))):
    iid = os.path.splitext(os.path.basename(path))[0]
    d = parse(path)
    if "coords" not in d:
        skipped.append(iid)
        continue
    lon, lat = [float(x) for x in d["coords"].strip("[]").split(",")]
    kind = d.get("kind", "island")
    props = {
        "id": iid,
        "kind": kind,
        "confidence": d.get("coords_confidence", "unknown"),
        "placeholder": True,
    }
    traced = os.path.join(OUTLINES, iid + ".geojson")
    if os.path.exists(traced):
        pass
        # A hand-traced depiction beats a blob. scripts/trace_outline.py wrote
        # it and already forced clockwise winding; provenance rides along.
        f = json.load(open(traced, encoding="utf-8"))
        geom = scale_to_size(f)
        props["placeholder"] = False
        props["traced_from"] = f["properties"].get("traced_from", "")
        if f["properties"].get("open_coast"):
            lines = [g["coordinates"] for g in
                     (geom["geometries"] if geom["type"] == "GeometryCollection" else [geom])
                     if g["type"] == "LineString"]
            # one shade per stretch of shore: Balch draws Bradley Land in two
            props["shade"] = [shade(l, f["properties"].get("shade_km",
                                                           round(SHADE_RATIO * chord_km(l))))
                              for l in lines]
        outlined.append(iid)
    elif kind == "reef":
        geom = {"type": "Point", "coordinates": [lon, lat]}
    else:
        r = RADIUS[kind]
        # Van der Grinten stretches the poles brutally; scale placeholder
        # blobs down above 60 deg so Crocker Land isn't a scar across the Arctic.
        if abs(lat) > 60:
            r *= max(0.3, math.cos(math.radians(abs(lat))) / math.cos(math.radians(60)))
        geom = {"type": "Polygon", "coordinates": blob(lon, lat, r, iid)}
    features.append({"type": "Feature", "properties": props, "geometry": geom})

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump({"type": "FeatureCollection", "features": features}, f, indent=1)

print(f"{len(features)} features written to {os.path.relpath(OUT, HERE)}")
if outlined:
    print(f"traced outlines used: {', '.join(outlined)}")
if skipped:
    print("no coordinates yet: " + ", ".join(skipped))
