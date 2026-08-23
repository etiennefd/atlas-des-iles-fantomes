#!/usr/bin/env python3
"""
Trace an island's outline from the historical chart that defines it.

The shape of a phantom island is a content decision: it is one cartographer's
claim, not a fact, so the chart is recorded alongside the geometry. Where no
specific depiction exists, leave the island as a blob — a place nobody agreed
on the shape of should look vague.

Everything is derived by georeferencing the chart, not by guessing. Portolans
carry real coastlines as well as invented islands, so a handful of identifiable
landmarks fit a similarity transform (scale + rotation + offset) from pixels to
lon/lat. That single transform then gives the island's position, its size, and
the chart's own rotation at once — an island placed by the same yardstick its
cartographer used.

    python3 scripts/trace_outline.py antillia --chart pizzigano \
        --image ~/scratch/charts/pizzigano.jpg \
        --mode red --bbox 1050,1450,1400,1950

Landmarks live in scripts/charts/<chart>.json. The chart rasters themselves are
deliberately NOT committed: they are megabytes of tracing input, and the
provenance URL is enough to reproduce the work.

Writes src/data/outlines/{id}.geojson; build_geojson.py prefers it over a blob,
so tracing one island is a complete unit of work.
"""
import argparse, json, math, os

import numpy as np
from PIL import Image
from scipy.ndimage import binary_closing, binary_fill_holes, binary_opening
from skimage.measure import approximate_polygon, find_contours, label, regionprops

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUTDIR = os.path.join(ROOT, "src", "data", "outlines")
CHARTS = os.path.join(HERE, "charts")


# --- georeference ---------------------------------------------------------
def fit_transform(landmarks, lat0):
    """Least-squares similarity from chart pixels to a local lon*cos(lat0)/lat
    plane. Image y grows downward and latitude grows upward, so y is flipped
    first — a similarity cannot express a reflection, and without the flip the
    fit absorbs it as a ~100 degree rotation and everything is nonsense."""
    K = math.cos(math.radians(lat0))
    A, b = [], []
    for m in landmarks:
        x, y = m["x"], -m["y"]
        A += [[x, -y, 1, 0], [y, x, 0, 1]]
        b += [m["lon"] * K, m["lat"]]
    p = np.linalg.lstsq(np.array(A, float), np.array(b, float), rcond=None)[0]
    return p, K


def to_lonlat(p, K, x, y):
    a, bb, tx, ty = p
    y = -y
    return ((a * x - bb * y + tx) / K, bb * x + a * y + ty)


def residuals(p, K, landmarks):
    out = []
    for m in landmarks:
        lon, lat = to_lonlat(p, K, m["x"], m["y"])
        out.append((m["name"], math.hypot((lon - m["lon"]) * 111 * K,
                                          (lat - m["lat"]) * 111)))
    return out


# --- the island ------------------------------------------------------------
def island_mask(img, mode, thr, bbox, close):
    """Isolate the island. On these charts land is a flat colour wash that
    nothing else nearby shares. Settlement cartouches are written *on* the
    island, so holes are filled: they are labels, not lakes."""
    a = np.asarray(img.convert("RGB")).astype(int)
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    score = {"red":   R - (G + B) / 2,
             "blue":  B - (R + G) / 2,
             "green": G - (R + B) / 2,
             "dark":  255 - (R + G + B) / 3}[mode]
    m = score > thr
    if bbox:
        x0, y0, x1, y1 = bbox
        keep = np.zeros_like(m); keep[y0:y1, x0:x1] = True
        m &= keep
    if not m.any():
        raise SystemExit("nothing selected — adjust --threshold/--mode/--bbox")
    lab = label(m)
    m = lab == max(regionprops(lab), key=lambda q: q.area).label
    m = binary_fill_holes(binary_closing(m, np.ones((close, close))))
    return binary_fill_holes(binary_opening(m, np.ones((5, 5))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("island")
    ap.add_argument("--chart", required=True, help="scripts/charts/<name>.json")
    ap.add_argument("--image", required=True, help="local copy of the chart raster")
    ap.add_argument("--mode", default="red", choices=("red", "blue", "green", "dark"))
    ap.add_argument("--threshold", type=float, default=45.0)
    ap.add_argument("--closing", type=int, default=21)
    ap.add_argument("--tolerance", type=float, default=2.0, help="simplify, px")
    ap.add_argument("--bbox", help="x0,y0,x1,y1 to restrict the search")
    ap.add_argument("--centre", help="lon,lat override. The chart still gives "
                    "shape, size and orientation; use this where its own "
                    "georeference is not trustworthy — typically the imagined "
                    "ocean west of everything it actually surveyed.")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    chart = json.load(open(os.path.join(CHARTS, a.chart + ".json"), encoding="utf-8"))
    lms = chart["landmarks"]
    lat0 = sum(m["lat"] for m in lms) / len(lms)
    p, K = fit_transform(lms, lat0)
    kmpx = math.hypot(p[0], p[1]) * 111.0
    rot = math.degrees(math.atan2(p[1], p[0]))

    res = residuals(p, K, lms)
    rms = math.sqrt(sum(e * e for _, e in res) / len(res))
    print(f"{chart['name']}")
    print(f"  {kmpx:.3f} km/px   chart rotation {rot:+.1f}°   RMS {rms:.0f} km")
    for name, e in res:
        print(f"     {name:14} {e:5.0f} km")

    bbox = [int(v) for v in a.bbox.split(",")] if a.bbox else None
    mask = island_mask(Image.open(os.path.expanduser(a.image)), a.mode,
                       a.threshold, bbox, a.closing)
    ring = approximate_polygon(max(find_contours(mask.astype(float), 0.5), key=len),
                               a.tolerance)
    if len(ring) > 3 and (ring[0] == ring[-1]).all():
        ring = ring[:-1]

    pts = [[round(v, 4) for v in to_lonlat(p, K, c, r)] for r, c in ring]
    # d3-geo reads polygons spherically: wound the wrong way, the island renders
    # as the whole planet except itself.
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] -
               pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    if area > 0:
        pts = pts[::-1]
    pts.append(pts[0])

    ys, xs = np.nonzero(mask)
    clon, clat = to_lonlat(p, K, (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2)
    moved = None
    if a.centre:
        tlon, tlat = [float(v) for v in a.centre.split(",")]
        dlon, dlat = tlon - clon, tlat - clat
        pts = [[round(q[0] + dlon, 4), round(q[1] + dlat, 4)] for q in pts]
        moved = (round(clon, 2), round(clat, 2))
        clon, clat = tlon, tlat
    lons = [q[0] for q in pts]; lats = [q[1] for q in pts]
    km_w = (max(lons) - min(lons)) * 111.32 * math.cos(math.radians(clat))
    km_h = (max(lats) - min(lats)) * 111.0

    print(f"\n{a.island}: {len(pts)-1} points")
    if moved:
        print(f"  centre     {clon:.2f}, {clat:.2f}   (override; chart put it at {moved[0]}, {moved[1]})")
    else:
        print(f"  centre     {clon:.2f}, {clat:.2f}   (from the chart)")
    print(f"  extent     {km_w:.0f} x {km_h:.0f} km")
    print(f"  lon {min(lons):.2f}..{max(lons):.2f}   lat {min(lats):.2f}..{max(lats):.2f}")

    feat = {"type": "Feature",
            "properties": {"id": a.island,
                           "traced_from": chart["name"],
                           "source_url": chart.get("source_url", ""),
                           "georeference": {"km_per_px": round(kmpx, 3),
                                            "chart_rotation_deg": round(rot, 1),
                                            "landmark_rms_km": round(rms),
                                            "landmarks": len(lms)},
                           "centre": [round(clon, 3), round(clat, 3)],
                           "centre_from_chart": moved,
                           "size_km": [round(km_w), round(km_h)]},
            "geometry": {"type": "Polygon", "coordinates": [pts]}}
    if a.dry_run:
        print("\n(dry run — nothing written)")
        return
    os.makedirs(OUTDIR, exist_ok=True)
    dest = os.path.join(OUTDIR, f"{a.island}.geojson")
    json.dump(feat, open(dest, "w", encoding="utf-8"), indent=1)
    print(f"  -> {os.path.relpath(dest, ROOT)}")


if __name__ == "__main__":
    main()
