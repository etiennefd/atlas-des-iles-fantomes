#!/usr/bin/env python3
"""Lift one polygon out of a GMT binned GSHHS file and write it as an outline.

For islands whose most influential depiction is a digital coastline rather
than a chart: Sandy Island lived longest as a polygon in the World Vector
Shoreline and the GSHHS coastline derived from it, until it was deleted in 2012.

    python3 -I scripts/extract_gshhs.py ile-de-sable \\
        --cdf ~/scratch/gshhs/gmt-gshhs-2.2.0/share/coast/binned_GSHHS_f.cdf \\
        --bbox 159.8,-19.5,160.1,-19.0 --chart gshhs-2.2.0

The binned format (GMT 4): 1-degree bins, row-major from the north pole;
each bin holds segments, each segment its points as 16-bit offsets from the
bin's south-west corner (65535 = one bin width). A polygon lying wholly
inside one bin is a single closed segment, which is all this handles: it
refuses anything that crosses a bin edge rather than stitching it.

The geometry is written untouched: no smoothing, no scaling, no turn.
`size_km` is deliberately not set, so build_geojson leaves the size alone.
"""

import argparse
import json
import math
from pathlib import Path

from scipy.io import netcdf_file

ROOT = Path(__file__).resolve().parent.parent


def polygons_in(cdf, bbox):
    lon0, lat0, lon1, lat1 = bbox
    f = netcdf_file(cdf, "r", mmap=False)
    v = f.variables
    bin_size = int(round(f.bin_size)) if hasattr(f, "bin_size") else 60
    deg = bin_size / 60.0
    nx = int(round(360 / deg))
    first_seg = v["Id_of_first_segment_in_a_bin"].data
    n_seg = v["N_segments_in_a_bin"].data
    enc = v["Embedded_npts_levels_exit_entry_for_a_segment"].data
    first_pt = v["Id_of_first_point_in_a_segment"].data
    gid = v["Id_of_GSHHS_ID"].data
    dx = v["Relative_longitude_from_SW_corner_of_bin"].data
    dy = v["Relative_latitude_from_SW_corner_of_bin"].data

    out = []
    for row in range(int((90 - lat1) // deg), int(math.ceil((90 - lat0) / deg))):
        for col in range(int(lon0 // deg), int(math.ceil(lon1 / deg))):
            b = row * nx + col
            sw_lon, sw_lat = col * deg, 90 - (row + 1) * deg
            for s in range(first_seg[b], first_seg[b] + n_seg[b]):
                e = int(enc[s])
                npts, level = e >> 9, (e >> 6) & 7
                exit_, entry = (e >> 3) & 7, e & 7
                p = int(first_pt[s])
                pts = [
                    (sw_lon + (int(dx[i]) & 0xFFFF) / 65535 * deg,
                     sw_lat + (int(dy[i]) & 0xFFFF) / 65535 * deg)
                    for i in range(p, p + npts)
                ]
                if not all(lon0 <= x <= lon1 and lat0 <= y <= lat1 for x, y in pts):
                    continue
                if exit_ != 4 or entry != 4:
                    raise SystemExit(f"segment {s} crosses a bin edge; not handled")
                out.append({"gshhs_id": int(gid[s]), "level": level, "pts": pts})
    f.close()
    return out


def extent_km(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    lat = math.radians((min(ys) + max(ys)) / 2)
    return (round((max(xs) - min(xs)) * 111.32 * math.cos(lat), 1),
            round((max(ys) - min(ys)) * 110.57, 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--cdf", required=True)
    ap.add_argument("--bbox", required=True, help="lon0,lat0,lon1,lat1")
    ap.add_argument("--chart", required=True, help="scripts/charts/{chart}.json")
    a = ap.parse_args()

    chart = json.loads((ROOT / "scripts/charts" / f"{a.chart}.json").read_text())
    polys = polygons_in(Path(a.cdf).expanduser(), [float(x) for x in a.bbox.split(",")])
    if len(polys) != 1:
        raise SystemExit(f"{len(polys)} polygons in the bbox; want exactly one")
    poly = polys[0]
    if poly["level"] != 1:
        raise SystemExit(f"level {poly['level']} is not land")

    ring = [[round(x, 5), round(y, 5)] for x, y in poly["pts"]]
    if ring[0] == ring[-1]:
        ring.pop()
    # GSHHS winds land counterclockwise; d3-geo reads that as the whole planet
    # except the island, and build_geojson trusts an outline file's winding.
    if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1])) > 0:
        ring.reverse()
    ring.append(ring[0])
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    centre = [round((min(xs) + max(xs)) / 2, 3), round((min(ys) + max(ys)) / 2, 3)]
    ext = extent_km(ring)

    feature = {
        "type": "Feature",
        "properties": {
            "id": a.id,
            "traced_from": chart["name"],
            "source_url": chart["source_url"],
            "georeference": "none needed: the source is already in longitude and latitude",
            "scale_source": "the polygon as distributed, unscaled",
            "gshhs_id": poly["gshhs_id"],
            "vertices": len(ring) - 1,
            "centre": centre,
            "extent_km": list(ext),
            "liberties": [],
        },
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }
    dest = ROOT / "src/data/outlines" / f"{a.id}.geojson"
    dest.write_text(json.dumps(feature, indent=1, ensure_ascii=False) + "\n")
    print(f"{dest.relative_to(ROOT)}: GSHHS id {poly['gshhs_id']}, "
          f"{len(ring) - 1} vertices, {ext[0]} x {ext[1]} km, centre {centre}")


if __name__ == "__main__":
    main()
