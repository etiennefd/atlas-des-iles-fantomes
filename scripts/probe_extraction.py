#!/usr/bin/env python3
"""
Which extraction mode and threshold will pull this island off this chart?

Answers by measurement what has otherwise been answered by sampling pixels
by hand on every chart so far — and catches the one failure that does not
announce itself.

    python3 scripts/probe_extraction.py --image ~/scratch/charts/x.jpg \\
        --bbox 980,100,1800,740

Frame the bbox so the island fills the middle and open water or parchment
runs round the edge: the probe treats the central fifth as island and the
border as background, and reports how far apart each mode drives them.

THE FRAGMENTATION WARNING IS THE POINT. A rhumb line or a graticule drawn
across an island depresses the score along its path; the mask splits, the
largest-component step in trace_outline drops the smaller piece, and the
island comes back truncated with a straight chord where the line crossed —
which reads perfectly well as a coastline. It has happened on two charts.
Whenever the largest part holds less than ~98% of the mask, the number to
reach for is *more smoothing*, not a tighter threshold, and the complete
island is the LARGER mask.
"""
import argparse, math

import numpy as np
from PIL import Image
from scipy.ndimage import binary_fill_holes, gaussian_filter
from skimage.measure import label, regionprops

Image.MAX_IMAGE_PIXELS = None

MODES = {
    "red":     lambda R, G, B: R - (G + B) / 2,
    "blue":    lambda R, G, B: B - (R + G) / 2,
    "green":   lambda R, G, B: G - (R + B) / 2,
    "magenta": lambda R, G, B: (R + B) / 2 - G,
    "dark":    lambda R, G, B: 255 - (R + G + B) / 3,
}


def scores(img, bbox):
    a = np.asarray(img.crop(tuple(bbox)).convert("RGB")).astype(float)
    return {n: f(a[:, :, 0], a[:, :, 1], a[:, :, 2]) for n, f in MODES.items()}


def separation(s):
    """d-prime between the middle of the frame and its border."""
    h, w = s.shape
    core = s[int(h * .4):int(h * .6), int(w * .4):int(w * .6)].ravel()
    edge = np.concatenate([s[:int(h * .06)].ravel(), s[-int(h * .06):].ravel(),
                           s[:, :int(w * .06)].ravel(), s[:, -int(w * .06):].ravel()])
    sd = math.sqrt((core.std() ** 2 + edge.std() ** 2) / 2) or 1e-9
    return (core.mean() - edge.mean()) / sd, core.mean(), edge.mean()


def measure(s, thr, bright, sigma):
    v = gaussian_filter(s, sigma) if sigma else s
    m = (v < thr) if bright else (v > thr)
    if not m.any() or m.all():
        return None
    lab = label(m)
    rp = regionprops(lab)
    big = max(rp, key=lambda q: q.area)
    held = big.area / m.sum()
    mm = binary_fill_holes(lab == big.label)
    ys, xs = np.nonzero(mm)
    return dict(w=xs.max() - xs.min() + 1, h=ys.max() - ys.min() + 1,
                area=int(mm.sum()), parts=len(rp), held=held)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--bbox", required=True, help="x0,y0,x1,y1 framing the island")
    ap.add_argument("--mode", help="probe only this mode")
    ap.add_argument("--sigma", type=float, default=None,
                    help="smoothing for the sweep (default: try several)")
    a = ap.parse_args()
    bbox = [int(v) for v in a.bbox.split(",")]
    import os
    img = Image.open(os.path.expanduser(a.image))
    sc = scores(img, bbox)

    print("separation between the middle of the frame and its border:\n")
    print(f"  {'mode':10}{'d-prime':>9}{'island':>9}{'border':>9}   use")
    ranked = []
    for n, s in sc.items():
        d, ci, ce = separation(s)
        ranked.append((abs(d), n, d))
        flag = "--mode %s%s" % (n, " --bright" if d < 0 else "")
        print(f"  {n:10}{d:9.1f}{ci:9.1f}{ce:9.1f}   {flag}")
    ranked.sort(reverse=True)
    best = a.mode or ranked[0][1]
    bright = next(d for _, n, d in ranked if n == best) < 0
    print(f"\nsweeping {best}{' --bright' if bright else ''}:\n")

    s = sc[best]
    lo, hi = np.percentile(s, 2), np.percentile(s, 98)
    thrs = [round(lo + (hi - lo) * k / 10, 1) for k in range(1, 10)]
    sigmas = [a.sigma] if a.sigma is not None else [0, 3, 8, 16]
    print(f"  {'sigma':>6}{'thr':>9}{'extent':>13}{'area':>10}{'parts':>7}{'largest':>9}  note")
    rows = {}
    for sg in sigmas:
        for t in thrs:
            r = measure(s, t, bright, sg)
            if not r:
                continue
            rows.setdefault(sg, []).append((t, r))
            note = ""
            if r["held"] < 0.98:
                note = "SPLIT — a line may be cutting the island; smooth more"
            print(f"  {sg:6}{t:9.1f}{r['w']:7}x{r['h']:<5}{r['area']:10}{r['parts']:7}"
                  f"{100*r['held']:8.1f}%  {note}")
        print()
    # plateau: where does the extent stop moving?
    print("plateaux (extent stable within 1% across neighbouring thresholds):")
    found = False
    for sg, rs in rows.items():
        for i in range(1, len(rs) - 1):
            a0, b0, c0 = rs[i - 1][1], rs[i][1], rs[i + 1][1]
            if all(abs(x["w"] - b0["w"]) <= max(2, .01 * b0["w"]) and
                   abs(x["h"] - b0["h"]) <= max(2, .01 * b0["h"]) for x in (a0, c0)) \
               and b0["held"] >= 0.98:
                print(f"  sigma {sg}, threshold {rs[i][0]}  ->  {b0['w']}x{b0['h']}")
                found = True
    if not found:
        print("  none — widen the sweep, or smooth harder if the masks are SPLIT")


if __name__ == "__main__":
    main()
