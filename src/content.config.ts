import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const OCEANS = [
  "arctique",
  "atlantique-nord",
  "atlantique-sud",
  "pacifique-nord",
  "pacifique-sud",
  "indien",
  "antarctique",
] as const;

/**
 * An island. Metadata only — no prose, no geometry.
 * One file per island; the filename is the id (canonical French slug).
 */
const islands = defineCollection({
  loader: glob({ pattern: "**/*.yaml", base: "./src/content/islands" }),
  schema: z.object({
    name_fr: z.string(),
    name_en: z.string(),

    /** island = filled shape | reef = point | misdrawn = real place, wrongly charted */
    kind: z.enum(["island", "reef", "misdrawn"]).default("island"),
    ocean: z.enum(OCEANS),

    /** [lon, lat]. Required before the island can be drawn. */
    coords: z.tuple([z.number(), z.number()]).optional(),
    /** [lon, lat] override for the label, when the centroid sits badly. */
    label_anchor: z.tuple([z.number(), z.number()]).optional(),

    /**
     * Lossy numeric range, for the map hover label ONLY.
     * The authoritative account lives in the story's `notice`.
     * null = open interval. Omit entirely when the dating is too contested
     * to reduce to two numbers.
     */
    span: z.tuple([z.number().nullable(), z.number().nullable()]).optional(),
    /** e.g. "vers" — prefixed to the span when displayed. */
    span_qualifier: z.string().optional(),
  }),
});

/**
 * A story. Lives at stories/{lang}/{slug}.md — lang is derived from the path.
 * A story may cover several islands (Crocker Land + Bradley Land).
 */
const stories = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/stories" }),
  schema: z.object({
    title: z.string(),
    /** Island ids covered by this story. At least one. */
    islands: z.array(z.string()).nonempty(),
    date: z.date(),
    /** Original post on the old blog, if any. */
    source: z.string().url().optional(),

    /**
     * The bullet block that precedes every story.
     * Open-ended and ordered — invent labels per island.
     * `body` is markdown; links and emphasis are expected.
     */
    notice: z
      .array(z.object({ label: z.string(), body: z.string() }))
      .default([]),

    /** Historical map details shown above the notice. */
    images: z
      .array(
        z.object({
          src: z.string(),
          alt: z.string().default(""),
          caption: z.string().optional(),
        })
      )
      .default([]),
  }),
});

export const collections = { islands, stories };
