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
OUT = os.path.join(HERE, "..", "src", "data", "islands.geojson")

# Rough apparent size in degrees, by kind. Deliberately small — these are
# placeholders and shouldn't look authoritative.
RADIUS = {"island": 1.1, "misdrawn": 3.0, "reef": 0.25}


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


features, skipped = [], []
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
    if kind == "reef":
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
if skipped:
    print("no coordinates yet: " + ", ".join(skipped))
