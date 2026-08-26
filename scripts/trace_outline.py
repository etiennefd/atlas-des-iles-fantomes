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
from scipy.ndimage import binary_closing, binary_fill_holes, gaussian_filter
from skimage.measure import approximate_polygon, find_contours, label, regionprops
from skimage.morphology import binary_closing as binary_closing_sk
from skimage.morphology import binary_opening, disk, square

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
def island_mask(img, mode, thr, bbox, close, se="disk", open_r=0,
                upsample=1, smooth=0.0, bright=False, blank=None, despeckle=0):
    """Isolate the island. On these charts land is a flat colour wash that
    nothing else nearby shares. Settlement cartouches are written *on* the
    island, so holes are filled: they are labels, not lakes."""
    if blank:
        # A neatline running close to the coast is a hole-closing bridge
        # waiting to happen: close the two together and the fill floods the
        # water between them. Paint the rule out first, in source pixels.
        img = img.convert("RGB")
        img.paste((255, 255, 255), (0, blank[0], img.width, blank[1]))
    x0, y0 = (bbox[0], bbox[1]) if bbox else (0, 0)
    if bbox:
        img = img.crop(tuple(bbox))
    if upsample > 1:
        img = img.resize((img.width * upsample, img.height * upsample), Image.LANCZOS)
    a = np.asarray(img.convert("RGB")).astype(int)
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    score = {"red":   R - (G + B) / 2,
             "blue":  B - (R + G) / 2,
             "green": G - (R + B) / 2,
             "dark":  255 - (R + G + B) / 3}[mode]
    if smooth:
        score = gaussian_filter(score.astype(float), smooth)
    m = (score < thr) if bright else (score > thr)
    if open_r:
        # Squared bays need a square element: a disk cannot hold a right angle,
        # and rounds every notch into a wave. (Canepa's north-west bay.)
        el = square(open_r) if se == "square" else disk(open_r)
        m = binary_opening(m, el)
    if not m.any():
        raise SystemExit("nothing selected — adjust --threshold/--mode/--bbox")
    lab = label(m)
    m = lab == max(regionprops(lab), key=lambda q: q.area).label
    # disk(close), not a close x close box: the box is far weaker, and a gap
    # left in the coast band means fill_holes cannot close the interior at all
    # — the island comes out as a ring rather than a shape.
    m = binary_fill_holes(binary_closing_sk(m, disk(close)))
    m = binary_fill_holes(m)
    if despeckle:
        # Survey stations drawn *on* the coastline — a circle, a triangle —
        # get absorbed by the fill and come out as warts. They are symbols,
        # not headlands. Take only the residue an opening strips, and only the
        # small pieces of it, so the rest of the coast is left untouched.
        res = m & ~binary_opening(m, disk(6))
        lab2 = label(res)
        for q in regionprops(lab2):
            if q.area < despeckle:
                m[lab2 == q.label] = False
    return m, (x0, y0)


def manual(a, chart):
    """No landmarks on this chart yet, so the chart gives only the silhouette;
    size and position are set explicitly. Georeference it properly and this
    path goes away."""
    if not (a.height_km and a.centre):
        raise SystemExit("this chart has no landmarks yet: pass --height-km and --centre")
    lon, lat = [float(v) for v in a.centre.split(",")]
    bbox = [int(v) for v in a.bbox.split(",")] if a.bbox else None
    mask, _ = island_mask(Image.open(os.path.expanduser(a.image)), a.mode,
                          a.threshold, bbox, a.closing, a.se, a.open_r,
                          a.upsample, a.smooth, a.bright, a.blank, a.despeckle)
    ring = approximate_polygon(max(find_contours(mask.astype(float), 0.5), key=len),
                               a.tolerance)
    if len(ring) > 3 and (ring[0] == ring[-1]).all():
        ring = ring[:-1]
    ys, xs = np.nonzero(mask)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    kmpx = a.height_km / (ys.max() - ys.min())   # already in upsampled px
    pts = []
    for r, c in ring:
        dlat = -(r - cy) * kmpx / 111.0
        dlon = (c - cx) * kmpx / (111.32 * math.cos(math.radians(lat)))
        pts.append([round(lon + dlon, 4), round(lat + dlat, 4)])
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] -
               pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    if area > 0:
        pts = pts[::-1]
    pts.append(pts[0])
    lons = [q[0] for q in pts]; lats = [q[1] for q in pts]
    km_w = (max(lons) - min(lons)) * 111.32 * math.cos(math.radians(lat))
    print(f"{a.island}: {len(pts)-1} points   (silhouette only — {chart['name']} "
          f"has no landmarks yet)")
    print(f"  centre     {lon}, {lat}   (given)")
    print(f"  extent     {km_w:.0f} x {a.height_km:.0f} km   (height given)")
    feat = {"type": "Feature",
            "properties": {"id": a.island, "traced_from": chart["name"],
                           "source_url": chart.get("source_url", ""),
                           "georeference": None,
                           "scale_source": "height set by hand; chart not yet georeferenced",
                           "centre": [lon, lat],
                           "size_km": [round(km_w), round(a.height_km)]},
            "geometry": {"type": "Polygon", "coordinates": [pts]}}
    if a.dry_run:
        print("\n(dry run — nothing written)"); return
    os.makedirs(OUTDIR, exist_ok=True)
    dest = os.path.join(OUTDIR, f"{a.island}.geojson")
    json.dump(feat, open(dest, "w", encoding="utf-8"), indent=1)
    print(f"  -> {os.path.relpath(dest, ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("island")
    ap.add_argument("--chart", required=True, help="scripts/charts/<name>.json")
    ap.add_argument("--image", required=True, help="local copy of the chart raster")
    ap.add_argument("--mode", default="red", choices=("red", "blue", "green", "dark"))
    ap.add_argument("--threshold", type=float, default=45.0)
    ap.add_argument("--closing", type=int, default=21)
    ap.add_argument("--open", type=int, default=0, dest="open_r",
                    help="opening radius, applied before anything else")
    ap.add_argument("--upsample", type=int, default=1,
                    help="resample the crop before thresholding. A mark only "
                         "20 px across quantises into axis-aligned steps; "
                         "resampling lets the boundary follow the underlying "
                         "grey values instead of pixel corners.")
    ap.add_argument("--smooth", type=float, default=0.0,
                    help="gaussian blur before thresholding, in upsampled px")
    ap.add_argument("--bright", action="store_true",
                    help="the island is the *pale* shape — engravers often "
                         "leave a small island blank and hachure the shoal "
                         "around it")
    ap.add_argument("--se", default="disk", choices=("disk", "square"),
                    help="structuring element; square preserves right angles")
    ap.add_argument("--height-km", type=float,
                    help="north-south extent in km. Use when the chart has no "
                         "landmarks yet, so scale is set by hand rather than "
                         "georeferenced.")
    ap.add_argument("--blank-rows", dest="blank",
                    help="y0,y1 band of the source to paint out before "
                         "thresholding — use for a neatline the coast runs "
                         "close enough to that closing would bridge them")
    ap.add_argument("--despeckle", type=int, default=0,
                    help="drop opening-residue blobs under N px: survey "
                         "stations drawn on the coast, not headlands")
    ap.add_argument("--tolerance", type=float, default=2.0, help="simplify, px")
    ap.add_argument("--bbox", help="x0,y0,x1,y1 to restrict the search")
    ap.add_argument("--centre", help="lon,lat override. The chart still gives "
                    "shape, size and orientation; use this where its own "
                    "georeference is not trustworthy — typically the imagined "
                    "ocean west of everything it actually surveyed.")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    a.blank = [int(v) for v in a.blank.split(",")] if a.blank else None

    chart = json.load(open(os.path.join(CHARTS, a.chart + ".json"), encoding="utf-8"))
    lms = chart["landmarks"]
    if not lms:
        return manual(a, chart)
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
    mask, (ox, oy) = island_mask(Image.open(os.path.expanduser(a.image)), a.mode,
                                 a.threshold, bbox, a.closing, a.se, a.open_r,
                          a.upsample, a.smooth, a.bright, a.blank, a.despeckle)
    ring = approximate_polygon(max(find_contours(mask.astype(float), 0.5), key=len),
                               a.tolerance)
    if len(ring) > 3 and (ring[0] == ring[-1]).all():
        ring = ring[:-1]

    pts = [[round(v, 4) for v in to_lonlat(p, K, c + ox, r + oy)] for r, c in ring]
    # d3-geo reads polygons spherically: wound the wrong way, the island renders
    # as the whole planet except itself.
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] -
               pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    if area > 0:
        pts = pts[::-1]
    pts.append(pts[0])

    ys, xs = np.nonzero(mask)
    clon, clat = to_lonlat(p, K, (xs.min() + xs.max()) / 2 + ox,
                           (ys.min() + ys.max()) / 2 + oy)
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
