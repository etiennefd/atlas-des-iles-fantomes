#!/usr/bin/env python3
"""Shapes for islands nobody drew, built from what their reporters wrote.

For five phantoms no depiction with a coastline was found (November 2026):
every chart draws a dot or a ring, and the reports are text. What the text
gives — a length, a bearing, a high end and a low end, "a group", "three low
islands within one reef" — is laid out here as geometry, so the island at
least has the size and the build its reporter described instead of a 250 km
blob. Everything past those few facts is invented, and each outline file
says which is which.

    python3 scripts/describe_island.py dougherty emerald nimrod tuanaki rupes-nigra
    npm run geo

Writes src/data/outlines/{id}.geojson, which build_geojson.py then prefers
over a blob, like any traced outline. Deterministic: the same spec gives the
same shape. Jacquet is not here — half a mile long, it is drawn as a reef.
"""
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUTLINES = os.path.join(HERE, "..", "src", "data", "outlines")
ISLANDS = os.path.join(HERE, "..", "src", "content", "islands")

NM = 1.852  # the reports are in sea miles

# Each island is a list of parts in a local km plane about its `coords`:
# `at` is the part's centre (east, north), `bearing` the compass direction of
# its long axis, `head` how much wider the end the bearing points to is than
# the other (a bluff against low land), `wobble` the coastline's irregularity.
SPECS = {
    "dougherty": {
        "traced_from": "Capt. Daniel Dougherty's report, 1841: no drawing exists",
        "source_url": "https://archive.org/details/the-nautical-magazine-1841",
        "scale_source": (
            "Dougherty: 'five or six miles in length, running N.E. and S.W., "
            "with a high round bluff on the N.E. end, with low land to the "
            "S.W.' (Nautical Magazine 1841, p. 783). 5.5 nm long on a NE-SW "
            "axis, its NE end the wider; the width (4 km) and the coastline "
            "are invented"
        ),
        "parts": [dict(at=(0, 0), length=5.5 * NM, width=4.0, bearing=45,
                       head=0.45, wobble=0.10, seed="dougherty")],
    },
    "emerald": {
        "traced_from": "Capt. C. J. Nockells' report, 1821: no drawing exists",
        "source_url": "https://archive.org/details/adirectoryforna00findgoog",
        "scale_source": (
            "Nockells, seen from 25 miles and never approached: 'very high, "
            "with peaked mountains ... Direction, N.E. and S.W., about 30 "
            "miles' (quoted in Findlay, Directory for the Pacific, 1851, "
            "p. 678). 30 nm on a NE-SW axis; the width (24 km) and the "
            "coastline are invented"
        ),
        "parts": [dict(at=(0, 0), length=30 * NM, width=24.0, bearing=45,
                       head=0.0, wobble=0.14, seed="emerald")],
    },
    "nimrod": {
        "traced_from": "Capt. Henry Eilbeck's report, 1828: no drawing exists",
        "source_url": "https://archive.org/details/adirectoryforna00findgoog",
        "scale_source": (
            "Eilbeck: 'a group of islands', which 'appear to have been seen "
            "at a considerable distance' (Findlay 1851, p. 678). No size and "
            "no count anywhere: four islets of 3-6 km over ~25 km are "
            "invented"
        ),
        "parts": [
            dict(at=(-9.0, 3.5), length=6.0, width=4.0, bearing=70,
                 head=0.2, wobble=0.12, seed="nimrod-1"),
            dict(at=(-1.5, -3.0), length=4.0, width=3.0, bearing=20,
                 head=0.0, wobble=0.12, seed="nimrod-2"),
            dict(at=(6.0, 2.0), length=5.0, width=3.5, bearing=110,
                 head=0.3, wobble=0.12, seed="nimrod-3"),
            dict(at=(11.0, -5.5), length=3.0, width=2.5, bearing=40,
                 head=0.0, wobble=0.10, seed="nimrod-4"),
        ],
    },
    "tuanaki": {
        "traced_from": "the Cook Islands accounts of the 1840s: no drawing exists",
        "source_url": "https://archive.org/details/gemsfromcoralis01gillgoog",
        "scale_source": (
            "Gill, Gems from the Coral Islands (1856), ii, p. 73: 'three low "
            "islands within one reef'; Soma, who said he landed c. 1842, "
            "describes his captain looking for the entrance (ava), i.e. a "
            "passage into a lagoon (JPS 20, 1911, p. 144). An atoll, then: a "
            "reef ring with a passage and three islets on it. No size is "
            "reported: 60 km across is a choice, made so the ring and its "
            "islets read at full zoom, the size of a reef's rock cluster. At "
            "25 km, Penrhyn's size, it was a 6 px ring at 8x"
        ),
        "atoll": dict(diameter=60.0, aspect=0.78, bearing=60, rim=0.07,
                      islets=[(20, 0.16, 38), (150, 0.13, 30), (255, 0.18, 44)],
                      gap=(95, 22), wobble=0.05, seed="tuanaki"),
    },    "rupes-nigra": {
        "traced_from": "Mercator's account, after Jacob Cnoyen: drawn only in profile",
        "source_url": "https://commons.wikimedia.org/wiki/File:Septentrionalium_terrarum_descriptio_-_per_Gerardum_Mercatorem_-_btv1b8591959t_(1_of_2).jpg",
        "scale_source": (
            "Mercator's legend on the Septentrionalium terrarum descriptio "
            "(1595): 'Rupes quae sub polo est ambitum circiter 33 leucarum "
            "habet', the rock under the pole is about 33 leagues round; his "
            "1577 letter to John Dee, copying Cnoyen, gives 'almost 33 French "
            "miles' and 'a bare Rock in the midst of the Sea'. 33 leagues of "
            "4.45 km is 147 km round, so 46.7 km across, centred on the pole. "
            "The roundness and the coastline are invented: every map draws "
            "the rock as a cliff seen from the side"
        ),
        "parts": [dict(at=(0, 0), length=46.7, width=46.7, bearing=0,
                       head=0.0, wobble=0.08, seed="rupes-nigra")],
    },
}


def rnd(seed):
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return [(h >> (8 * i)) % 256 / 256 for i in range(12)]


def wobble(a, r, amp):
    # blob()'s three harmonics, scaled down: a coast, not a potato
    return 1 + amp * (math.sin(2 * a + 6.3 * r[0]) * 0.9
                      + math.sin(3 * a + 6.3 * r[1]) * 0.6
                      + math.sin(5 * a + 6.3 * r[2]) * 0.35)


def axes(bearing):
    t = math.radians(bearing)
    return (math.sin(t), math.cos(t)), (math.cos(t), -math.sin(t))


def islet(p, n=36):
    r = rnd(p["seed"])
    u, v = axes(p["bearing"])
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        w = wobble(a, r, p["wobble"])
        x = p["length"] / 2 * math.cos(a) * w
        y = p["width"] / 2 * math.sin(a) * w * (1 + p["head"] * math.cos(a))
        pts.append((p["at"][0] + u[0] * x + v[0] * y,
                    p["at"][1] + u[1] * x + v[1] * y))
    return pts


def atoll(s, n=160):
    """A reef ring with a gap for the passage, its rim swelling inward where
    the islets stand: the outer edge stays smooth, as an atoll's seaward reef
    does, and the land lies on the lagoon side of it."""
    r = rnd(s["seed"])
    u, v = axes(s["bearing"])
    R = s["diameter"] / 2
    g0, gw = s["gap"]
    start, span = g0 + gw / 2, 360 - gw
    outer, inner = [], []
    for i in range(n + 1):
        deg = start + span * i / n
        a = math.radians(deg)
        ro = R * wobble(a, r, s["wobble"])
        rim = s["rim"]
        for c, wid, ext in s["islets"]:
            d = (deg - c + 180) % 360 - 180
            if abs(d) < ext / 2:
                rim = max(rim, wid * math.cos(math.pi * d / ext) ** 2 + s["rim"] * 0.5)
        ri = ro - rim * s["diameter"]
        for rad, out in ((ro, outer), (ri, inner)):
            x, y = rad * math.cos(a), rad * math.sin(a) * s["aspect"]
            out.append((u[0] * x + v[0] * y, u[1] * x + v[1] * y))
    return outer + inner[::-1]


def polar_lonlat(pts, lat0):
    """At a pole the local plane cannot be scaled by cos(latitude): it is laid
    out azimuthally instead, distance from the pole along a meridian. Up the
    plane is the 180th meridian and right is 90 E at the north pole, as on
    Mercator's polar sheet. The ring encloses the pole, so its winding is set
    by longitude rather than by planar area: clockwise seen from the outside
    of the sphere is westward round the north pole."""
    north = lat0 > 0
    ring = []
    for x, y in pts:
        d = math.hypot(x, y) / 111.32
        lon = math.degrees(math.atan2(x, -y if north else y))
        ring.append([round(lon, 5), round(lat0 - d if north else lat0 + d, 5)])
    # unwrap, then wind so longitude falls round the north pole (rises round
    # the south), and close
    turn = 0.0
    for a, b in zip(ring, ring[1:] + ring[:1]):
        turn += (b[0] - a[0] + 180) % 360 - 180
    if (turn > 0) == north:
        ring = ring[::-1]
    return [ring + [ring[0]]]


def to_lonlat(pts, lon0, lat0):
    if abs(lat0) > 89.5:
        return polar_lonlat(pts, lat0)
    k = 1 / (111.32 * math.cos(math.radians(lat0)))
    ring = [[round(lon0 + x * k, 5), round(lat0 + y / 111.32, 5)] for x, y in pts]
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1]))
    if area > 0:  # d3-geo wants clockwise; see Traps in CLAUDE.md
        ring = ring[::-1]
    return [ring + [ring[0]]]


def coords_of(iid):
    for line in open(os.path.join(ISLANDS, iid + ".yaml"), encoding="utf-8"):
        if line.startswith("coords:"):
            return [float(x) for x in line.split(":", 1)[1].strip(" []\n").split(",")]
    raise SystemExit(f"{iid}: no coords")


def build(iid):
    s = SPECS[iid]
    lon, lat = coords_of(iid)
    rings = [atoll(s["atoll"])] if "atoll" in s else [islet(p) for p in s["parts"]]
    polys = [to_lonlat(r, lon, lat) for r in rings]
    geom = ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
            else {"type": "MultiPolygon", "coordinates": polys})
    xs = [x for r in rings for x, _ in r]; ys = [y for r in rings for _, y in r]
    props = {
        "id": iid,
        "traced_from": s["traced_from"],
        "source_url": s["source_url"],
        "georeference": None,
        "scale_source": s["scale_source"],
        "described": True,
        "liberties": ["the coastline: no depiction with one exists"],
        "centre": [lon, lat],
        "extent_km": [round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1)],
    }
    if len(polys) > 1:
        props["parts"] = len(polys)
    out = os.path.join(OUTLINES, iid + ".geojson")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"type": "Feature", "properties": props, "geometry": geom}, f, indent=1)
    print(f"{iid}: {len(polys)} part(s), {props['extent_km'][0]} x "
          f"{props['extent_km'][1]} km E-W x N-S -> {os.path.relpath(out)}")


if __name__ == "__main__":
    for iid in sys.argv[1:] or SPECS:
        build(iid)
