// Where each language lives.
//
// In production each language has its own subdomain and is served from the
// root: ilesfantomes.etiennefd.com/iles/antillia/ is dist/fr/iles/antillia/,
// rewritten there by vercel.json. Everywhere else (npm run dev, npm run
// preview, Vercel's preview deployments) there is one host and the language
// is the first path segment, as the build lays it out. So every internal link
// goes through url() below, never a hand-written `/${lang}/...`.
//
// Vercel sets VERCEL_ENV at build time. ATLAS_SPLIT_HOSTS=1 forces the
// production layout in a local build, to inspect its links.

export const ORIGIN = {
  fr: "https://ilesfantomes.etiennefd.com",
  en: "https://phantomislands.etiennefd.com",
};

export const SPLIT_HOSTS =
  process.env.VERCEL_ENV === "production" ||
  process.env.ATLAS_SPLIT_HOSTS === "1";

/**
 * A link to `path` on `lang`'s site, written on a page in `from`. Same-site
 * links stay relative to the host; links across languages are absolute once
 * the languages are on different hosts.
 *
 * @param {"fr" | "en"} lang
 * @param {string} path starts and ends with "/", e.g. "/liste/"
 * @param {"fr" | "en"} [from] the language of the linking page; defaults to `lang`
 * @returns {string}
 */
export function url(lang, path = "/", from = lang) {
  if (!SPLIT_HOSTS) return `/${lang}${path}`;
  return lang === from ? path : ORIGIN[lang] + path;
}
