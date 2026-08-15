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

CATEGORY IS NOW CAPTURED, as of the fix below -- and it is CAPTURED, not
re-derived. Before the two-column repair of 2026-08-08 the table's own
sub-category labels ("Simple Melee Weapons," "Simple Ranged Weapons,"
"Martial Melee Weapons," "Martial Ranged Weapons") reached this parser
displaced as a group to the end of their page, with no marker left behind to
say which rows they used to introduce -- extract.py's old columns_of()
classified a block by width alone, and the four narrow one-line labels fell
under the 0.7 span-ratio threshold that every wide table row cleared. The
repair put them back where they are printed: between the rows they
introduce. `table_sections.skip_subheading` still steps over each one so it
is never mistaken for a row, but this parser now reads the label's text
BEFORE stepping over it and carries it onto every row that follows, until
the next label changes it. Two fields, not one composite string
("martial-melee"): a consumer commonly filters on only one of the two
dimensions, and a composite would have to be split back apart on every use.

Re-deriving the category from row CONTENT instead of the label was
considered and rejected as a guess, same as before: the "Thrown" property
does not distinguish Melee from Ranged the way it looks like it should --
Javelin (Thrown, Simple MELEE) and Dart (Thrown, Simple RANGED) both carry
the same property, differing only in a classification the source states
nowhere in the row itself. Only the label the source prints above the row
is trustworthy.

VERIFIED against the pinned EN PDF, p.91, read by hand line by line: the
four labels are a closed set (CATEGORY_LABELS below), and the rows between
them count 10 Simple Melee, 4 Simple Ranged, 18 Martial Melee, 6 Martial
Ranged -- 38 in total, the same 38 this parser already produced. An
unrecognised label text stops the parser with an anomaly rather than
silently leaving a row uncategorised; a row that somehow reaches this parser
before any label has been seen does the same. Neither happens on the real,
complete table -- the first line after the header is always a label -- so
both guards are defensive, never expected to fire against a real page.

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

# The table's own four sub-category labels, exactly as printed on p.91, mapped
# to the two independent facts they state. A closed set -- the SRD prints
# exactly these four and no others (verified against the pinned PDF) -- so an
# unrecognised label is an extraction defect, not a fifth category to guess at.
CATEGORY_LABELS = {
    "Simple Melee Weapons": ("simple", "melee"),
    "Simple Ranged Weapons": ("simple", "ranged"),
    "Martial Melee Weapons": ("martial", "melee"),
    "Martial Ranged Weapons": ("martial", "ranged"),
}

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

    category = weapon_range = None
    while i < len(stripped):
        name = stripped[i]
        if not name or not _DAMAGE_RE.match(stripped[i + 1] if i + 1 < len(stripped) else ""):
            # The table's own sub-category label ("Simple Melee Weapons"), which
            # reaches this parser in its printed position since the two-column
            # extraction was repaired. `name` still holds the label's own text
            # here, one line before it is overwritten by the row that follows
            # it -- captured into (category, weapon_range) rather than merely
            # stepped over, so every row below carries what the table itself
            # says about it. If it is not a label the table's own row test
            # recognises, the table has ended and we stop as before.
            resumed = skip_subheading(stripped, i, starts_row)
            if resumed is None:
                break
            if name not in CATEGORY_LABELS:
                anomalies.append(
                    {"page": page_at(i), "line": i,
                     "detail": "weapon table sub-category label %r is not one "
                               "of the four the SRD prints (%s)"
                               % (name, ", ".join(sorted(CATEGORY_LABELS)))}
                )
                return weapons, anomalies
            category, weapon_range = CATEGORY_LABELS[name]
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

        if category is None:
            # Never observed against a real, complete table -- the first line
            # after the header is always a label -- but a row must not ship
            # with a guessed or absent category if a future source ever
            # reorders one.
            anomalies.append(
                {"page": page_at(row_start), "line": row_start,
                 "detail": "weapon %r appears before any sub-category label; "
                           "its category cannot be read" % name}
            )
            return weapons, anomalies

        properties = " ".join(properties_lines).strip()
        weapons.append(
            {
                "name": name,
                "damage": damage,
                "properties": None if properties in ("", "—") else properties,
                "mastery": mastery,
                "weight": weight,
                "cost": cost,
                "weapon_category": category,
                "weapon_range": weapon_range,
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
