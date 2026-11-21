// Typography applied at render time, so the markdown stays plain and editable
// (U+00A0 is invisible in an editor) and whatever is written next gets it too.
//
// French:
// - a non-breaking space before : ; ! ? » and after «. The blog had them and
//   the importer flattened them (import_posts.py). Only existing spaces are
//   changed: the stories put no space before ? ! ; and that is the author's
//   usage;
// - numbers kept with their units and their thousands (60 km, 22 h 30,
//   10 000), abbreviations with what follows (M. Kim, c. 150, av. J.-C.), the
//   dialogue dash with its first word;
// - ordinals raised: XXᵉ siècle, 17ᵉ, Iᵉʳ. A century's roman numeral is set in
//   small caps, a sovereign's (Élisabeth Iʳᵉ) in capitals, as French books do.
// English: numbers kept with their units, Mr./Dr./St. with the name.

const NBSP = " ";

const FR_UNITS =
  "km|m|cm|mm|kg|g|t|h|min|s|%|°|ans|an|mois|jours|heures|minutes|secondes|" +
  "degrés|milles|lieues|mètres|kilomètres|pieds|brasses|nœuds|tonnes";
const EN_UNITS =
  "km|m|cm|mm|kg|mi|ft|in|lb|%|°|miles|leagues|knots|degrees|fathoms|feet|metres|meters";

const RULES = {
  fr: [
    [/ +(?=[:;!?»])/g, NBSP],
    [/« +/g, "«" + NBSP],
    [/(\d) h (?=\d)/g, "$1" + NBSP + "h" + NBSP], // 22 h 30, before the units
    [new RegExp(`(\\d) (?=(?:${FR_UNITS})(?![\\p{L}\\d’']))`, "gu"), "$1" + NBSP],
    [/(\d) (?=\d{3}(?!\d))/g, "$1" + NBSP], // 10 000
    [/(^|[\s(])(M\.|MM\.|Mme|Mmes|Mlle|Dr|Me|St|Ste|p\.|pp\.|n°|c\.|av\.|apr\.) (?=\S)/g, "$1$2" + NBSP],
    [/^— /, "—" + NBSP], // dialogue: only a dash that opens the text
  ],
  en: [
    [new RegExp(`(\\d) (?=(?:${EN_UNITS})(?![\\p{L}\\d’']))`, "gu"), "$1" + NBSP],
    [/(^|[\s(])(Mr\.|Mrs\.|Ms\.|Dr\.|St\.|p\.|pp\.|c\.) (?=\S)/g, "$1$2" + NBSP],
  ],
};

/** Spacing only: plain text in, plain text out. */
export function spacing(s, lang) {
  for (const [re, to] of RULES[lang] ?? []) s = s.replace(re, to);
  return s;
}

// --- Ordinals (French) ------------------------------------------------------

// A roman numeral of two letters or more, or of one before "siècle": "Le" is
// L + e, so a lone letter with a bare "e" is only trusted next to the word.
const ROMAN = /(?<![\p{L}\d])([IVXL]+)(er|re|e)(?![\p{L}\d])/gu;
const ARABIC = /(?<![\p{L}\d])(\d+)(er|re|e)(?![\p{L}\d])/gu;
// "XVe et XVIe siècles", "Ier ou IIe siècle": a chain that ends on the word.
const TO_CENTURY = /^(?:(?:\s+(?:et|ou|à|au)\s+|,\s*|\s*[–-]\s*)[IVXL]+(?:er|re|e))*\s+siècles?\b/u;

/**
 * Split text into plain runs and ordinals.
 * @returns {Array<string | {num: string, suffix: string, century: boolean}>}
 */
export function ordinals(s) {
  const hits = [];
  for (const m of s.matchAll(ROMAN)) {
    const [, num, suffix] = m;
    const toCentury = TO_CENTURY.test(s.slice(m.index + m[0].length));
    // "Le" is L + e; "Ier" and "Ire" are never words, so only a lone letter
    // with a bare "e" needs "siècle" after it to count
    if (num.length === 1 && suffix === "e" && !toCentury) continue;
    // a century, unless it is a sovereign's number (Élisabeth Ire)
    const century = suffix === "e" || toCentury;
    hits.push({ index: m.index, length: m[0].length, num, suffix, century });
  }
  for (const m of s.matchAll(ARABIC)) {
    hits.push({ index: m.index, length: m[0].length, num: m[1], suffix: m[2], century: false });
  }
  hits.sort((a, b) => a.index - b.index);
  const out = [];
  let at = 0;
  for (const h of hits) {
    if (h.index < at) continue;
    if (h.index > at) out.push(s.slice(at, h.index));
    out.push({ num: h.num, suffix: h.suffix, century: h.century });
    at = h.index + h.length;
  }
  if (at < s.length) out.push(s.slice(at));
  return out;
}

// --- Markdown strings (notices, captions, notes) ----------------------------

const ordinalHtml = (o) =>
  (o.century ? `<span class="century">${o.num}</span>` : o.num) +
  `<sup class="ord">${o.suffix}</sup>`;

/**
 * Typeset a markdown source string before it is parsed. Link targets, inline
 * HTML and code are left alone, so nothing inside a URL is ever touched.
 */
export function typesetMarkdown(md, lang) {
  return md
    .split(/(\]\([^)]*\)|<[^>]+>|`[^`]*`)/)
    .map((part, i) => {
      if (i % 2) return part; // a protected piece
      const s = spacing(part, lang);
      if (lang !== "fr") return s;
      return ordinals(s)
        .map((o) => (typeof o === "string" ? o : ordinalHtml(o)))
        .join("");
    })
    .join("");
}

// --- rehype, for the story bodies ---------------------------------------------

function langOf(file) {
  const p = (file.path || (file.history && file.history[0]) || "").replace(/\\/g, "/");
  const m = p.match(/\/stories\/(fr|en)\//);
  return m ? m[1] : null;
}

const SKIP = new Set(["code", "pre", "script", "style"]);
const OPENS_TEXT = new Set(["p", "li", "dd", "blockquote"]);

const el = (tagName, className, value) => ({
  type: "element",
  tagName,
  properties: { className: [className] },
  children: [{ type: "text", value }],
});

function walk(node, lang) {
  if (node.type === "element" && SKIP.has(node.tagName)) return;
  if (!node.children) return;
  const next = [];
  node.children.forEach((child, i) => {
    if (child.type !== "text") {
      walk(child, lang);
      next.push(child);
      return;
    }
    let value = child.value;
    // a dialogue dash only counts at the start of a paragraph
    if (!(i === 0 && node.type === "element" && OPENS_TEXT.has(node.tagName))) {
      value = value.replace(/^— /, "\u0000");
    }
    value = spacing(value, lang).replace("\u0000", "— ");
    if (lang !== "fr") {
      next.push({ ...child, value });
      return;
    }
    for (const o of ordinals(value)) {
      if (typeof o === "string") next.push({ type: "text", value: o });
      else {
        next.push(o.century ? el("span", "century", o.num) : { type: "text", value: o.num });
        next.push(el("sup", "ord", o.suffix));
      }
    }
  });
  node.children = next;
}

/** rehype plugin: the typography above, in the text of every story. */
export function rehypeTypeset() {
  return (tree, file) => {
    const lang = langOf(file);
    if (lang) walk(tree, lang);
  };
}
