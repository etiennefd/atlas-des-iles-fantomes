import { geoPath, type GeoProjection } from "d3-geo";
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
    tx = 0,
    ty = 0;
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

  // Anchor point per island, in projected screen coords (pre-transform).
  const anchors: { id: string; x: number; y: number }[] = [];

  function project() {
    anchors.length = 0;
    for (const f of feats) {
      const id = f.properties.id as string;
      const c = path.centroid(f as any);
      if (Number.isFinite(c[0])) anchors.push({ id, x: c[0], y: c[1] });
      shapes.get(id)!.setAttribute("d", path(f as any) ?? "");
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
      pts[i * 2] = a.x * k + tx;
      pts[i * 2 + 1] = a.y * k + ty;
    });
    delaunay = new Delaunay(pts);
  }

  function resize() {
    const r = root.getBoundingClientRect();
    W = Math.max(320, r.width);
    H = Math.max(240, r.height);
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    projection.fitExtent(
      [
        [8, 8],
        [W - 8, H - 8],
      ],
      fitTarget as any
    );
    project();
    applyTransform();
  }

  function applyTransform() {
    gRoot.setAttribute("transform", `translate(${tx},${ty}) scale(${k})`);
    landPath.setAttribute("d", path(land as any) ?? "");
    updateHalosAndLabels();
    rebuildVoronoi();
  }

  function updateHalosAndLabels() {
    for (const f of feats) {
      const id = f.properties.id as string;
      const shape = shapes.get(id)!;
      const halo = halos.get(id)!;
      const chip = chips.get(id)!;

      const a = anchors.find((p) => p.id === id);
      if (!a) {
        halo.setAttribute("r", "0");
        chip.style.display = "none";
        continue;
      }

      // Apparent size in device pixels at the current zoom.
      let bboxDiag = 0;
      try {
        const b = shape.getBBox();
        bboxDiag = Math.hypot(b.width, b.height) * k;
      } catch {
        bboxDiag = 0;
      }
      const needsHalo =
        f.geometry.type === "Point" || bboxDiag < HALO_THRESHOLD;
      const r = needsHalo ? Math.max(bboxDiag * 1.35, HALO_MIN) / k : 0;
      halo.setAttribute("cx", String(a.x));
      halo.setAttribute("cy", String(a.y));
      halo.setAttribute("r", String(r));

      const sx = a.x * k + tx;
      const sy = a.y * k + ty;
      const off = Math.max((r || bboxDiag / 2) * k, 8) + 6;
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
    const d = Math.hypot(a.x * k + tx - mx, a.y * k + ty - my);
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
      ({ k, x: tx, y: ty } = ev.transform);
      reset.hidden = k === 1 && tx === 0 && ty === 0;
      applyTransform();
    });

  const sel = select(svg as unknown as SVGSVGElement);
  sel.call(zoomBehavior as any);
  // translateExtent needs the size, so set it after first resize.

  reset.addEventListener("click", () => {
    sel
      .transition()
      .duration(window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 450)
      .call(zoomBehavior.transform as any, zoomIdentity);
  });

  function refreshExtent() {
    zoomBehavior.translateExtent([
      [-W * 0.15, -H * 0.15],
      [W * 1.15, H * 1.15],
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
