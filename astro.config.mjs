import { defineConfig } from "astro/config";
import { rehypeTypeset } from "./src/lib/typo.mjs";
import { rehypeFootnoteLabels } from "./src/lib/footnotes.mjs";

export default defineConfig({
  markdown: {
    rehypePlugins: [rehypeTypeset, rehypeFootnoteLabels],
  },
  // the live Vercel origin until a real domain exists; change it then
  site: "https://atlas-des-iles-fantomes.vercel.app",
  i18n: {
    locales: ["fr", "en"],
    defaultLocale: "fr",
    routing: { prefixDefaultLocale: true },
  },
});
