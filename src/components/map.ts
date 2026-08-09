import { geoPath, geoCentroid, geoBounds, type GeoProjection } from "d3-geo";
import { geoVanDerGrinten } from "d3-geo-projection";
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
// Latitude band the map is fitted to. Van der Grinten inflates the poles
// enormously; cropping below -62 keeps Antarctica out of the frame while
// still showing every Southern Ocean phantom (the lowest is Dougherty, -59.3).
const FIT_SOUTH = -62;
const FIT_NORTH = 84;
const MAX_ZOOM = 8;
// Central meridian the map opens on and returns to. 0 is Atlantic-centred;
// -160 would open on the Pacific. Van der Grinten is a round projection, so
// it can't be tiled the way a cylindrical one can — horizontal panning
// rotates the globe instead, which is seamless and has no edge to reach.
const HOME_LON = 0;

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
    k = 1,
    ty = 0;
  // Horizontal position is a rotation, not a translation: `lambda` is the
  // projection's rotation and `lastTx` only exists to turn d3-zoom's
  // ever-growing x into a per-gesture delta.
  let lambda = HOME_LON;
  let lastTx = 0;
  let suppressRotate = false;
  const projection: GeoProjection = geoVanDerGrinten();
  const path = geoPath(projection);

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
    for (const g of geoInfo) {
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

  // Sample the latitude band we want in frame. Antarctica is still drawn but
  // falls below the viewBox, which clips it.
  const fitTarget = {
    type: "MultiPoint",
    coordinates: (() => {
      const pts: [number, number][] = [];
      for (let lon = -180; lon <= 180; lon += 15) {
        pts.push([lon, FIT_SOUTH], [lon, FIT_NORTH]);
      }
      pts.push([-180, 0], [180, 0]);
      return pts;
    })(),
  };

  let delaunay: Delaunay<number> | null = null;
  function rebuildVoronoi() {
    if (!anchors.length) return;
    // Delaunay in *transformed* screen space, so the cutoff stays honest
    // regardless of zoom level.
    const pts = new Float64Array(anchors.length * 2);
    anchors.forEach((a, i) => {
      pts[i * 2] = a.x * k;
      pts[i * 2 + 1] = a.y * k + ty;
    });
    delaunay = new Delaunay(pts);
  }

  function resize() {
    const r = root.getBoundingClientRect();
    W = Math.max(320, r.width);
    H = Math.max(240, r.height);
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    projection.rotate([lambda, 0]);
    projection.fitExtent(
      [
        [8, 8],
        [W - 8, H - 8],
      ],
      fitTarget as any
    );
    applyTransform();
  }

  function applyTransform() {
    // Rotation changes the geometry itself, so every path is regenerated —
    // there is no transform shortcut for a change of central meridian.
    projection.rotate([lambda, 0]);
    gRoot.setAttribute("transform", `translate(0,${ty}) scale(${k})`);
    landPath.setAttribute("d", path(land as any) ?? "");
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

      const sx = a.x * k;
      const sy = a.y * k + ty;
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
    const d = Math.hypot(a.x * k - mx, a.y * k + ty - my);
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
      lastTx = t.x;
      k = t.k;
      ty = t.y;
      if (!suppressRotate) lambda = wrap180(lambda + (dx / (W * k)) * 360);
      reset.hidden =
        k === 1 && ty === 0 && Math.abs(wrap180(lambda - HOME_LON)) < 0.5;
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
    const delta = wrap180(HOME_LON - from); // always the short way round
    const t0 = performance.now();
    const step = (now: number) => {
      const u = dur === 0 ? 1 : Math.min(1, (now - t0) / dur);
      const e = u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;
      lambda = wrap180(from + delta * e);
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
      });
  });

  function refreshExtent() {
    // Unbounded in x — that is the wrap-around. Vertical stays penned in so
    // the map can't be dragged off the top or bottom of the frame.
    zoomBehavior.translateExtent([
      [-Infinity, -H * 0.15],
      [Infinity, H * 1.15],
    ]);
  }

  const ro = new ResizeObserver(() => {
    resize();
    refreshExtent();
  });
  ro.observe(root);

  resize();
  refreshExtent();
  root.classList.add("is-ready");
}
