import { getCollection, type CollectionEntry } from "astro:content";
import type { Lang } from "../i18n/ui";

export type Island = CollectionEntry<"islands">;
export type Story = CollectionEntry<"stories">;

/** stories/fr/hy-brasil.md -> { lang: "fr", slug: "hy-brasil" } */
export function splitStoryId(id: string): { lang: Lang; slug: string } {
  const [lang, ...rest] = id.split("/");
  return { lang: lang as Lang, slug: rest.join("/") };
}

export type State = "available" | "translated" | "planned";

export type Resolved = {
  island: Island;
  name: string;
  state: State;
  /** The story to link to. Undefined when planned. */
  story?: Story;
  /** Language the linked story is actually in. */
  storyLang?: Lang;
  href?: string;
};

/**
 * Resolve every island against the stories that exist, for one language.
 * An island is `available` if a story in this language lists its id,
 * `translated` if only the other language does, `planned` otherwise.
 */
export async function resolveIslands(lang: Lang): Promise<Resolved[]> {
  const islands = await getCollection("islands");
  const stories = await getCollection("stories");

  const byLang = new Map<string, Map<string, Story>>();
  for (const story of stories) {
    // Drafts keep their notice and image but leave the island "planned".
    if (story.data.draft) continue;
    const { lang: l } = splitStoryId(story.id);
    if (!byLang.has(l)) byLang.set(l, new Map());
    for (const id of story.data.islands) byLang.get(l)!.set(id, story);
  }

  const here = byLang.get(lang) ?? new Map();
  const there = byLang.get(lang === "fr" ? "en" : "fr") ?? new Map();

  return islands
    .map((island): Resolved => {
      const name = lang === "fr" ? island.data.name_fr : island.data.name_en;
      const mine = here.get(island.id);
      const theirs = there.get(island.id);

      if (mine) {
        return {
          island,
          name,
          state: "available",
          story: mine,
          storyLang: lang,
          href: `/${lang}/iles/${splitStoryId(mine.id).slug}/`,
        };
      }
      if (theirs) {
        const otherLang: Lang = lang === "fr" ? "en" : "fr";
        return {
          island,
          name,
          state: "translated",
          story: theirs,
          storyLang: otherLang,
          href: `/${otherLang}/iles/${splitStoryId(theirs.id).slug}/`,
        };
      }
      return { island, name, state: "planned" };
    })
    .sort((a, b) => a.name.localeCompare(b.name, lang));
}

/**
 * "1906 – 1914" · "vers 1325 –" · "" when no span is recorded.
 * Deliberately lossy: the real account lives in the story's notice.
 */
export function lifespan(island: Island): string {
  const span = island.data.span;
  if (!span) return "";
  const [a, b] = span;
  const q = island.data.span_qualifier ? `${island.data.span_qualifier} ` : "";
  const fmt = (y: number) => (y < 0 ? `${Math.abs(y)} av. J.-C.` : String(y));
  if (a === null && b === null) return "";
  if (b === null) return `${q}${fmt(a!)} –`;
  if (a === null) return `– ${fmt(b)}`;
  return `${q}${fmt(a)} – ${fmt(b)}`;
}

export async function counts(lang: Lang) {
  const resolved = await resolveIslands(lang);
  return {
    total: resolved.length,
    written: resolved.filter((r) => r.state !== "planned").length,
  };
}
