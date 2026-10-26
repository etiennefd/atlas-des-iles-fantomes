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


# An open coast's land is shaded this far behind the line, fading to nothing.
SHADE_KM = 150


def destination(lon, lat, bearing, km):
    """Great-circle step from a point, bearing in degrees from north."""
    p1, l1, b, d = math.radians(lat), math.radians(lon), math.radians(bearing), km / 6371.0
    p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(b))
    l2 = l1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(p1),
                         math.cos(d) - math.sin(p1) * math.sin(p2))
    return [round(math.degrees(l2), 4), round(math.degrees(p2), 4)]


def bearing(a, b):
    p1, p2, dl = math.radians(a[1]), math.radians(b[1]), math.radians(b[0] - a[0])
    return math.degrees(math.atan2(math.sin(dl) * math.cos(p2),
                                   math.cos(p1) * math.sin(p2) -
                                   math.sin(p1) * math.cos(p2) * math.cos(dl)))


def shade(line, km):
    """The land behind an open coast, which trace_coast.py writes with the land
    on its right. Its far edge is the coast's chord pushed inland, not an
    offset of every vertex: an offset of a wiggly shore self-intersects in
    every bay, and the far edge is invisible anyway, the gradient having
    faded out by then. map.ts paints it with two gradients, `across` (coast
    to inland) and `along` (fading out past both ends of the shore), both
    as pairs of points so they can be reprojected each frame."""
    a, b = line[0], line[-1]
    right = bearing(a, b) + 90
    ring = wind_cw([list(p) for p in line] +
                   [destination(*b, right, km), destination(*a, right, km)])
    mid = [sum(p[0] for p in line) / len(line), sum(p[1] for p in line) / len(line)]
    return {"ring": ring, "km": km,
            "across": [[round(v, 4) for v in mid], destination(*mid, right, km)],
            "along": [list(a), list(b)]}


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
            props["shade"] = shade(lines[0], f["properties"].get("shade_km", SHADE_KM))
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
