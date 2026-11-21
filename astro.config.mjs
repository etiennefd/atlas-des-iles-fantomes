import { defineConfig } from "astro/config";
import { rehypeTypeset } from "./src/lib/typo.mjs";
import { rehypeFootnoteLabels } from "./src/lib/footnotes.mjs";
import { ORIGIN, SPLIT_HOSTS } from "./src/lib/hosts.mjs";

export default defineConfig({
  markdown: {
    rehypePlugins: [rehypeTypeset, rehypeFootnoteLabels],
  },
  // Each language has its own host in production (src/lib/hosts.mjs); French
  // is the default, so it stands for the site.
  site: ORIGIN.fr,
  // Production serves French from "/" by a vercel.json rewrite, which Vercel
  // applies only where no file exists, so the build must not write a root
  // index.html there. Everywhere else "/" sends you to the French tree.
  redirects: SPLIT_HOSTS ? {} : { "/": "/fr/" },
  i18n: {
    locales: ["fr", "en"],
    defaultLocale: "fr",
    routing: { prefixDefaultLocale: true, redirectToDefaultLocale: false },
  },
});
