"""Adventuring gear table parser for the English SRD 5.2.1.

CALIBRATED against the pinned EN PDF on 2026-08-03, the Adventuring Gear
reference table (p.95-96, inside the "Equipment" chapter, p.89-103).
82 items, 0 anomalies.

WHAT THIS CAPTURES, AND WHAT IT DELIBERATELY DOES NOT: this is the
Item/Weight/Cost REFERENCE TABLE only -- row-coherent in the same way the
Weapons and Armor tables are (see parse_weapons_en.py for the measured
explanation). The SRD also gives most of these 82 items their own
individual prose entry afterward, in alphabetical order, some carrying
real rules text (Ball Bearings' saving throw, Caltrops' damage, a Bedroll's
interaction with extreme cold) and two of them (Arcane Focus, Druidic
Focus) their own further nested variant sub-table. That per-item rules
catalogue is a DIFFERENT grammar from this one -- much closer in shape to a
magic item entry (name, one-line head, description) than to this table --
and interleaved with this very table in the source (the table sits between
the "Ammunition" and "Antitoxin" prose entries, splitting the alphabetical
catalogue in two around itself). Capturing both correctly in one pass
would mean solving two grammars and their interleaving at once; this pass
takes the reliable, unambiguous half and leaves the richer prose catalogue
named and deferred, the same discipline already applied twice before to
Equipment as a whole.

THE ONE ARTEFACT THIS TABLE HAS THAT WEAPONS AND ARMOR DO NOT: its own
"Item / Weight / Cost" column-header block reappears VERBATIM mid-table,
between "Ink" and "Ink Pen" -- the same narrow-block column-misclassification
already named in parse_weapons_en.py (a short header line falls under the
span-ratio threshold that classifies the surrounding rows as a single
wide block, and gets re-inserted at its own, unrelated position). Naively
stopping the table at the first row that fails to parse would end it 44
items early, silently. Detected by its exact, literal text and skipped
outright, rather than counted as the table's end.
"""

import re

import canon
from parse_spells_en import _dehyphenate_numbered

TABLE_HEADER = ["Item", "Weight", "Cost"]
SECTION_HEAD = "Adventuring Gear"

_WEIGHT_RE = re.compile(r"^[\d½¼/.\s]+lb\.?(?:\s*\(full\))?$|^—$|^Varies$")
_COST_RE = re.compile(r"^[\d,]+\s*(?:CP|SP|EP|GP|PP)$|^Varies$")


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
        anomalies.append({"page": 0, "line": 0, "detail": "Adventuring Gear table header not found"})
        return gear, anomalies

    i = start
    while i < len(stripped) and not stripped[i]:
        i += 1

    while i < len(stripped):
        if stripped[i : i + 3] == TABLE_HEADER:
            # The column header reappears mid-table -- see module docstring.
            i += 3
            if i < len(stripped) and not stripped[i]:
                i += 1
            continue

        name = stripped[i]
        weight = stripped[i + 1] if i + 1 < len(stripped) else ""
        cost = stripped[i + 2] if i + 2 < len(stripped) else ""
        if not name or not _WEIGHT_RE.match(weight) or not _COST_RE.match(cost):
            break

        gear.append({"name": name, "weight": weight, "cost": cost, "page": page_at(i)})
        i += 3
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
