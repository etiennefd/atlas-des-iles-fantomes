#!/usr/bin/env python3
"""The Great Lakes, so the islands Bellin put in Lake Superior sit in water.

world-atlas's land-50m has no lakes: Superior is solid land on the globe. The
five Great Lakes from Natural Earth's 50m lakes, with their islands as holes,
are written to public/data/lakes.geojson, and map.ts cuts them out of the land
through the same <mask> that erases California and Korea, so no new layer is
drawn. 1,743 points against land-50m's 60,635.

    curl -sLo ~/scratch/ne_50m_lakes.geojson \
      https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_lakes.geojson
    python3 scripts/build_lakes.py ~/scratch/ne_50m_lakes.geojson

The source is not committed, like the chart rasters; the URL reproduces it.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "public", "data", "lakes.geojson")
KEEP = ["Lake Superior", "Lake Michigan", "Lake Huron", "Lake Erie", "Lake Ontario"]


def rnd(g):
    # 0.001 deg is ~100 m, a fortieth of a pixel at full zoom
    if isinstance(g[0], (int, float)):
        return [round(g[0], 3), round(g[1], 3)]
    return [rnd(x) for x in g]


src = json.load(open(sys.argv[1], encoding="utf-8"))
feats = [{"type": "Feature", "properties": {"name": f["properties"]["name"]},
          "geometry": {"type": f["geometry"]["type"],
                       "coordinates": rnd(f["geometry"]["coordinates"])}}
         for f in src["features"] if f["properties"].get("name") in KEEP]
missing = set(KEEP) - {f["properties"]["name"] for f in feats}
if missing:
    raise SystemExit(f"not found: {', '.join(sorted(missing))}")
with open(OUT, "w", encoding="utf-8") as f:
    json.dump({"type": "FeatureCollection", "features": feats}, f, separators=(",", ":"))
print(f"{len(feats)} lakes -> {os.path.relpath(OUT)} ({os.path.getsize(OUT) // 1024} kB)")
