"""Adventuring gear table parser for the French SRD 5.2.1.

CALIBRATED against the pinned FR PDF on 2026-08-03, the "Matériel
d'aventurier" reference table (p.101-102, inside the "Équipement" chapter,
p.95-106). Ported from `parse_gear_en.py`: the Objet/Poids/Prix reference
table only, row-coherent the same way the Armes/Armures tables are,
deliberately NOT the richer per-item prose catalogue that follows it
alphabetically and is interleaved with this very table in the source --
the same deferral EN already made, for the same reason (two different
grammars, solving both in one pass would mean calibrating both at once).

THE SAME MID-TABLE HEADER-REPEAT ARTEFACT EN'S TABLE HAS: "Objet / Poids /
Prix" reappears verbatim partway through (before "Miroir"), the same
`columns_of()` narrow-block displacement already documented in
`parse_weapons_en.py`. Skipped outright by exact match, not counted as
the table's end.

TWO ROW SHAPES THIS TABLE HAS THAT NEITHER THE EN GEAR TABLE NOR THE FR
WEAPONS/ARMOR TABLES DO, both found by the parser stopping early with
zero anomalies (the "table ended naturally" exit) rather than by a caught
error -- so, as with the weapons table's merged Hache-à-deux-mains row,
neither would have shown up as a count deficit's *reason* without reading
past the stopping point by hand:

1. **A NAME can wrap onto a second physical line**: "Paquetage
   d'exploration" / "souterraine" -- long enough to overflow the column
   width EN's shorter equivalent name did not. Tried as a fallback only
   when the ordinary one-line-name shape does not resolve to a valid
   Poids/Prix pair immediately after it, so it does not risk mis-reading
   an ordinary short name as the first half of a wrapped one.
2. **Weight can carry a parenthetical annotation on ITS OWN following
   line**: "Outre\n2,5 kg\n(pleine)\n2 pa" -- "(pleine)" ["full"] describes
   what the weight figure assumes, and sits between the weight value and
   the price with no delimiter of its own. Tried as a second fallback,
   after the plain 3-line shape, before the wrapped-name shape (an
   annotation line is never itself a valid Prix value, so trying it
   first cannot mask a real wrapped name).

WEIGHT AND COST also accept the bare word "Variable" (Focaliseur
arcanique, Focaliseur druidique, Munitions, Symbole sacré all price and
weigh "Variable"/"Variable") -- the FR equivalent of EN's own "Varies"
exception for the same handful of price-varies items.
"""

import re

import canon
from parse_spells import _dehyphenate_numbered

TABLE_HEADER = ["Objet", "Poids", "Prix"]
SECTION_HEAD = "Matériel d’aventurier"

_WEIGHT_RE = re.compile(r"^[\d,.\s]+\s?(?:kg|g)\.?$|^—$|^Variable$")
_COST_RE = re.compile(r"^[\d\s]+(?:pc|pa|pe|po|pp)$|^Variable$")


def _find_table_start(stripped):
    for i, l in enumerate(stripped):
        if l != SECTION_HEAD:
            continue
        k = i + 1
        while k < len(stripped) and not stripped[k]:
            k += 1
        if stripped[k : k + 3] == TABLE_HEADER:
            return k + 3
    return None


def parse_stream(lines, page_of):
    stripped = [l.strip() for l in lines]

    def page_at(i):
        return page_of[i] if i < len(page_of) else (page_of[-1] if page_of else 0)

    start = _find_table_start(stripped)
    gear, anomalies = [], []
    if start is None:
        anomalies.append({"page": 0, "line": 0, "detail": "Matériel d'aventurier table header not found"})
        return gear, anomalies

    i = start
    while i < len(stripped) and not stripped[i]:
        i += 1

    while i < len(stripped):
        if stripped[i : i + 3] == TABLE_HEADER:
            i += 3
            if i < len(stripped) and not stripped[i]:
                i += 1
            continue

        name = stripped[i]
        if not name:
            break

        w1 = stripped[i + 1] if i + 1 < len(stripped) else ""
        c1 = stripped[i + 2] if i + 2 < len(stripped) else ""
        w2 = stripped[i + 2] if i + 2 < len(stripped) else ""
        c2 = stripped[i + 3] if i + 3 < len(stripped) else ""
        wrapped_name = name + " " + w1 if i + 1 < len(stripped) else name

        if _WEIGHT_RE.match(w1) and _COST_RE.match(c1):
            gear.append({"name": name, "weight": w1, "cost": c1, "page": page_at(i)})
            i += 3
        elif (
            _WEIGHT_RE.match(w1) and not _COST_RE.match(c1) and not _WEIGHT_RE.match(c1)
            and c1 and i + 3 < len(stripped) and _COST_RE.match(stripped[i + 3])
        ):
            # Weight carries a parenthetical annotation on its own line
            # before the price -- "Outre / 2,5 kg / (pleine) / 2 pa".
            gear.append(
                {"name": name, "weight": "%s %s" % (w1, c1), "cost": stripped[i + 3], "page": page_at(i)}
            )
            i += 4
        elif _WEIGHT_RE.match(w2) and _COST_RE.match(c2):
            # The name itself wrapped onto a second physical line --
            # "Paquetage d'exploration / souterraine".
            gear.append({"name": wrapped_name, "weight": w2, "cost": c2, "page": page_at(i)})
            i += 4
        else:
            break

        if i < len(stripped) and not stripped[i]:
            i += 1

    return gear, anomalies


def parse(pages, suspect_pages=()):
    suspect = set(suspect_pages)

    numbered = []
    for number, raw in enumerate(pages, start=1):
        for line in raw.split("\n"):
            numbered.append((number, line))

    numbered = _dehyphenate_numbered(numbered)
    lines = [l for _, l in numbered]
    page_of = [n for n, _ in numbered]

    found, anomalies = parse_stream(lines, page_of)

    gear, conflicts = [], []
    for item in found:
        if item["page"] in suspect:
            conflicts.append(
                {"page": item["page"], "name": item["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            gear.append(item)

    gear.sort(key=lambda g: canon.slugify(g["name"]))
    return gear, anomalies, conflicts
