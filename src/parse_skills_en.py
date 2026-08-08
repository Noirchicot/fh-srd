"""Skill table parser for the English SRD 5.2.1.

CALIBRATED against the pinned EN PDF on 2026-08-08, the Skills table
("Playing the Game", p.9). All 18 SRD skills, 0 anomalies.

WHY THIS PARSER EXISTS AT ALL, since the catalogue already had twelve kinds:
the 18 skills were in NONE of them. Verified before writing a line of code --
nothing for athletics, stealth, persuasion or arcana in any language; the one
hit for "perception" was the *concept* of Passive Perception in the Rules
Glossary, not the skill. Every class record says "Choose 2: Animal Handling,
Athletics, Intimidation, Nature, Perception, or Survival" as raw source text,
and no record anywhere said what Athletics is or which ability it uses. So a
character could not pick a skill from data.

THE TABLE IS ROW-COHERENT AND ITS ROWS ARE BLANK-LINE SEPARATED, the same
shape already found for Weapons and the class progression tables: each row is
Name / Ability / Example Uses, one field per line, with Example Uses wrapping
freely. What is NOT reliable is the order, and it is worth naming because it
looks like corruption and is not: extract.py's columns_of() reads the wide
table as spanning blocks first and the narrow ones after, so the printed
alphabetical order comes back split into two runs (Acrobatics...Sleight of
Hand, then Deception...Survival) with the table's own header sitting BETWEEN
them. Nothing is lost and no row is interleaved -- only the sequence moves.
Records are emitted sorted by slug anyway, so the exported file is in true
alphabetical order regardless.

THE FIELD BOUNDARY IS A CLOSED SET, not a shape guess. Example Uses has no
delimiter and wraps; a row is recognised by its SECOND line being one of the
six ability names, exactly the trick the Weapons parser uses with its eight
Mastery words. Six words, enumerable, and they are the same six the monster
stat blocks already key their ability scores by -- which is why `ability_key`
below is `dex`/`wis`, not an invented code: it is the PDF's own abbreviation,
lowercased, so a skill and a monster's ability scores join without a mapping
table living in the consumer.

SCOPE, DELIBERATE: the table is confined to one page and the parser says so.
Restricting the scan to the page carrying the header is a calibration fact
(measured: p.9, both languages), not a shortcut -- an ability name on line 2
of a three-line group is a cheap pattern that would certainly fire somewhere
in 364 pages of monsters if it were allowed to roam. The record count is
asserted against the header's own promise instead of being trusted.
"""

import canon
from parse_spells_en import _dehyphenate_numbered

# The six abilities, spelled as the Skills table spells them, mapped to the
# abbreviation the SRD's own stat blocks use (parse_monsters_en.ABILITIES).
# Both spellings come from the same PDF; nothing here is transliterated.
ABILITIES = {
    "Strength": "str",
    "Dexterity": "dex",
    "Constitution": "con",
    "Intelligence": "int",
    "Wisdom": "wis",
    "Charisma": "cha",
}

TABLE_HEADER = ["Skill", "Ability", "Example Uses"]

# The SRD's own count. Asserted, not assumed: a table that comes back with 17
# rows because one wrapped oddly is exactly the failure that would ship a
# builder unable to offer Survival.
EXPECTED_SKILLS = 18


def _find_seq(stripped, seq):
    for i in range(len(stripped) - len(seq) + 1):
        if all(stripped[i + k] == seq[k] for k in range(len(seq))):
            return i
    return None


def _groups(stripped, page_of, lo, hi):
    """Blank-line-separated groups of (page, [lines]) within [lo, hi)."""
    out, cur, start = [], [], None
    for i in range(lo, hi):
        if stripped[i]:
            if not cur:
                start = i
            cur.append(stripped[i])
        elif cur:
            out.append((page_of[start], cur))
            cur = []
    if cur:
        out.append((page_of[start], cur))
    return out


def parse_stream(lines, page_of):
    stripped = [l.strip() for l in lines]
    header = _find_seq(stripped, TABLE_HEADER)
    if header is None:
        return [], [{"page": 0, "line": 0, "detail": "Skills table header not found"}]

    page = page_of[header]
    lo = next(i for i in range(len(page_of)) if page_of[i] == page)
    hi = next((i for i in range(lo, len(page_of)) if page_of[i] != page), len(page_of))

    skills, anomalies = [], []
    for pno, group in _groups(stripped, page_of, lo, hi):
        if len(group) < 2 or group[1] not in ABILITIES:
            continue
        if len(group) < 3:
            anomalies.append(
                {"page": pno, "line": 0,
                 "detail": "skill %r: ability %r with no Example Uses line"
                           % (group[0], group[1])}
            )
            continue
        skills.append(
            {
                "name": group[0],
                "ability": group[1],
                "ability_key": ABILITIES[group[1]],
                "example_uses": " ".join(group[2:]).strip(),
                "page": pno,
            }
        )

    if len(skills) != EXPECTED_SKILLS:
        anomalies.append(
            {"page": page, "line": header,
             "detail": "Skills table yielded %d rows, expected %d"
                       % (len(skills), EXPECTED_SKILLS)}
        )
    return skills, anomalies


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

    skills, conflicts = [], []
    for skill in found:
        if skill["page"] in suspect:
            conflicts.append(
                {"page": skill["page"], "name": skill["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            skills.append(skill)

    skills.sort(key=lambda s: canon.slugify(s["name"]))
    return skills, anomalies, conflicts
