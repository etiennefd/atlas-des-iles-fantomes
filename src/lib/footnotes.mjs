// remark-gfm writes its footnote section in English ("Footnotes", "Back to
// reference 1") with a screen-reader-only heading. The blog showed a visible
// "Notes" heading, so the heading is shown and both labels are taken from the
// story's language. The story page writes the same markup for footnotes called
// from the notice or a caption ([slug].astro), with the same strings.

import { ui } from "../i18n/ui.ts";

function langOf(file) {
  const p = (file.path || (file.history && file.history[0]) || "").replace(/\\/g, "/");
  const m = p.match(/\/stories\/(fr|en)\//);
  return m ? m[1] : null;
}

function walk(node, t) {
  if (node.type === "element") {
    const props = node.properties || {};
    if (node.tagName === "h2" && props.id === "footnote-label") {
      delete props.className;
      node.children = [{ type: "text", value: t.notes }];
    }
    if (node.tagName === "a" && "dataFootnoteBackref" in props) {
      props.ariaLabel = t.backToText;
    }
  }
  if (node.children) node.children.forEach((c) => walk(c, t));
}

/** rehype plugin: localise remark-gfm's footnote section. */
export function rehypeFootnoteLabels() {
  return (tree, file) => {
    const lang = langOf(file);
    if (lang) walk(tree, ui[lang]);
  };
}
