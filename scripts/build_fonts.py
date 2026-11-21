#!/usr/bin/env python3
"""
Build the site's web fonts: Piazzolla, roman and italic, self-hosted.

    python3 scripts/build_fonts.py

Why not Google Fonts' CSS API: it strips small caps (smcp, c2sc) and old-style
figures (onum) from everything it serves, and the site uses both. The full
files from the google/fonts repository keep them. They are fetched into
~/scratch/fonts (not committed, like the chart rasters: 2.7 MB of pure input
that the URL reproduces), then cut down to what the site sets:

- weights up to 700 (the default master, 100, cannot be moved, so the range
  is 100-700 rather than 400-700); the optical-size axis is kept whole;
- Latin, Latin Extended and punctuation. No Cyrillic: the one or two places
  it occurs (Ernest-Legouvé) fall back to Georgia, by Étienne's choice;
- every OpenType feature kept.

The OFL requires the licence to travel with the font, so it is copied too.
"""
import os, urllib.parse, urllib.request
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "public", "fonts")
CACHE = os.path.expanduser("~/scratch/fonts")
REPO = "https://github.com/google/fonts/raw/main/ofl/piazzolla/"
FILES = {
    "normal": "Piazzolla[opsz,wght].ttf",
    "italic": "Piazzolla-Italic[opsz,wght].ttf",
}
LATIN = ("U+0000-024F,U+0259,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0300-0301,"
         "U+1E00-1EFF,U+2000-206F,U+20AC,U+2122,U+2190-2193,U+2212")
MAX_WGHT = 700


def fetch(name):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        urllib.request.urlretrieve(REPO + urllib.parse.quote(name), path)
    return path


def main():
    os.makedirs(OUT, exist_ok=True)
    for style, name in FILES.items():
        font = TTFont(fetch(name))
        w = next(a for a in font["fvar"].axes if a.axisTag == "wght")
        font = instancer.instantiateVariableFont(
            font, {"wght": (w.minValue, min(MAX_WGHT, w.maxValue))})

        opts = subset.Options()
        opts.layout_features = ["*"]
        opts.flavor = "woff2"
        opts.name_IDs = ["*"]
        opts.notdef_outline = True
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=subset.parse_unicodes(LATIN))
        sub.subset(font)
        dest = os.path.join(OUT, f"piazzolla-{style}.woff2")
        subset.save_font(font, dest, opts)

        feats = {r.FeatureTag for r in font["GSUB"].table.FeatureList.FeatureRecord}
        assert {"smcp", "onum"} <= feats, f"{style}: lost small caps or figures"
        print(f"{os.path.relpath(dest)}  {os.path.getsize(dest) // 1024} kB")

    lic = os.path.join(OUT, "OFL.txt")
    with open(fetch("OFL.txt"), "rb") as src, open(lic, "wb") as dst:
        dst.write(src.read())
    print(os.path.relpath(lic))


if __name__ == "__main__":
    main()
