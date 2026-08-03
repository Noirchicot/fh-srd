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

THE SAME CATEGORY LIMITATION AS WEAPONS, same root cause: "Light Armor (1
Minute to Don or Doff)," "Medium Armor (5 Minutes to Don and 1 Minute to
Doff)," "Heavy Armor (10 Minutes to Don and 5 Minutes to Doff)," and
"Shield (Utilize Action to Don or Doff)" are real text in the source, but
are narrow one-line blocks that extract.py's columns_of() buckets as
ordinary left-column text rather than the wide "spanning" rows the table's
own data occupies -- displaced as a group to the end of the page, in their
own correct relative order, with nothing left behind linking them back to
which rows they introduced. Not re-derived by guessing (unlike the
Weapons table, this one is arguably guessable from the AC column's shape --
Light armor's AC is "11-12 + Dex modifier" with no cap, Medium is "+ Dex
modifier (max 2)," Heavy is a flat number, Shield is "+2" -- but a
guessed rule is still a guess, and the source's own words for it were not
used).
"""

import re

import canon
from parse_spells_en import _dehyphenate_numbered

TABLE_HEADER = ["Armor", "Armor Class (AC)", "Strength", "Stealth", "Weight", "Cost"]

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

    while i + 5 < len(stripped) and _AC_RE.match(stripped[i + 1]):
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

        armors.append(
            {
                "name": name,
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
