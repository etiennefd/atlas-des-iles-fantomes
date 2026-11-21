// French spacing, applied at render time to French pages only.
//
// The blog had a non-breaking space before : ; ! ? » and after «, and the
// importer flattened every one of them to a plain space (import_posts.py), so
// a line could break between a word and its colon or inside the guillemets.
// Doing it here rather than in the markdown keeps the files editable — U+00A0
// is invisible in an editor — and covers whatever is written next.
//
// Only existing spaces are made non-breaking. None is added where there was
// none: the stories put no space before ? ! ; and that is the author's usage.

const NBSP = " ";

/** @param {string} s */
export function frenchSpacing(s) {
  return s.replace(/ +(?=[:;!?»])/g, NBSP).replace(/« +/g, "«" + NBSP);
}

/** True for a story file under src/content/stories/fr/. */
function isFrench(file) {
  const p = (file.path || (file.history && file.history[0]) || "").replace(/\\/g, "/");
  return p.includes("/stories/fr/");
}

const SKIP = new Set(["code", "pre", "script", "style"]);

function walk(node) {
  if (node.type === "text") {
    node.value = frenchSpacing(node.value);
    return;
  }
  if (node.type === "element" && SKIP.has(node.tagName)) return;
  if (node.children) node.children.forEach(walk);
}

/** rehype plugin: French spacing in text nodes of French stories. */
export function rehypeFrenchSpacing() {
  return (tree, file) => {
    if (isFrench(file)) walk(tree);
  };
}
