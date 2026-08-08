"""Weapon table parser for the English SRD 5.2.1.

CALIBRATED against the pinned EN PDF on 2026-08-03, the Weapons table
(p.91, inside the "Equipment" chapter, p.89-103). 38 weapons, 0 anomalies.

THE VERDICT ON THE MULTI-COLUMN TABLE QUESTION THIS LOT WAS ASKED TO SETTLE:
this table IS row-coherent in the extracted text, the same finding already
made for the class level-progression table and NOT the case for a magic
item's embedded random tables. Confirmed by reading raw PyMuPDF block
coordinates directly (not just the normalised text extract.py hands every
parser): every weapon row is emitted as ONE SINGLE PDF block already
containing Name/Damage/Properties/Mastery/Weight/Cost in the correct order,
because the table is wide enough (about 83% of the page width) to be read
as a single unbroken span rather than split into two interleaved columns --
the trap that corrupted spell reading order on other pages. So the row data
itself needs no geometry fix, only a field-boundary rule (see below).

WHAT IS DELIBERATELY NOT CAPTURED, measured rather than assumed: the
table's own sub-category labels ("Simple Melee Weapons," "Simple Ranged
Weapons," "Martial Melee Weapons," "Martial Ranged Weapons"). These ARE
present in the source, but extract.py's columns_of() -- calibrated for the
document's ordinary two-column BODY TEXT, and correct there -- classifies
a block by width alone: the table's rows are wide enough to count as
"spanning" and are sorted purely by y-position (preserving correct order),
but the four narrow one-line category headers fall under the 0.7 span-ratio
threshold and get bucketed as ordinary left-column text instead, which is
sorted AFTER every spanning block on the page. The result: all four labels
survive in the extracted text, in their own correct relative order, but
displaced as a group to the very end of the page, with no marker left
behind to say which rows they used to introduce.

Re-deriving the category from row CONTENT was tried and rejected as a
guess: the "Thrown" property does not distinguish Melee from Ranged the way
it looks like it should -- Javelin (Thrown, Simple MELEE) and Dart (Thrown,
Simple RANGED) both carry the same property, differing only in a
classification the source states nowhere in the row itself. Recovering the
true category would require re-reading the PDF's block geometry directly
for this one table (bypassing the shared columns_of() heuristic, which
exists for body text and is calibrated against it, not against a 6-column
table) -- a legitimate fix, but a different, targeted piece of work from
this pass, not attempted here rather than guessed.

FIELD BOUNDARIES: Name and Damage are always exactly one line each.
Properties WRAPS across more than one physical line for four of the 38
weapons (every Ammunition weapon whose range note pushes the line past its
width: Light Crossbow, Heavy Crossbow, Longbow, Musket) with no delimiter
marking where it ends. Mastery does not have this problem: it is always
exactly one of eight fixed words (Cleave, Graze, Nick, Push, Sap, Slow,
Topple, Vex; verified against the "Mastery Properties" section's own eight
definitions two pages earlier), so Properties is read as "every line up to
the first line that IS one of those eight words" -- a closed, exhaustively
enumerable set, not a pattern guessed from shape.
"""

import re

import canon
from parse_spells_en import _dehyphenate_numbered
from table_sections import skip_subheading

MASTERY_PROPERTIES = {
    "Cleave", "Graze", "Nick", "Push", "Sap", "Slow", "Topple", "Vex",
}

TABLE_HEADER = ["Name", "Damage", "Properties", "Mastery", "Weight", "Cost"]

_DAMAGE_RE = re.compile(r"^\d+d\d+(?:\s*\+\s*\d+)?\s+\S+$|^1\s+\S+$")
_WEIGHT_RE = re.compile(r"^[\d½¼/.\s]+lb\.?$|^—$")
_COST_RE = re.compile(r"^[\d,]+\s*(?:CP|SP|EP|GP|PP)$")

CHAPTER_START = "Equipment"


def _find_seq(stripped, seq, after=0):
    for i in range(after, len(stripped) - len(seq) + 1):
        if all(stripped[i + k] == seq[k] for k in range(len(seq))):
            return i
    return None


def parse_stream(lines, page_of):
    stripped = [l.strip() for l in lines]

    def page_at(i):
        return page_of[i] if i < len(page_of) else (page_of[-1] if page_of else 0)

    header = _find_seq(stripped, TABLE_HEADER)
    weapons, anomalies = [], []
    if header is None:
        anomalies.append({"page": 0, "line": 0, "detail": "Weapons table header not found"})
        return weapons, anomalies

    i = header + len(TABLE_HEADER)
    while i < len(stripped) and not stripped[i]:
        i += 1

    def starts_row(j):
        return bool(stripped[j]) and _DAMAGE_RE.match(
            stripped[j + 1] if j + 1 < len(stripped) else "") is not None

    while i < len(stripped):
        name = stripped[i]
        if not name or not _DAMAGE_RE.match(stripped[i + 1] if i + 1 < len(stripped) else ""):
            # The table's own sub-category label ("Simple Melee Weapons"), which
            # reaches this parser in its printed position since the two-column
            # extraction was repaired. Stepped over, never counted as a row --
            # and if it is not one, the table has ended and we stop as before.
            resumed = skip_subheading(stripped, i, starts_row)
            if resumed is None:
                break
            i = resumed
            name = stripped[i]
        row_start = i
        i += 1
        damage = stripped[i]
        i += 1

        properties_lines = []
        guard_start = i
        while i < len(stripped) and stripped[i] not in MASTERY_PROPERTIES:
            properties_lines.append(stripped[i])
            i += 1
            if i - guard_start > 6:
                anomalies.append(
                    {"page": page_at(row_start), "line": row_start,
                     "detail": "weapon %r: no Mastery Properties word found within 6 lines" % name}
                )
                return weapons, anomalies
        if i >= len(stripped):
            anomalies.append(
                {"page": page_at(row_start), "line": row_start,
                 "detail": "weapon %r: table ended before a Mastery value was found" % name}
            )
            break
        mastery = stripped[i]
        i += 1

        if i >= len(stripped) or not _WEIGHT_RE.match(stripped[i]):
            anomalies.append(
                {"page": page_at(row_start), "line": row_start,
                 "detail": "weapon %r: expected a weight value, found %r"
                           % (name, stripped[i] if i < len(stripped) else None)}
            )
            break
        weight = stripped[i]
        i += 1

        if i >= len(stripped) or not _COST_RE.match(stripped[i]):
            anomalies.append(
                {"page": page_at(row_start), "line": row_start,
                 "detail": "weapon %r: expected a cost value, found %r"
                           % (name, stripped[i] if i < len(stripped) else None)}
            )
            break
        cost = stripped[i]
        i += 1

        properties = " ".join(properties_lines).strip()
        weapons.append(
            {
                "name": name,
                "damage": damage,
                "properties": None if properties in ("", "—") else properties,
                "mastery": mastery,
                "weight": weight,
                "cost": cost,
                "page": page_at(row_start),
            }
        )

        if i < len(stripped) and not stripped[i]:
            i += 1

    return weapons, anomalies


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

    weapons, conflicts = [], []
    for weapon in found:
        if weapon["page"] in suspect:
            conflicts.append(
                {"page": weapon["page"], "name": weapon["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            weapons.append(weapon)

    weapons.sort(key=lambda w: canon.slugify(w["name"]))
    return weapons, anomalies, conflicts
