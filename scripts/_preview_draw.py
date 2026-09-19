#!/usr/bin/env python3
"""Render the scene preview_island.mjs projects. Not called directly."""
import json, sys
from PIL import Image, ImageDraw, ImageFont

scene = json.load(open(sys.argv[1]))
W, H = scene["W"], scene["H"]
WATER, LAND, PH = (237, 239, 240), (56, 61, 64), (116, 32, 47)
RULE, INK, GHOST, HITC = (199, 204, 207), (22, 25, 27), (196, 168, 174), (214, 92, 60)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Georgia.ttf", 21)
except OSError:
    font = ImageFont.load_default()

tiles = []
for v in scene["views"]:
    im = Image.new("RGB", (W, H), WATER)
    dr = ImageDraw.Draw(im)
    for r in v["sphere"]:
        if len(r) > 2:
            dr.polygon([tuple(p) for p in r], fill=WATER, outline=RULE)
    for r in v["land"]:
        if len(r) > 2:
            dr.polygon([tuple(p) for p in r], fill=LAND)
    for r in v["others"]:
        if len(r) > 2:
            dr.line([tuple(p) for p in r] + [tuple(r[0])], fill=GHOST, width=2)
    # land overlap ALWAYS drawn: an outline over a dark fill hides it otherwise
    for q in v["hits"]:
        dr.ellipse([q[0] - 2.4, q[1] - 2.4, q[0] + 2.4, q[1] + 2.4], fill=HITC)
    for r in v["island"]:
        if len(r) > 2:
            dr.line([tuple(p) for p in r] + [tuple(r[0])], fill=PH, width=4)
    im.paste(Image.new("RGB", (W, 36), "white"), (0, 0))
    ImageDraw.Draw(im).text((12, 8), v["label"], fill=INK, font=font)
    tiles.append(im)

cols = 1 if len(tiles) == 1 else 2
rows = (len(tiles) + cols - 1) // cols
out = Image.new("RGB", (cols * (W + 12), rows * (H + 12)), "white")
for i, t in enumerate(tiles):
    out.paste(t, ((i % cols) * (W + 12), (i // cols) * (H + 12)))
k = min(1.0, 900 / out.size[0])
out = out.resize((int(out.size[0] * k), int(out.size[1] * k)), Image.Resampling.LANCZOS)
out.save(scene["out"])
print(scene["out"], out.size)
