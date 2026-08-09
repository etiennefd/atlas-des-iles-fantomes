# Coordinates — provenance

Every island's position, where it came from, and how much to trust it.
Machine-readable equivalents live in `coords_confidence` and `coords_note`
in each `src/content/islands/*.yaml`.

**attested** — a specific published position exists
**approximate** — a described region, no fixed coordinate; I picked a plausible point
**conjectural** — my inference from context; check before relying on it
**unknown** — no position found

Positions are `[lon, lat]`, matching GeoJSON order.

---

## Attested (9)

| id | position | source |
|---|---|---|
| `jacquet` | −43.0, 47.0 | Charted just east of the Flemish Cap. Reported by John Scott of the *Seaflower*, 1836. |
| `crocker-land` | −100.0, 83.0 | Peary, *Nearest the Pole*: sighted from the summit of Cape Colgate, c. 130 miles NW. |
| `bradley-land` | −102.0, 84.75 | Cook: extended 84°20′N to 85°11′N at about 102°W. Midpoint used. **Sources differ** — some give the southern limit as 83°20′N, which would move the midpoint to 84.26. |
| `maria-de-lajara` | −140.0, 27.0 | Pacific charts registered it around 27°N, 140°W from the late 17th to early 19th century. |
| `ernest-legouve` | −150.667, −35.2 | International Hydrographic Bureau, 9 Feb 1957: 35°12′S 150°40′W. Searched 1982–83, not found. |
| `maria-theresa` | −136.65, −36.833 | Reported 16 Nov 1843 by Capt. Asaph P. Taber of the *Maria-Theresa*. Note: Verne gives 37°11′S 153°00′W on the Paris meridian. |
| `aurora` | −47.817, −52.617 | The Spanish *San Miguel* fixed them at 52°37′S, 47°49′W; surveyed by the *Atrevida*, 20 Feb 1794. |
| `dougherty` | −120.333, −59.333 | Capt. Daniel Dougherty of the *James Stewart*, 1841. Keates 1860 and Stannard 1886 gave slightly different fixes. |
| `emerald` | 162.2, −57.5 | Capt. William Elliot of the *Emerald*, December 1821: 57°30′S 162°12′E. |

## Approximate (10)

| id | position | basis |
|---|---|---|
| `hy-brasil` | −15.0, 51.5 | West of Ireland. Position varied across five centuries of charts; there is no single right answer. |
| `mayda` | −20.0, 47.0 | Babcock: open Atlantic far west of lower Brittany, roughly 46–48°N. Migrated westward over time toward Newfoundland and Bermuda. |
| `frisland` | −25.0, 62.5 | Zeno map, 1558: south of Iceland. Reappeared off Labrador in 1630. |
| `buss` | −25.0, 57.0 | Charted between Ireland and Frisland at about 57°N. |
| `antillia` | −45.0, 32.0 | Pizzigano chart, 1424: far west of Portugal, with Satanazes just north. |
| `bermeja` | −91.0, 22.5 | Santa Cruz, 1539; c. 55 nautical miles off the NW Yucatán coast. A seamount sits at 22°38.76′N 90°51.3′W, which is a defensible alternative. |
| `californie` | −114.0, 28.0 | Baja drawn as an island. Placeholder is a blob; the real shape should be the long N–S sliver. |
| `coree` | 127.5, 37.0 | Korea as an island on 16th–17th century European charts. |
| `tuanaki` | −158.0, −23.5 | South of Rarotonga, within two days' sail of Mangaia. Haymet Rocks proposed as a remnant. |
| `elizabeth` | −70.0, −57.0 | Drake, October 1578, at latitude 57°S (Hakluyt: "57 and a terce"). **Longitude is unrecorded** — I used the Pactolus Bank area west of Cape Horn. |

## Conjectural (10) — check these

| id | position | reasoning |
|---|---|---|
| `saint-brendan` | −25.0, 30.0 | Wandered constantly for a millennium. Pick whichever depiction your story uses. |
| `bacalao` | −52.0, 47.5 | Terra dos Bacalhaus, Newfoundland region. Highly variable. |
| `ile-des-demons` | −55.5, 51.5 | Usually off the northern tip of Newfoundland, near Quirpon. Often conflated with Satanazes. |
| `groclant` | −45.0, 72.0 | Groclandia, NW of Greenland on Ruysch and Mercator. |
| `thule` | −19.0, 64.0 | Pytheas, c. 330 BCE. Variously Iceland, Norway, Shetland. Placed on Iceland here. |
| `terre-de-davis` | −90.0, −27.0 | Sighted 1687 sailing south from the Galápagos; later conflated with Easter Island (109°W), so this could move a long way west. |
| `juan-de-lisboa` | 55.0, −28.0 | SE of Madagascar on 17th–18th century charts. |
| `dos-romeiros` | 57.0, −26.0 | Depicted alongside Juan de Lisboa; **relative position guessed entirely**. |
| `kianida` | 33.0, 43.5 | Cianeis Insula, in the Black Sea on a 1467 map. Needed a new `mer-noire` ocean value. |
| `los-jardines` | 150.0, 21.0 | **Sources conflict.** English Wikipedia: NE of the Marianas near Guam. German Wikipedia: east of the Marshalls. I used the former. |

## Unknown (3) — I need your notes

| id | why |
|---|---|
| `saint-mathieu` | São Mateus, South Atlantic, but I couldn't source a position. |
| `zanara` | Nothing found under this name. |
| `ile-aux-vaches` | Nothing found under this name. |

These three have `coords` commented out and are skipped by the geojson build.

---

## Also worth flagging

**Spans are lossy by design.** Where I gave an end year for something never
formally struck, treat it as the last chart I could find it on, not a
disproof date. The real account belongs in the story's `notice`.

**`kianida` is in the Black Sea**, which broke the ocean enum — I added
`mer-noire`. Worth deciding whether the Van der Grinten framing should still
work when one island is inland from every ocean.

**Three of the placeholder blobs are misleading in shape**, not just position:
`californie` should be a long N–S sliver, `coree` a peninsula-shaped mass,
and `frisland` the distinctive Zeno lozenge. Those three would repay tracing
first, because their shapes carry the argument.

---

## Update — the three unknowns are resolved

Pulled from the notices on the blog:

| id | position | basis |
|---|---|---|
| `zanara` | 10.99, 42.3 | **Mediterranean**, not Atlantic. Tyrrhenian Sea off Tuscany near Monte Argentario, between Giglio and Giannutri. Mercator 1589 → c. 1720. |
| `saint-mathieu` | −13.0, −1.2 | Atlantic west of Africa, about 1000 km north of Ascension. Possibly a confusion with Annobón, at the same latitude. |
| `ile-aux-vaches` | −30.0, −3.0 | Atlantic between South America and Africa, off the Brazilian coast on the Piri Reis map of 1513 — apparently its only appearance. Position read off the fragment, so loose. |

Zanara needed a `mediterranee` ocean value, the same situation as Kianida in
the Black Sea. Two of thirty-four islands are now in enclosed seas.

## Added

| id | position | basis |
|---|---|---|
| `nakanotorishima` | 154.0, 30.1 | North Pacific east of Japan, charted around 30°N 154°E. Approximate — worth checking against the 1941 chart. |
| `nimrod` | −158.0, −56.0 | **Attested.** Approximately 56°S 158°W, east of Emerald and west of Dougherty. |

Both have `draft: true` story files carrying their notice and map image, which
keeps them showing as *à venir* on the map until the prose is finished.

## Gotcha worth remembering

**d3-geo reads polygons spherically.** An exterior ring wound the wrong way
doesn't render as a small island — it renders as *the entire planet except
that island*, i.e. a burgundy disc swallowing the map. This bit me on the first
render.

`scripts/build_geojson.py` now forces clockwise winding. QGIS and geojson.io
both export RFC 7946 counterclockwise, so **anything you trace will need
flipping**. Run the winding check before committing new geometry.
