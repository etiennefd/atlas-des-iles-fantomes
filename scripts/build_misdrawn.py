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
                       mainland_to_lat=39.4,
                       cap_wrap=1.1,
                       strait_km=200.0,
                       rough=0.35,
                       borrow="oregon",
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


def inside(ring, lon, lat):
    c = False
    n = len(ring)
    for i in range(n):
        j = (i - 1) % n
        if (ring[i][1] > lat) != (ring[j][1] > lat) and \
           lon < (ring[j][0] - ring[i][0]) * (lat - ring[i][1]) / \
                 ((ring[j][1] - ring[i][1]) or 1e-12) + ring[i][0]:
            c = not c
    return c


def offset_arc(arc, ring, km):
    """Push an open arc outward from the shape it was cut from.

    Orientation is decided by testing the candidate point against the polygon,
    not by pointing away from the centroid. On a long thin island the centroid
    is hundreds of km south of the northern tip, so "away from the centroid"
    sends the whole collar due north instead of following the coast round —
    which is how the strait came out 1300 km wide at its head.
    """
    out = []
    n = len(arc)
    for i, (lon, lat) in enumerate(arc):
        klon = 111.32 * math.cos(math.radians(lat)) or 1e-6
        ax, ay = arc[max(i - 1, 0)]
        bx, by = arc[min(i + 1, n - 1)]
        dx, dy = (bx - ax) * klon, (by - ay) * 111.0
        m = math.hypot(dx, dy) or 1e-9
        nx, ny = -dy / m, dx / m
        cand = [lon + nx * km / klon, lat + ny * km / 111.0]
        if inside(ring, cand[0], cand[1]):
            cand = [lon - nx * km / klon, lat - ny * km / 111.0]
        out.append(cand)
    return out


def resample(path, n):
    klon = 111.32 * math.cos(math.radians(sum(p[1] for p in path) / len(path)))
    d = [0.0]
    for i in range(1, len(path)):
        d.append(d[-1] + math.hypot((path[i][0] - path[i-1][0]) * klon,
                                    (path[i][1] - path[i-1][1]) * 111.0))
    total = d[-1] or 1e-9
    out, j = [], 0
    for i in range(n):
        t = total * i / (n - 1)
        while j < len(d) - 2 and d[j + 1] < t:
            j += 1
        f = (t - d[j]) / ((d[j + 1] - d[j]) or 1e-9)
        out.append([path[j][0] + (path[j+1][0] - path[j][0]) * f,
                    path[j][1] + (path[j+1][1] - path[j][1]) * f])
    return out


def graft_along(seg, path, amp=0.35):
    """Lay a borrowed coastline's wiggle along a path of our choosing.

    The first version grafted between two anchors with a similarity, which
    meant the borrowed shore ran wherever the straight line between them went
    — out to open ocean, taking 900 km of real Oregon with it and opening a
    bay that served no purpose. Following a path instead keeps the strait a
    chosen width the whole way round the island's north end, and the borrowed
    coast supplies only the roughness, as a sideways deviation from that path.
    """
    path = resample(path, len(seg))
    lat0 = sum(p[1] for p in path) / len(path)
    klon = 111.32 * math.cos(math.radians(lat0))
    km = lambda p: (p[0] * klon, p[1] * 111.0)
    # the borrowed coast's deviation from its own chord, in km
    s0, s1 = km(seg[0]), km(seg[-1])
    cx, cy = s1[0] - s0[0], s1[1] - s0[1]
    clen = math.hypot(cx, cy) or 1e-9
    ux, uy = cx / clen, cy / clen
    dev = []
    for q in seg:
        x, y = km(q)
        dx, dy = x - s0[0], y - s0[1]
        dev.append(dx * -uy + dy * ux)          # perpendicular component
    # De-mean and damp. Raw, the Oregon stretch bulges to one side by up to
    # 108 km with a 44 km bias; laid against a 200 km collar that pushes the
    # whole shore across the strait and folds the ring inside out. What is
    # wanted from the borrowed coast is its roughness, not its overall bend.
    mean = sum(dev) / len(dev)
    dev = [(d - mean) * amp for d in dev]
    out = []
    n = len(path)
    for i, (lon, lat) in enumerate(path):
        ax, ay = km(path[max(i - 1, 0)])
        bx, by = km(path[min(i + 1, n - 1)])
        tx, ty = bx - ax, by - ay
        m = math.hypot(tx, ty) or 1e-9
        nx, ny = -ty / m, tx / m
        out.append([lon + nx * dev[i] / klon, lat + ny * dev[i] / 111.0])
    return out


def graft(seg, t0, t1):
    """Lay a borrowed coastline between two anchors.

    A similarity in a local km plane: rotate and scale the real stretch so its
    ends land on the two points the strait has to join, and its wiggle rides
    along unchanged. Orientation is not preserved — the source runs north-south
    and the gap runs east-west — but coastline roughness does not care which
    way it faces.
    """
    lat0 = (t0[1] + t1[1]) / 2
    klon = 111.32 * math.cos(math.radians(lat0))
    to_km = lambda p: (p[0] * klon, p[1] * 111.0)
    s0, s1 = to_km(seg[0]), to_km(seg[-1])
    u0, u1 = to_km(t0), to_km(t1)
    sdx, sdy = s1[0] - s0[0], s1[1] - s0[1]
    udx, udy = u1[0] - u0[0], u1[1] - u0[1]
    slen = math.hypot(sdx, sdy) or 1e-9
    k = math.hypot(udx, udy) / slen
    th = math.atan2(udy, udx) - math.atan2(sdy, sdx)
    cs, sn = math.cos(th) * k, math.sin(th) * k
    out = []
    for p in seg:
        x, y = to_km(p)
        dx, dy = x - s0[0], y - s0[1]
        out.append([(u0[0] + dx * cs - dy * sn) / klon,
                    (u0[1] + dx * sn + dy * cs) / 111.0])
    return out


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
    # Stop following the chart's mainland before its head: Vinckeboons bends
    # that coast east to -111.5, so carrying it to the top opens a 370 km
    # swathe of water across the north and a bay that serves nothing. Above
    # this latitude the shore is the collar instead, which keeps the strait
    # roughly the width the chart gives it further south.
    west = [p for p in flank(mainland, "west")
            if lat_s <= p[1] <= spec["mainland_to_lat"]]
    if not east or not west:
        raise SystemExit("strait: arcs are empty, check gulf_mouth_lat")

    north_tip = east[0]
    ring = (
        east                              # island's east shore, north to south
        + [[west[-1][0], west[-1][1]]]    # across the mouth of the Gulf
        + west[::-1]                      # continent's west shore, south to north
    )
    # The charts stop around 41.4 N and the strait still has to round the
    # island's north end and reach open water. Left as a straight run to the
    # ocean it took 900 km of real Oregon with it and opened a bay that served
    # no purpose, so the northern shore now follows the island's own coast at a
    # set distance, with a real coastline supplying the roughness.
    lat_c = spec["mainland_to_lat"]
    tip_lat = north_tip[1]
    cap_e = [q for q in east if q[1] >= lat_c][::-1]          # east shore, up to the tip
    cap_w = [q for q in flank(island, "west")
             if q[1] >= tip_lat - spec["cap_wrap"]]           # round the tip, a little way down
    cap = offset_arc(cap_e + cap_w, island, spec["strait_km"])
    # converge from the chart's wide gulf head onto that offset, rather than
    # stepping across it
    lead = [[west[0][0] + (cap[0][0] - west[0][0]) * t,
             west[0][1] + (cap[0][1] - west[0][1]) * t] for t in (0.3, 0.62, 0.86)]
    borrowed = os.path.join(ROOT, "src", "data", "borrowed", spec["borrow"] + ".json")
    seg = json.load(open(borrowed, encoding="utf-8"))["coordinates"]
    ring += graft_along(seg, [west[0]] + lead + cap, spec["rough"])
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
