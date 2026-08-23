"""Armor table parser for the English SRD 5.2.1.

CALIBRATED against the pinned EN PDF on 2026-08-03, the Armor table
(p.92, inside the "Equipment" chapter, p.89-103). 13 rows (12 armors plus
the Shield), 0 anomalies.

Simpler than the Weapons table it sits right after: every field is exactly
one line for all 13 rows, no wrapping (the AC column's longest value,
"14 + Dex modifier (max 2)", still fits one physical line). Row-coherent
for the same reason the Weapons table is -- see parse_weapons_en.py's
docstring for the measured explanation (the table is wide enough to be
read as a single spanning block per row rather than split across the
document's usual two-column layout).

THE CATEGORY IS READ FROM THE TABLE'S OWN LABELS. "Light Armor (1 Minute to
Don or Doff)," "Medium Armor (5 Minutes to Don and 1 Minute to Doff),"
"Heavy Armor (10 Minutes to Don and 5 Minutes to Doff)" and "Shield
(Utilize Action to Don or Doff)" are printed above the rows they introduce,
and since the two-column extraction was repaired they reach this parser in
that printed position. They used to be swept to the end of the page as a
group, which is why every earlier version of this file said the category
could not be recovered; that sentence outlived the repair by two lots and
is corrected here.

⛔ IT IS NOT RE-DERIVED FROM THE ROWS. This table is arguably guessable from
the AC column's shape -- Light is "11-12 + Dex modifier" with no cap, Medium
carries "(max 2)," Heavy is a flat number, Shield is "+2" -- and that is
exactly the reasoning this parser refuses. A guessed rule is still a guess,
and the source prints its own words for it one line above the row.

THE DON/DOFF TEXT IS KEPT BESIDE THE CATEGORY, not inside it (Eric,
2026-08-23: the category is "light armor" and nothing more; the donning time
belongs on the sheet). Two fields from one label, because they are two facts:
`armor_category` is a key a screen filters on, `don_doff` is a sentence a
sheet prints.

⛔ `don_doff` IS NOT TYPED HERE. The shield's own text is "Utilize Action to
Don or Doff" -- not a duration at all -- so a `minutes` number would be wrong
for one of the four values on day one. Turning these into numbers plus an
action is the typed-fields work, and this is an extraction repair; what is
captured is exactly what the source prints.
"""

import re

import canon
from parse_spells_en import _dehyphenate_numbered
from table_sections import skip_subheading

TABLE_HEADER = ["Armor", "Armor Class (AC)", "Strength", "Stealth", "Weight", "Cost"]

# The table's own four sub-category labels, as printed on p.92, mapped to the
# stable key each one states. A closed set: the SRD prints exactly these four
# and no others, so an unrecognised label is an extraction defect, not a fifth
# category to guess at.
#
# ⚠️ MATCHED ON THE LEADING WORDS, not on the whole printed string, and that is
# a deliberate difference from `parse_weapons_en.CATEGORY_LABELS`. A weapon
# label is two or three plain words ("Simple Melee Weapons"); an armor label
# carries a don/doff time in a parenthesis, and the French one carries it with
# narrow no-break spaces ("s\u2019enfile ou se retire en 1\u00a0minute"). Keying on
# the whole string would make this parser fail on a punctuation change in text
# it does not even use. The set stays closed; only its fragile half is excluded
# from the match.
ARMOR_CATEGORY_LABELS = (
    (re.compile(r"^Light Armor\b"), "light"),
    (re.compile(r"^Medium Armor\b"), "medium"),
    (re.compile(r"^Heavy Armor\b"), "heavy"),
    (re.compile(r"^Shield\b"), "shield"),
)

# The rest of the label, which every one of the four carries in a parenthesis.
_DON_DOFF_RE = re.compile(r"\(([^)]*)\)\s*$")


def category_of(label):
    """The stable key a sub-category label states, or None if it states none."""
    for pattern, key in ARMOR_CATEGORY_LABELS:
        if pattern.match(label):
            return key
    return None


def don_doff_of(label):
    """What the label says about donning and doffing, as printed, or None.

    None is a real answer: a label with no parenthesis states a category and
    nothing else. It is not an empty string and not a missing time.
    """
    found = _DON_DOFF_RE.search(label)
    return found.group(1).strip() if found else None


_AC_RE = re.compile(r"^\d|^\+\d")
_WEIGHT_RE = re.compile(r"^[\d½¼/.\s]+lb\.?$|^—$")
_COST_RE = re.compile(r"^[\d,]+\s*(?:CP|SP|EP|GP|PP)$")


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
    armors, anomalies = [], []
    if header is None:
        anomalies.append({"page": 0, "line": 0, "detail": "Armor table header not found"})
        return armors, anomalies

    i = header + len(TABLE_HEADER)
    while i < len(stripped) and not stripped[i]:
        i += 1

    def starts_row(j):
        return j + 5 < len(stripped) and _AC_RE.match(stripped[j + 1]) is not None

    armor_category = armor_don_doff = None
    while i < len(stripped):
        if not starts_row(i):
            # The table's own category label ("Light Armor (1 Minute to Don or
            # Doff)"), which reaches this parser in its printed position since
            # the two-column extraction was repaired. `label` holds its text
            # here, one line before the row that follows overwrites it --
            # captured rather than merely stepped over, so every row below
            # carries what the table itself says about it. If it is not a label
            # the table's own row test recognises, the table has ended.
            label = stripped[i]
            resumed = skip_subheading(stripped, i, starts_row)
            if resumed is None:
                break
            key = category_of(label)
            if key is None:
                anomalies.append(
                    {"page": page_at(i), "line": i,
                     "detail": "armor table sub-category label %r is not one of "
                               "the four the SRD prints (Light/Medium/Heavy "
                               "Armor, Shield)" % label}
                )
                return armors, anomalies
            armor_category = key
            armor_don_doff = don_doff_of(label)
            i = resumed
        row_start = i
        name = stripped[i]
        armor_class = stripped[i + 1]
        strength = stripped[i + 2]
        stealth = stripped[i + 3]
        weight = stripped[i + 4]
        cost = stripped[i + 5]

        if not _WEIGHT_RE.match(weight):
            anomalies.append(
                {"page": page_at(row_start), "line": row_start,
                 "detail": "armor %r: expected a weight value, found %r" % (name, weight)}
            )
            break
        if not _COST_RE.match(cost):
            anomalies.append(
                {"page": page_at(row_start), "line": row_start,
                 "detail": "armor %r: expected a cost value, found %r" % (name, cost)}
            )
            break

        if armor_category is None:
            # Never seen on the real, complete table -- the first line after the
            # header is always a label -- but a row must not ship with a guessed
            # or absent category if a future printing ever reorders one.
            anomalies.append(
                {"page": page_at(row_start), "line": row_start,
                 "detail": "armor %r appears before any sub-category label; its "
                           "category cannot be read" % name}
            )
            return armors, anomalies

        armors.append(
            {
                "name": name,
                "armor_category": armor_category,
                "don_doff": armor_don_doff,
                "armor_class": armor_class,
                "strength": None if strength == "—" else strength,
                "stealth_disadvantage": stealth == "Disadvantage",
                "weight": weight,
                "cost": cost,
                "page": page_at(row_start),
            }
        )

        i += 6
        if i < len(stripped) and not stripped[i]:
            i += 1

    return armors, anomalies


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

    armors, conflicts = [], []
    for armor in found:
        if armor["page"] in suspect:
            conflicts.append(
                {"page": armor["page"], "name": armor["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            armors.append(armor)

    armors.sort(key=lambda a: canon.slugify(a["name"]))
    return armors, anomalies, conflicts
