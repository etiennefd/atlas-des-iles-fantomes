export const LANGS = ["fr", "en"] as const;
export type Lang = (typeof LANGS)[number];

export const ui = {
  fr: {
    siteTitle: "Atlas des îles fantômes",
    tagline: "Des îles qu'on a cru voir",
    list: "Liste des îles",
    map: "Carte",
    about: "À propos",
    forthcoming: "à venir",
    sources: "Sources",
    originally: "Publié d'abord sur",
    otherLang: "English",
    onlyInOther:
      "Cette histoire n'existe qu'en anglais pour l'instant.",
    read: "Lire en anglais",
    written: "écrites",
  },
  en: {
    siteTitle: "Atlas of Phantom Islands",
    tagline: "Islands we thought we saw",
    list: "List of islands",
    map: "Map",
    about: "About",
    forthcoming: "forthcoming",
    sources: "Sources",
    originally: "First published at",
    otherLang: "Français",
    onlyInOther:
      "This story exists only in French for now.",
    read: "Read it in French",
    written: "written",
  },
} as const;

export const other = (lang: Lang): Lang => (lang === "fr" ? "en" : "fr");
