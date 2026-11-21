export const LANGS = ["fr", "en"] as const;
export type Lang = (typeof LANGS)[number];

export const ui = {
  fr: {
    siteTitle: "Atlas des îles fantômes",
    tagline: "Des îles qu’on a cru voir",
    list: "Liste des îles",
    map: "Carte",
    about: "À propos",
    forthcoming: "à venir",
    sources: "Sources",
    originally: "Publié d’abord sur",
    otherLang: "English",
    onlyInOther:
      "Cette histoire n’existe qu’en anglais pour l’instant.",
    read: "Lire en anglais",
    otherOnly: "en anglais seulement",
    written: "écrites",
    reset: "Réinitialiser la carte",
    notes: "Notes",
    backToText: "Retour au texte",
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
    otherOnly: "French only",
    written: "written",
    reset: "Reset the map",
    notes: "Notes",
    backToText: "Back to the text",
  },
} as const;

export const other = (lang: Lang): Lang => (lang === "fr" ? "en" : "fr");
