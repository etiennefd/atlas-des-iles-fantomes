import { defineConfig } from "astro/config";
import { rehypeFrenchSpacing } from "./src/lib/typo.mjs";

export default defineConfig({
  markdown: {
    rehypePlugins: [rehypeFrenchSpacing],
  },
  // the live Vercel origin until a real domain exists; change it then
  site: "https://atlas-des-iles-fantomes.vercel.app",
  i18n: {
    locales: ["fr", "en"],
    defaultLocale: "fr",
    routing: { prefixDefaultLocale: true },
  },
});
