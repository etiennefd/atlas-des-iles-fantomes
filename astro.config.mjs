import { defineConfig } from "astro/config";

export default defineConfig({
  // the live Vercel origin until a real domain exists; change it then
  site: "https://atlas-des-iles-fantomes.vercel.app",
  i18n: {
    locales: ["fr", "en"],
    defaultLocale: "fr",
    routing: { prefixDefaultLocale: true },
  },
});
