#!/usr/bin/env python3
"""
Build the regions where a `misdrawn` island's chart overrides real geography.

A misdrawn island is not an invention — it is real land drawn wrong — so
showing it means *replacing* a piece of the basemap, not drawing on top of it.
And erasing the island's own footprint is not enough: the claim about
California is that the isthmus is a strait, so the water has to be opened up
east of the phantom coast as well, or nothing has changed.

The corridor is derived from the island's own eastern shore, pushed east by a
width that tapers away southward — below the Gulf of California's head there
is already sea there and widening would eat mainland Mexico.

Writes public/data/misdrawn.geojson, which map.ts uses to mask the land layer.
"""
import json, math, os

import numpy as np
from scipy.ndimage import distance_transform_edt
from skimage.draw import polygon as draw_polygon
from skimage.measure import approximate_polygon, find_contours

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUT = os.path.join(ROOT, "public", "data", "misdrawn.geojson")

# id -> buffer width in km at/above `full_lat`, tapering to `min_km` at `min_lat`
SPEC = {
    "californie": dict(mainland="californie-mainland",
                       gulf_mouth_lat=22.6,
                       north_open=(-127.5, 44.6),
                       grow_km=70.0),
}


def wind_cw(ring):
    """d3-geo reads polygons spherically: a ring wound the wrong way is not a
    hole, it is everything except the hole. Hand-built rings have to be forced
    the same way trace_outline forces traced ones — the symptom is geoBounds
    coming back as the whole planet."""
    r = ring[:-1] if ring[0] == ring[-1] else ring[:]
    area = sum(r[i][0] * r[(i + 1) % len(r)][1] - r[(i + 1) % len(r)][0] * r[i][1]
               for i in range(len(r)))
    if area > 0:
        r = r[::-1]
    return r + [r[0]]


def footprint(parts, km, step=0.02):
    """The island's own area, grown a little, as the region to cut out.

    Grown because the real coast is not the charted one: leave the footprint
    at exactly the traced outline and small real islands survive just outside
    it — Cedros, the Channel Islands, specks of Baja's shore — and sit there
    in dark grey under the phantom. Done on a raster, because offsetting a
    coastline vertex by vertex self-intersects on every concave bay and leaves
    unerased shards stranded in the new sea.
    """
    lons = [p[0] for q in parts for p in q]
    lats = [p[1] for q in parts for p in q]
    pad = km / 100.0 + 1.0
    lo0, lo1 = min(lons) - pad * 1.6, max(lons) + pad * 1.6
    la0, la1 = min(lats) - pad, max(lats) + pad
    nx = int((lo1 - lo0) / step) + 1
    ny = int((la1 - la0) / step) + 1
    grid = np.zeros((ny, nx), bool)
    for q in parts:
        rr, cc = draw_polygon([(p[1] - la0) / step for p in q],
                              [(p[0] - lo0) / step for p in q], grid.shape)
        grid[rr, cc] = True
    lat0 = (la0 + la1) / 2
    dist = distance_transform_edt(
        ~grid, sampling=(111.0 * step, 111.32 * math.cos(math.radians(lat0)) * step))
    mask = grid | (dist <= km)
    out = []
    for c in find_contours(mask.astype(float), 0.5):
        c = approximate_polygon(c, 1.5)
        if len(c) >= 4:
            out.append(wind_cw([[lo0 + x * step, la0 + y * step] for y, x in c]))
    return out


def flank(ring, side):
    """The arc down one side of a shape, north tip to south tip."""
    r = ring[:-1] if ring[0] == ring[-1] else ring[:]
    n = max(range(len(r)), key=lambda i: r[i][1])
    s = min(range(len(r)), key=lambda i: r[i][1])
    a = r[n:] + r[:s + 1] if n > s else r[n:s + 1]
    b = r[s:] + r[:n + 1] if s > n else r[s:n + 1]
    mean = lambda q: sum(p[0] for p in q) / len(q)
    pick = (a if mean(a) > mean(b) else b) if side == "east" else \
           (a if mean(a) < mean(b) else b)
    return pick if pick[0][1] > pick[-1][1] else pick[::-1]


def strait(island, mainland, spec):
    """The channel the chart opens between the phantom island and the continent.

    Carving only this plus the island's own footprint leaves the real mainland
    real: its coast east of the channel is the genuine one, not a synthetic
    curve, and there is no seam where a patch would have ended. The channel's
    eastern shore is the coastline the cartographer actually drew.

    North of where the chart's mainland stops the shore has to be invented —
    the chart runs the strait off the top of its sheet and simply does not say.
    It sweeps west round the island's north tip and out to the Pacific, which
    is the one direction that separates the island without inventing a coast
    anyone could check.
    """
    lat_s = spec["gulf_mouth_lat"]
    east = [p for p in flank(island, "east") if p[1] >= lat_s]
    west = [p for p in flank(mainland, "west") if p[1] >= lat_s]
    if not east or not west:
        raise SystemExit("strait: arcs are empty, check gulf_mouth_lat")

    north_tip = east[0]
    nx, ny = spec["north_open"]          # a point in open Pacific, north-west
    ring = (
        east                              # island's east shore, north to south
        + [[west[-1][0], west[-1][1]]]    # across the mouth of the Gulf
        + west[::-1]                      # continent's west shore, south to north
        # then the invented part: round the island's north end to open water
        + [[west[0][0] - 1.5, west[0][1] + 1.2],
           [west[0][0] - 4.5, west[0][1] + 2.4],
           [north_tip[0] + 0.6, ny],
           [nx, ny - 0.4]]
    )
    return wind_cw(ring)


feats = []
for iid, spec in SPEC.items():
    src = os.path.join(ROOT, "src", "data", "outlines", f"{iid}.geojson")
    mnl = os.path.join(ROOT, "src", "data", "outlines", f"{spec['mainland']}.geojson")
    if not (os.path.exists(src) and os.path.exists(mnl)):
        print(f"  {iid}: needs both {iid}.geojson and {spec['mainland']}.geojson")
        continue
    g = json.load(open(src, encoding="utf-8"))["geometry"]
    parts = ([p[0] for p in g["coordinates"]] if g["type"] == "MultiPolygon"
             else [g["coordinates"][0]])
    main = max(parts, key=len)
    mainland = json.load(open(mnl, encoding="utf-8"))["geometry"]["coordinates"][0]

    rings = footprint(parts, spec["grow_km"]) + [strait(main, mainland, spec)]
    feats.append({"type": "Feature",
                  "properties": {"id": iid, "part": "erase"},
                  "geometry": {"type": "MultiPolygon",
                               "coordinates": [[r] for r in rings]}})
    print(f"  {iid}: {len(parts)} island part(s) -> {len(rings)} erase ring(s)")

json.dump({"type": "FeatureCollection", "features": feats},
          open(OUT, "w", encoding="utf-8"))
print(f"-> {os.path.relpath(OUT, ROOT)}  ({len(feats)} misdrawn island(s))")
