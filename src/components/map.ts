import {
  geoPath,
  geoCentroid,
  geoBounds,
  geoDistance,
  geoOrthographic,
  type GeoProjection,
} from "d3-geo";
import { select } from "d3-selection";
import { zoom as d3zoom, zoomIdentity, type D3ZoomEvent } from "d3-zoom";
import { Delaunay } from "d3-delaunay";
import { feature } from "topojson-client";

type State = "available" | "translated" | "planned";

export type IslandMeta = {
  id: string;
  name: string;
  state: State;
  href?: string;
  lifespan: string;
  forthcoming: string;
};

type Cfg = {
  root: HTMLElement;
  meta: IslandMeta[];
  landUrl: string;
  islandsUrl: string;
};

// Screen-space radius below which an island gets a halo ring.
const HALO_THRESHOLD = 14;
const HALO_MIN = 7;
const MAX_ZOOM = 8;

// Basemap detail. Natural Earth 110m has no small islands at all — no
// Balearics, no Lesser Antilles, no Azores — which is a poor look on an atlas
// about islands. But the globe reprojects every path every frame, and detail
// is ruinous at that rate: measured 3 ms/frame for 110m, 32 ms for 50m and
// 265 ms for 10m. Culling to the visible hemisphere doesn't rescue it, because
// the few visible polygons include whole continents.
//
// So: coarse while the globe is moving, fine the moment it stops. You only
// need to *see* small islands when you've stopped to look at them. The 10m
// tier is additionally gated behind a close zoom, so a casual visitor never
// downloads 800 kB for it.
const DETAIL_TIERS = [
  { url: "/data/land-50m.json", minZoom: 0 },
  { url: "/data/land-10m.json", minZoom: 3 },
];
const IDLE_MS = 180;
// Where the globe opens and returns to. Dragging rotates it, so there is no
// edge to reach in any direction and the poles are reachable — which a
// flattened projection fitted to a latitude band could never offer.
const HOME_LON = 0;
const HOME_LAT = 0;

const wrap180 = (d: number) => ((((d + 180) % 360) + 360) % 360) - 180;

const SVG_NS = "http://www.w3.org/2000/svg";
const el = (n: string, attrs: Record<string, string> = {}) => {
  const e = document.createElementNS(SVG_NS, n);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
};

export async function mount(cfg: Cfg) {
  const { root, meta } = cfg;
  const byId = new Map(meta.map((m) => [m.id, m]));

  const [landTopo, islands] = await Promise.all([
    fetch(cfg.landUrl).then((r) => r.json()),
    fetch(cfg.islandsUrl).then((r) => r.json()),
  ]);
  const land = feature(landTopo, landTopo.objects.land);

  // Keep only islands we have metadata for, and sort so planned ones sit
  // underneath — a faint ring should never occlude a written island.
  const order: Record<State, number> = { planned: 0, translated: 1, available: 2 };
  const feats = islands.features
    .filter((f: any) => byId.has(f.properties.id))
    .sort(
      (a: any, b: any) =>
        order[byId.get(a.properties.id)!.state] -
        order[byId.get(b.properties.id)!.state]
    );

  // --- scaffolding -------------------------------------------------------
  root.classList.add("pmap");
  const svg = el("svg", { class: "pmap__svg", role: "img" });
  svg.setAttribute("aria-label", root.dataset.label ?? "Carte");
  const gRoot = el("g");
  const gLand = el("g", { class: "pmap__land" });
  const gIslands = el("g", { class: "pmap__islands" });
  const gHalos = el("g", { class: "pmap__halos" });
  gRoot.append(gLand, gHalos, gIslands);
  svg.append(gRoot);

  const labels = document.createElement("div");
  labels.className = "pmap__labels";
  labels.setAttribute("aria-hidden", "true");

  const reset = document.createElement("button");
  reset.type = "button";
  reset.className = "pmap__reset";
  reset.textContent = root.dataset.resetLabel ?? "↺";
  reset.title = root.dataset.resetTitle ?? "Reset";
  reset.hidden = true;

  root.append(svg, labels, reset);

  // --- projection --------------------------------------------------------
  let W = 0,
    H = 0,
    k = 1;
  // Position is rotation, not translation: dragging turns the globe. `lastTx`
  // and `lastTy` exist only to turn d3-zoom's ever-growing x/y into
  // per-gesture deltas.
  let lambda = HOME_LON;
  let phi = -HOME_LAT;
  let lastTx = 0;
  let lastTy = 0;
  let offX = 0;
  let offY = 0;
  let suppressRotate = false;
  const clampPhi = (v: number) => Math.max(-89, Math.min(89, v));
  const projection: GeoProjection = geoOrthographic().clipAngle(90);
  const path = geoPath(projection);

  // The ocean is the disc itself, so it needs an edge — otherwise the land
  // floats on the page background with nothing to sit in.
  const spherePath = el("path", { class: "pmap__sphere" }) as SVGPathElement;
  gLand.before(spherePath);

  const landPath = el("path", { class: "pmap__landpath" });
  gLand.append(landPath);

  // One <path> per island so each can be hit-tested and styled individually.
  const shapes = new Map<string, SVGPathElement>();
  const halos = new Map<string, SVGCircleElement>();
  const chips = new Map<string, HTMLAnchorElement>();

  for (const f of feats) {
    const id = f.properties.id as string;
    const m = byId.get(id)!;

    const p = el("path", {
      class: `pmap__island is-${m.state} kind-${f.properties.kind}`,
      "data-id": id,
    }) as SVGPathElement;
    gIslands.append(p);
    shapes.set(id, p);

    const c = el("circle", {
      class: `pmap__halo is-${m.state}`,
      "data-id": id,
    }) as SVGCircleElement;
    gHalos.append(c);
    halos.set(id, c);

    const a = document.createElement("a");
    a.className = `pmap__label is-${m.state}`;
    if (m.href) a.href = m.href;
    a.innerHTML =
      `<span class="pmap__name">${m.name}</span>` +
      `<span class="pmap__span">${
        m.state === "planned" ? m.forthcoming : m.lifespan
      }</span>`;
    labels.append(a);
    chips.set(id, a);
  }

  // Spherical centroid and angular half-height per island. Both are
  // rotation-invariant, so deriving screen position and apparent size from
  // these keeps a shape's anchor put even when rotation splits it across the
  // antimeridian — path.centroid() and getBBox() both go haywire on a shape
  // cut into two pieces at opposite edges of the frame.
  const geoInfo = feats.map((f: any) => {
    const c = geoCentroid(f);
    const b = geoBounds(f);
    return {
      id: f.properties.id as string,
      lon: c[0],
      lat: c[1],
      halfLat: Math.max((b[1][1] - b[0][1]) / 2, 0),
    };
  });

  // Anchor point per island, in projected screen coords (pre-transform).
  const anchors: { id: string; x: number; y: number; sizePx: number }[] = [];

  function project() {
    for (const f of feats) {
      const id = f.properties.id as string;
      shapes.get(id)!.setAttribute("d", path(f as any) ?? "");
    }
    anchors.length = 0;
    // projection() still returns a point for the far side of the globe — it
    // mirrors it onto the near disc — so the hidden hemisphere has to be
    // culled explicitly, or you could hover an island through the earth.
    // Just under 90° to spare the jittery limb.
    const centre: [number, number] = [-lambda, -phi];
    for (const g of geoInfo) {
      if (geoDistance([g.lon, g.lat], centre) > Math.PI / 2 - 0.02) continue;
      const p = projection([g.lon, g.lat]);
      if (!p || !Number.isFinite(p[0])) continue;
      // Apparent size, measured north-south so it never crosses the seam.
      const e =
        g.halfLat > 0
          ? projection([g.lon, Math.min(g.lat + g.halfLat, 89)])
          : null;
      const sizePx = e ? 2 * Math.hypot(e[0] - p[0], e[1] - p[1]) : 0;
      anchors.push({ id: g.id, x: p[0], y: p[1], sizePx });
    }
  }

  let delaunay: Delaunay<number> | null = null;
  function rebuildVoronoi() {
    if (!anchors.length) return;
    // Delaunay in *transformed* screen space, so the cutoff stays honest
    // regardless of zoom level.
    const pts = new Float64Array(anchors.length * 2);
    anchors.forEach((a, i) => {
      pts[i * 2] = a.x * k + offX;
      pts[i * 2 + 1] = a.y * k + offY;
    });
    delaunay = new Delaunay(pts);
  }

  function resize() {
    const r = root.getBoundingClientRect();
    W = Math.max(320, r.width);
    H = Math.max(240, r.height);
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    projection.rotate([lambda, phi]);
    projection.fitExtent(
      [
        [8, 8],
        [W - 8, H - 8],
      ],
      { type: "Sphere" } as any
    );
    applyTransform();
  }

  // Screen position of a projected point is `p * k + off`. d3-zoom's own
  // translation never reaches the transform, so the scale needs its own
  // anchor or it grows away from the origin and the globe walks off to the
  // top left. Anchoring at the frame centre keeps the disc centred at every
  // zoom level.
  function setOffsets() {
    offX = (W / 2) * (1 - k);
    offY = (H / 2) * (1 - k);
  }

  // --- basemap detail ----------------------------------------------------
  type Tier = { polys: { p: any; c: [number, number]; r: number }[] };
  const tiers = new Map<string, Tier | "loading">();
  let idleTimer = 0;
  let showingDetail = false;

  function tierFor(zoom: number) {
    let pick: (typeof DETAIL_TIERS)[number] | null = null;
    for (const t of DETAIL_TIERS) if (zoom >= t.minZoom) pick = t;
    return pick;
  }

  // Split the land into individual polygons, each with a spherical centre and
  // radius, so the far hemisphere can be skipped when drawing.
  function prepare(geo: any): Tier {
    const rings: any[] = [];
    const push = (g: any) => {
      if (!g) return;
      if (g.type === "Polygon") rings.push(g.coordinates);
      else if (g.type === "MultiPolygon") g.coordinates.forEach((c: any) => rings.push(c));
    };
    if (geo.features) geo.features.forEach((f: any) => push(f.geometry));
    else push(geo.geometry ?? geo);
    return {
      polys: rings.map((coordinates) => {
        const p = { type: "Feature", geometry: { type: "Polygon", coordinates } };
        const b = geoBounds(p as any);
        return {
          p,
          c: [(b[0][0] + b[1][0]) / 2, (b[0][1] + b[1][1]) / 2] as [number, number],
          r: geoDistance(b[0], b[1]) / 2,
        };
      }),
    };
  }

  function detailD(tier: Tier) {
    const centre: [number, number] = [-lambda, -phi];
    let d = "";
    for (const m of tier.polys) {
      if (geoDistance(m.c, centre) - m.r > Math.PI / 2) continue;
      d += path(m.p as any) ?? "";
    }
    return d;
  }

  function drawDetail() {
    const want = tierFor(k);
    if (!want) return;
    const got = tiers.get(want.url);
    if (got === "loading") return;
    if (!got) {
      tiers.set(want.url, "loading");
      fetch(want.url)
        .then((r) => r.json())
        .then((topo) => {
          tiers.set(want.url, prepare(feature(topo, topo.objects.land)));
          drawDetail();
        })
        .catch(() => tiers.delete(want.url));
      return;
    }
    landPath.setAttribute("d", detailD(got));
    showingDetail = true;
  }

  // Any interaction drops straight back to the coarse basemap so the next
  // frame stays cheap, then redraws detail once things settle.
  function bumpIdle() {
    if (showingDetail) {
      showingDetail = false;
      landPath.setAttribute("d", path(land as any) ?? "");
    }
    clearTimeout(idleTimer);
    idleTimer = window.setTimeout(drawDetail, IDLE_MS);
  }

  function applyTransform() {
    // Rotation changes the geometry itself, so every path is regenerated —
    // there is no transform shortcut for a change of central meridian.
    projection.rotate([lambda, phi]);
    setOffsets();
    gRoot.setAttribute("transform", `translate(${offX},${offY}) scale(${k})`);
    spherePath.setAttribute("d", path({ type: "Sphere" } as any) ?? "");
    if (!showingDetail) landPath.setAttribute("d", path(land as any) ?? "");
    project();
    updateHalosAndLabels();
    rebuildVoronoi();
  }

  // Coalesce redraws: d3-zoom fires per pointermove, but we only need one
  // reprojection per frame.
  let frame = 0;
  function schedule() {
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      applyTransform();
    });
  }

  function updateHalosAndLabels() {
    const byAnchor = new Map(anchors.map((a) => [a.id, a]));
    for (const f of feats) {
      const id = f.properties.id as string;
      const halo = halos.get(id)!;
      const chip = chips.get(id)!;

      const a = byAnchor.get(id);
      if (!a) {
        halo.setAttribute("r", "0");
        chip.style.display = "none";
        continue;
      }

      // Apparent size in device pixels at the current zoom.
      const sizePx = a.sizePx * k;
      const needsHalo = f.geometry.type === "Point" || sizePx < HALO_THRESHOLD;
      const r = needsHalo ? Math.max(sizePx * 1.35, HALO_MIN) / k : 0;
      halo.setAttribute("cx", String(a.x));
      halo.setAttribute("cy", String(a.y));
      halo.setAttribute("r", String(r));

      const sx = a.x * k + offX;
      const sy = a.y * k + offY;
      const off = Math.max(r ? r * k : sizePx / 2, 8) + 6;
      chip.style.display = sx < -80 || sx > W + 80 || sy < -40 || sy > H + 40 ? "none" : "";
      chip.style.transform = `translate(${sx}px, ${sy - off}px) translate(-50%, -100%)`;
    }
  }

  // --- interaction -------------------------------------------------------
  let active: string | null = null;
  const coarse = window.matchMedia("(pointer: coarse)").matches;
  const CUTOFF = coarse ? 44 : 60;

  function setActive(id: string | null) {
    if (id === active) return;
    if (active) {
      shapes.get(active)?.classList.remove("is-active");
      halos.get(active)?.classList.remove("is-active");
      chips.get(active)?.classList.remove("is-active");
    }
    active = id;
    if (id) {
      shapes.get(id)?.classList.add("is-active");
      halos.get(id)?.classList.add("is-active");
      chips.get(id)?.classList.add("is-active");
    }
  }

  function nearest(mx: number, my: number): string | null {
    if (!delaunay) return null;
    const i = delaunay.find(mx, my);
    if (i == null || i < 0) return null;
    const a = anchors[i];
    const d = Math.hypot(a.x * k + offX - mx, a.y * k + offY - my);
    return d <= CUTOFF ? a.id : null;
  }

  function pointerPos(e: PointerEvent | MouseEvent) {
    const r = svg.getBoundingClientRect();
    return [
      ((e.clientX - r.left) / r.width) * W,
      ((e.clientY - r.top) / r.height) * H,
    ] as const;
  }

  if (!coarse) {
    svg.addEventListener("pointermove", (e) => {
      const [mx, my] = pointerPos(e);
      setActive(nearest(mx, my));
    });
    svg.addEventListener("pointerleave", () => setActive(null));
  }

  svg.addEventListener("click", (e) => {
    const [mx, my] = pointerPos(e);
    const id = nearest(mx, my);
    if (!id) {
      setActive(null);
      return;
    }
    const m = byId.get(id)!;
    // Coarse pointers: first tap reveals, second navigates.
    if (coarse && active !== id) {
      setActive(id);
      return;
    }
    if (m.href) window.location.href = m.href;
  });

  const zoomBehavior = d3zoom<SVGSVGElement, unknown>()
    .scaleExtent([1, MAX_ZOOM])
    .on("zoom", (ev: D3ZoomEvent<SVGSVGElement, unknown>) => {
      const t = ev.transform;
      // d3-zoom's x is allowed to run away to infinity; we consume it as a
      // delta and spend it on rotation, so there is no edge to drag up
      // against in either direction. At zoom k the world spans W*k pixels,
      // so that many pixels of drag is exactly one full turn.
      const dx = t.x - lastTx;
      const dy = t.y - lastTy;
      lastTx = t.x;
      lastTy = t.y;
      const kPrev = k;
      const zooming = t.k !== kPrev;

      // d3 supplies the scale and the raw gesture deltas; position is entirely
      // ours. Its own x and y are never applied, because horizontal position is
      // a rotation and any vertical correction we make would be overwritten by
      // the next event's t.y.
      let holdGeo: [number, number] | null = null;
      let holdAt: readonly [number, number] | null = null;
      if (zooming && ev.sourceEvent) {
        holdAt = pointerPos(ev.sourceEvent as PointerEvent);
        const inv = (projection as any).invert?.([
          (holdAt[0] - offX) / kPrev,
          (holdAt[1] - offY) / kPrev,
        ]);
        // Within about 75° of the centre the cursor can be held to a pixel or
        // two. Past that the globe is degenerate — one pixel spans a huge
        // angle and invert() is ill-conditioned, so anchoring diverges — and
        // we fall back to scaling about the middle of the disc, which is
        // stable and is what globe UIs conventionally do anyway.
        if (
          inv &&
          Number.isFinite(inv[0]) &&
          geoDistance(inv, [-lambda, -phi]) < 1.31
        )
          holdGeo = inv;
      }

      k = t.k;
      if (!suppressRotate && !zooming) {
        lambda = wrap180(lambda + (dx / (W * k)) * 360);
        phi = clampPhi(phi - (dy / (H * k)) * 180);
      }
      setOffsets();

      // Pin the point under the cursor. The correction is made in *degrees*,
      // not pixels: ask what is under the cursor now, and shift the central
      // meridian by the difference in longitude. Pixels-per-degree is not a
      // constant on either projection — on a sphere it falls off towards the
      // limb — so a pixel-scaled nudge overshoots and the loop oscillates
      // instead of settling. Iterating in degrees converges in two or three
      // passes. Vertically the flat map translates, so there the pixel error
      // is exact and can be applied directly.
      if (holdGeo && holdAt) {
        for (let i = 0; i < 6; i++) {
          projection.rotate([lambda, phi]);
          const p = projection(holdGeo);
          if (!p || !Number.isFinite(p[0])) break;
          const ex = holdAt[0] - (p[0] * k + offX);
          const ey = holdAt[1] - (p[1] * k + offY);
          if (Math.abs(ex) < 0.25 && Math.abs(ey) < 0.25) break;
          const under = (projection as any).invert?.([
            (holdAt[0] - offX) / k,
            (holdAt[1] - offY) / k,
          ]);
          if (!under || !Number.isFinite(under[0])) break;
          lambda = wrap180(lambda + wrap180(under[0] - holdGeo[0]));
          phi = clampPhi(phi + (under[1] - holdGeo[1]));
          setOffsets();
        }
      }

      reset.hidden =
        k === 1 &&
        Math.abs(phi + HOME_LAT) < 0.5 &&
        Math.abs(wrap180(lambda - HOME_LON)) < 0.5;
      bumpIdle();
      schedule();
    });

  const sel = select(svg as unknown as SVGSVGElement);
  sel.call(zoomBehavior as any);
  // translateExtent needs the size, so set it after first resize.

  reset.addEventListener("click", () => {
    const dur = window.matchMedia("(prefers-reduced-motion: reduce)").matches
      ? 0
      : 450;

    // Rotation lives outside the zoom transform, so it needs its own tween —
    // and the zoom transition's own x-change must not be spent on rotation
    // while that runs, or the two fight each other.
    suppressRotate = true;
    const from = lambda;
    const fromPhi = phi;
    const delta = wrap180(HOME_LON - from); // always the short way round
    const t0 = performance.now();
    const step = (now: number) => {
      const u = dur === 0 ? 1 : Math.min(1, (now - t0) / dur);
      const e = u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;
      lambda = wrap180(from + delta * e);
      phi = -HOME_LAT + (fromPhi + HOME_LAT) * (1 - e);
      applyTransform();
      if (u < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);

    sel
      .transition()
      .duration(dur)
      .call(zoomBehavior.transform as any, zoomIdentity)
      .on("end interrupt", () => {
        suppressRotate = false;
        lastTx = 0;
        lastTy = 0;
      });
  });

  function refreshExtent() {
    // d3's own translation is never applied — we read its deltas and keep
    // position ourselves — so it must stay unconstrained in both axes or it
    // would silently swallow gestures at the edges. A globe has no edges to
    // bound: every direction comes back round.
    zoomBehavior.translateExtent([
      [-Infinity, -Infinity],
      [Infinity, Infinity],
    ]);
  }

  const ro = new ResizeObserver(() => {
    resize();
    refreshExtent();
    bumpIdle();
  });
  ro.observe(root);

  resize();
  refreshExtent();
  root.classList.add("is-ready");
  // Coarse first paint, then fill in the small islands a beat later.
  bumpIdle();
}
