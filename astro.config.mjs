import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://example.com", // TODO: real domain
  i18n: {
    locales: ["fr", "en"],
    defaultLocale: "fr",
    routing: { prefixDefaultLocale: true },
  },
});
