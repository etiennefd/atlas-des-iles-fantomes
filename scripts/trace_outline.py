#!/usr/bin/env python3
"""
Trace an island's outline from the historical chart in its story.

The shape of a phantom island is a content decision: it is one cartographer's
depiction, not a fact, so the chart is recorded alongside the geometry. Where
no specific depiction exists, leave the island as a blob — a place nobody
agreed on the shape of should look vague.

The scale comes from the chart itself. These plates carry real coastlines too,
so two identifiable landmarks give kilometres per pixel, and the island is
sized by the same yardstick its cartographer used.

    python3 scripts/trace_outline.py antillia \
        --image public/iles/antillia.png \
        --scale 3.19 --rotate 6.4 \
        --source "Bartolomeo Pareto, 1455"

Writes src/data/outlines/{id}.geojson. build_geojson.py prefers it over a blob,
so tracing one island is a complete unit of work.
"""
import argparse, json, math, os, sys

import numpy as np
from PIL import Image
from scipy.ndimage import binary_closing, binary_fill_holes, binary_opening
from skimage.measure import approximate_polygon, find_contours, label, regionprops

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUTDIR = os.path.join(ROOT, "src", "data", "outlines")


def island_mask(img, mode, thr):
    """Isolate the island. On these charts land is washed in a flat colour that
    nothing else on the sheet shares — blue for Antillia — so a channel
    contrast plus the largest connected component is enough."""
    a = np.asarray(img.convert("RGB")).astype(int)
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    if mode == "blue":
        score = B - (R + G) / 2
    elif mode == "red":
        score = R - (G + B) / 2
    elif mode == "green":
        score = G - (R + B) / 2
    elif mode == "dark":
        score = 255 - (R + G + B) / 3
    else:
        raise SystemExit(f"unknown --mode {mode}")

    m = score > thr
    if not m.any():
        raise SystemExit("nothing selected — lower --threshold or change --mode")
    lab = label(m)
    m = lab == max(regionprops(lab), key=lambda p: p.area).label

    # the wash is patchy where the label is written over it; close the gaps,
    # fill the interior, then shave single-pixel parchment specks
    m = binary_closing(m, np.ones((7, 7)))
    m = binary_fill_holes(m)
    m = binary_opening(m, np.ones((3, 3)))
    return binary_fill_holes(m)


def outline(mask, tol):
    c = max(find_contours(mask.astype(float), 0.5), key=len)   # (row, col)
    simple = approximate_polygon(c, tol)
    if len(simple) > 3 and (simple[0] == simple[-1]).all():
        simple = simple[:-1]
    return simple


def wind_cw(pts):
    """Same convention as build_geojson.py: d3-geo reads polygons spherically,
    and a ring wound the wrong way renders as the whole planet minus the
    island."""
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] -
               pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    if area > 0:
        pts = pts[::-1]
    return pts + [pts[0]]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("island")
    p.add_argument("--image", required=True)
    p.add_argument("--scale", type=float, required=True, help="km per pixel")
    p.add_argument("--rotate", type=float, default=0.0,
                   help="degrees CCW; portolans are drawn to magnetic north")
    p.add_argument("--mode", default="blue", choices=("blue", "red", "green", "dark"))
    p.add_argument("--threshold", type=float, default=5.0)
    p.add_argument("--tolerance", type=float, default=1.0, help="simplification, px")
    p.add_argument("--source", default="", help="chart, cartographer, year")
    p.add_argument("--source-url", default="")
    p.add_argument("--coords", help="lon,lat — defaults to the island's yaml")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    if a.coords:
        lon, lat = [float(v) for v in a.coords.split(",")]
    else:
        y = open(os.path.join(ROOT, "src", "content", "islands", f"{a.island}.yaml"),
                 encoding="utf-8").read()
        line = [l for l in y.splitlines() if l.startswith("coords:")][0]
        lon, lat = [float(v) for v in line.split("[")[1].split("]")[0].split(",")]

    mask = island_mask(Image.open(os.path.join(ROOT, a.image)), a.mode, a.threshold)
    ring = outline(mask, a.tolerance)
    ys, xs = np.nonzero(mask)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2

    # pixels -> km east/north about the shape's centre
    th = math.radians(a.rotate)
    pts = []
    for r, c in ring:
        e, n = (c - cx) * a.scale, -(r - cy) * a.scale
        e, n = e * math.cos(th) - n * math.sin(th), e * math.sin(th) + n * math.cos(th)
        dlat = n / 111.0
        dlon = e / (111.32 * math.cos(math.radians(lat)))
        pts.append([round(lon + dlon, 4), round(lat + dlat, 4)])

    pts = wind_cw(pts)
    km_w = (xs.max() - xs.min()) * a.scale
    km_h = (ys.max() - ys.min()) * a.scale
    lons = [q[0] for q in pts]; lats = [q[1] for q in pts]

    print(f"{a.island}: {len(pts)-1} points")
    print(f"  mask       {xs.max()-xs.min()} x {ys.max()-ys.min()} px")
    print(f"  real size  {km_w:.0f} x {km_h:.0f} km   at {a.scale} km/px")
    print(f"  extent     lon {min(lons):.2f}..{max(lons):.2f} ({max(lons)-min(lons):.2f}°)"
          f"  lat {min(lats):.2f}..{max(lats):.2f} ({max(lats)-min(lats):.2f}°)")
    print(f"  centred on {lon}, {lat}")

    feat = {
        "type": "Feature",
        "properties": {
            "id": a.island,
            "traced_from": a.source,
            "source_url": a.source_url,
            "plate": a.image,
            "scale_km_per_px": a.scale,
            "rotation_deg": a.rotate,
            "size_km": [round(km_w), round(km_h)],
        },
        "geometry": {"type": "Polygon", "coordinates": [pts]},
    }
    if a.dry_run:
        print("\n(dry run — nothing written)")
        return
    os.makedirs(OUTDIR, exist_ok=True)
    dest = os.path.join(OUTDIR, f"{a.island}.geojson")
    json.dump(feat, open(dest, "w", encoding="utf-8"), indent=1)
    print(f"  -> {os.path.relpath(dest, ROOT)}")


if __name__ == "__main__":
    main()
