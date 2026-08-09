#!/usr/bin/env python3
"""Seed src/content/islands/*.yaml with researched coordinates."""
import os, textwrap

OUT = os.path.join(os.path.dirname(__file__), "..", "src", "content", "islands")

# id: (name_fr, name_en, kind, ocean, lon, lat, span_qualifier, span_a, span_b, confidence, source)
# confidence: attested | approximate | conjectural | unknown
I = [
 ("hy-brasil","L'île de Hy-Brasil","The Island of Hy-Brasil","island","atlantique-nord",
  -15.0,51.5,None,1325,1865,"approximate","West of Ireland; position varied across charts. Last mention 1865 as Brasil Rock."),
 ("mayda","Mayda","Mayda","island","atlantique-nord",
  -20.0,47.0,None,1367,1906,"approximate","Babcock: open Atlantic far west of lower Brittany, SW of Ireland, c. 46-48 deg N. Position migrated westward over time."),
 ("frisland","Frisland","Frisland","island","atlantique-nord",
  -25.0,62.5,None,1558,1660,"approximate","Zeno map 1558: south of Iceland. Reappeared off Labrador 1630; gone by 1652."),
 ("buss","L'île Buss","Buss Island","island","atlantique-nord",
  -25.0,57.0,None,1578,1856,"approximate","Charted between Ireland and Frisland at about 57 deg N. Frobisher's third expedition."),
 ("antillia","Antillia","Antillia","island","atlantique-nord",
  -45.0,32.0,None,1424,1500,"approximate","Pizzigano chart 1424, far west of Portugal; Satanazes just north."),
 ("saint-brendan","L'île de Saint-Brendan","Saint Brendan's Island","island","atlantique-nord",
  -25.0,30.0,None,None,1759,"conjectural","Position wandered constantly across a millennium of charts. Verify against whichever depiction the story uses."),
 ("bacalao","Bacalao","Bacalao","island","atlantique-nord",
  -52.0,47.5,None,1508,1600,"conjectural","Terra dos Bacalhaus, Newfoundland region. Position highly variable."),
 ("ile-des-demons","L'île des Démons","The Isle of Demons","island","atlantique-nord",
  -55.5,51.5,None,1508,1600,"conjectural","Usually charted off the northern tip of Newfoundland, near Quirpon."),
 ("jacquet","L'île Jacquet","Jacquet Island","island","atlantique-nord",
  -43.0,47.0,None,1836,1900,"attested","Charted at approximately 47 N 43 W, just east of the Flemish Cap. Reported by John Scott of the Seaflower, 1836."),
 ("groclant","Groclant","Groclant","island","arctique",
  -45.0,72.0,None,1507,1700,"conjectural","Groclandia, northwest of Greenland on Ruysch/Mercator maps."),
 ("thule","Thulé","Thule","island","atlantique-nord",
  -19.0,64.0,"vers",-330,1600,"conjectural","Pytheas, c. 330 BCE. Variously identified with Iceland, Norway, Shetland. Planned-state test case."),
 ("crocker-land","Crocker Land","Crocker Land","island","arctique",
  -100.0,83.0,None,1906,1914,"attested","Peary, Nearest the Pole: sighted from Cape Colgate, c. 130 miles NW, at 83 N 100 W."),
 ("bradley-land","Bradley Land","Bradley Land","island","arctique",
  -102.0,84.75,None,1907,1918,"attested","Cook: extended 84 deg 20' N to 85 deg 11' N at about 102 W. Midpoint used. Some sources give the southern limit as 83 deg 20'."),
 ("bermeja","L'île de Bermeja","Bermeja","island","atlantique-nord",
  -91.0,22.5,None,1539,1921,"approximate","Alonso de Santa Cruz 1539; c. 55 nautical miles off the NW Yucatan coast. A seamount sits at 22 38.76 N 90 51.3 W."),
 ("californie","L'île de Californie","The Island of California","misdrawn","pacifique-nord",
  -114.0,28.0,None,1510,1747,"approximate","Baja California drawn as an island. Ferdinand VII's 1747 decree conventionally ends it."),
 ("coree","La Corée","Korea","misdrawn","pacifique-nord",
  127.5,37.0,None,1568,1700,"approximate","Korea depicted as an island on European charts of the 16th-17th centuries."),
 ("los-jardines","Los Jardines","Los Jardines","island","pacifique-nord",
  150.0,21.0,None,1528,1973,"conjectural","SOURCES CONFLICT: English Wikipedia says NE of the Marianas near Guam; German Wikipedia says east of the Marshalls. Pick per your research."),
 ("maria-de-lajara","L'île María de Lajara","María de Lajara","island","pacifique-nord",
  -140.0,27.0,None,1699,1830,"attested","Pacific charts registered it at about 27 N, 140 W (ENE of Hawaii) from the late 17th to early 19th century."),
 ("tuanaki","Tuanaki","Tuanaki","island","pacifique-sud",
  -158.0,-23.5,None,1842,1856,"approximate","South of Rarotonga, within two days' sail of Mangaia. Haymet Rocks proposed as a remnant. Missionary searches failed 1844 and 1856."),
 ("terre-de-davis","La Terre de Davis","Davis Land","island","pacifique-sud",
  -90.0,-27.0,None,1687,1770,"conjectural","Sighted by Edward Davis 1687 sailing south from the Galapagos. Later conflated with Easter Island."),
 ("ernest-legouve","Récif Ernest-Legouvé","Ernest Legouvé Reef","reef","pacifique-sud",
  -150.667,-35.2,None,1902,1983,"attested","International Hydrographic Bureau, 9 Feb 1957: 35 12' S 150 40' W. Searched 1982-83, not found."),
 ("maria-theresa","Récif Maria-Theresa","Maria Theresa Reef","reef","pacifique-sud",
  -136.65,-36.833,None,1843,1983,"attested","Reported 16 Nov 1843 by Capt. Asaph P. Taber of the Maria-Theresa. Also charted as Tabor Reef."),
 ("aurora","Les îles Aurora","The Aurora Islands","island","atlantique-sud",
  -47.817,-52.617,None,1762,1870,"attested","Spanish ship San Miguel fixed them at 52 37' S, 47 49' W. Surveyed by the Atrevida, 20 Feb 1794."),
 ("elizabeth","L'île Elizabeth","Elizabeth Island","island","antarctique",
  -70.0,-57.0,None,1578,1747,"approximate","Drake, October 1578, at latitude 57 S (Hakluyt: '57 and a terce'). Longitude unrecorded; Pactolus Bank proposed."),
 ("dougherty","L'île de Dougherty","Dougherty Island","island","antarctique",
  -120.333,-59.333,None,1841,1934,"attested","Capt. Daniel Dougherty of the James Stewart, 1841: 59 20' S 120 20' W. Still on maps in 1934."),
 ("emerald","L'île Emerald","Emerald Island","island","antarctique",
  162.2,-57.5,None,1821,1909,"attested","Capt. William Elliot of the Emerald, December 1821: 57 30' S 162 12' E."),
 ("juan-de-lisboa","Juan de Lisboa","Juan de Lisboa","island","indien",
  55.0,-28.0,None,1600,1800,"conjectural","Charted southeast of Madagascar on 17th-18th century maps."),
 ("dos-romeiros","Dos Romeiros","Dos Romeiros","island","indien",
  57.0,-26.0,None,1600,1800,"conjectural","Depicted alongside Juan de Lisboa. Relative position guessed."),
 ("kianida","Kianida","Kianida","island","atlantique-nord",
  33.0,43.5,None,1467,1600,"conjectural","Cianeis Insula, shown in the Black Sea on a 1467 map. Ocean field needs a 'mer-noire' value adding."),
 # --- no position found ---
 ("saint-mathieu","L'île Saint-Mathieu","Saint Matthew Island","island","atlantique-sud",
  None,None,None,None,None,"unknown","Sao Mateus, South Atlantic, but I could not source a position. Needs your notes."),
 ("zanara","Zanara","Zanara","island","atlantique-nord",
  None,None,None,None,None,"unknown","No source found. Needs your notes."),
 ("ile-aux-vaches","L'île aux Vaches","Cow Island","island","atlantique-nord",
  None,None,None,None,None,"unknown","No source found. Needs your notes."),
]

def q(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'

os.makedirs(OUT, exist_ok=True)
for (iid, fr, en, kind, ocean, lon, lat, qual, a, b, conf, note) in I:
    L = []
    L.append(f"name_fr: {q(fr)}")
    L.append(f"name_en: {q(en)}")
    L.append(f"kind: {kind}")
    L.append(f"ocean: {ocean}")
    if lon is not None:
        L.append(f"coords: [{lon}, {lat}]")
    else:
        L.append("# coords: [lon, lat]   # UNKNOWN — see coords_note")
    if a is not None or b is not None:
        L.append(f"span: [{'null' if a is None else a}, {'null' if b is None else b}]")
    if qual:
        L.append(f"span_qualifier: {qual}")
    L.append(f"coords_confidence: {conf}")
    for line in textwrap.wrap(note, 74):
        pass
    L.append("coords_note: >-")
    for line in textwrap.wrap(note, 72):
        L.append("  " + line)
    open(os.path.join(OUT, iid + ".yaml"), "w").write("\n".join(L) + "\n")

print(f"wrote {len(I)} island files")
