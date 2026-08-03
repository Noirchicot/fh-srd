"""Background parser for the English SRD 5.2.1.

CALIBRATED against the pinned EN PDF on 2026-08-03, "Character Backgrounds"
(p.82-83). The SRD 5.2.1 subset carries only four: Acolyte, Criminal, Sage,
Soldier -- matching the standing expectation (ATTRIBUTION.md) that the 2024
books' fuller background list is mostly outside the SRD grant. There is
nothing in this document to diff the missing ones against, the same position
already taken for feats: an importer that reads only the SRD PDF has no
`not-in-srd` exclusion to produce, because the PDF simply does not contain
the excluded content. That bookkeeping belongs to whoever cross-references a
fuller rulebook against this base.

Grammar is the simplest of this round's three: a name line, then exactly
five colon-labelled fields in a FIXED order -- Ability Scores, Feat, Skill
Proficiencies, Tool Proficiency, Equipment -- with no free-standing
description paragraph after them (unlike a spell, item or feat, a background
entry in the SRD IS its stat block; there is no prose tail). Confirmed by
reading all four entries in full: Equipment ends and the next background's
name starts on the very next non-blank line.

Two fields are decomposed rather than kept as raw source text, because both
are UNCONDITIONAL grants with a fixed, known count -- not a "choose N from
this list" clause the way a class's skill proficiencies are:

  * `ability_scores` -- always exactly three, comma-separated, no "or"
    anywhere in the four entries. "Parts of a Background" (the section
    intro, not per-entry text) confirms the rule: you get all three, only
    which gets +2 vs +1 is your choice.
  * `skill_proficiencies` -- always exactly two, joined by "and", never "or".

`feat`, `tool_proficiency` and `equipment` stay raw source text: `feat`
because "Magic Initiate (Cleric)" is a cross-reference into the feat catalogue
best left for a consumer to resolve, not this importer to link; `equipment`
because it is a "Choose A or B" clause exactly like a class's starting
equipment, and forcing it into a list would fabricate structure the source
does not commit to (the same call already made for a magic item's rarity
clause and a spell's components).

Reused unchanged from the class/species/feat family: continuous-stream
parsing, the page-transition-closes-a-field guard (defensive here even
though no observed background actually straddles a page break in the pinned
PDF -- the whole chapter fits in under two pages -- because a parser that
only guards against traps it has already been bitten by is one bug away from
being bitten again), and the discipline that an unparsed block becomes an
exclusion, never a half-filled record.
"""

import re

import canon
from parse_spells_en import _dehyphenate_numbered

NAMES = ["Acolyte", "Criminal", "Sage", "Soldier"]

FIELDS = [
    ("ability_scores_raw", re.compile(r"^Ability Scores:\s*(.+)$")),
    ("feat", re.compile(r"^Feat:\s*(.+)$")),
    ("skill_proficiencies_raw", re.compile(r"^Skill Proficiencies:\s*(.+)$")),
    ("tool_proficiency", re.compile(r"^Tool Proficiency:\s*(.+)$")),
    ("equipment", re.compile(r"^Equipment:\s*(.+)$")),
]

CHAPTER_START = "Background Descriptions"
CHAPTER_END = "Character Species"


def parse_stream(text, page_of):
    lines = [l.strip("\n") for l in text.split("\n")]
    backgrounds, anomalies = [], []

    def page_at(i):
        return page_of[i] if i < len(page_of) else (page_of[-1] if page_of else 0)

    stripped = [l.strip() for l in lines]

    chapter_start = 0
    for i, l in enumerate(stripped):
        if l == CHAPTER_START:
            chapter_start = i
            break

    chapter_end = len(lines)
    for i, l in enumerate(stripped):
        if i > chapter_start and l == CHAPTER_END:
            chapter_end = i
            break

    # A background's name is a bare line matching one of the four known
    # names in this SRD subset. Unlike a spell's "Level N" or an item's
    # category word, a bare "Acolyte" or "Sage" could plausibly appear in
    # running prose elsewhere in the document -- so, like magic items and
    # feats, the chapter is bounded explicitly rather than trusted to the
    # name list alone, and matching is restricted to inside that bound.
    heads = [
        i for i, l in enumerate(stripped)
        if chapter_start < i < chapter_end and l in NAMES
        # A real head is immediately followed by "Ability Scores:" -- the
        # name mentioned in passing ("...as detailed for the Acolyte
        # background") would not be.
        and i + 1 < len(stripped) and stripped[i + 1].startswith("Ability Scores:")
    ]
    next_head = {}
    for position, index in enumerate(heads):
        following = heads[position + 1] if position + 1 < len(heads) else chapter_end
        next_head[index] = min(following, chapter_end)

    heads_set = set(heads)
    for idx, line in enumerate(stripped):
        if idx not in heads_set:
            continue
        name = line

        stats = {}
        limit = next_head.get(idx, chapter_end)
        i = idx + 1
        current = None
        while i < limit:
            # Same guard as the spell/item/feat parsers: a page transition,
            # once every field is already found, is at least as strong a
            # separator as the blank line the text does not actually have at
            # a page seam.
            if current and i > 0 and page_of[i] != page_of[i - 1]:
                if len(stats) == len(FIELDS):
                    break
                current = None
            wline = stripped[i]
            matched = None
            for key, pattern in FIELDS:
                m = pattern.match(wline)
                if m:
                    matched = key
                    stats[key] = m.group(1).strip()
                    current = key
                    break
            if matched:
                i += 1
                continue
            if not wline:
                if len(stats) == len(FIELDS):
                    i += 1
                    break
                current = None
                i += 1
                continue
            if current:
                stats[current] = (stats[current] + " " + wline).strip()
            i += 1

        missing = [key for key, _ in FIELDS if key not in stats]
        if missing:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "background %r missing field(s): %s"
                           % (name, ", ".join(missing))}
            )
            continue

        ability_scores = [
            s.strip() for s in stats["ability_scores_raw"].split(",") if s.strip()
        ]
        if len(ability_scores) != 3:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "background %r has %d ability score(s), expected 3: %r"
                           % (name, len(ability_scores), stats["ability_scores_raw"])}
            )
            continue

        skill_proficiencies = [
            s.strip() for s in re.split(r"\s+and\s+", stats["skill_proficiencies_raw"])
            if s.strip()
        ]
        if len(skill_proficiencies) != 2:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "background %r has %d skill proficiency(ies), expected 2: %r"
                           % (name, len(skill_proficiencies), stats["skill_proficiencies_raw"])}
            )
            continue

        backgrounds.append(
            {
                "name": name,
                "ability_scores": ability_scores,
                "feat": stats["feat"],
                "skill_proficiencies": skill_proficiencies,
                "tool_proficiency": stats["tool_proficiency"],
                "equipment": stats["equipment"],
                "page": page_at(idx),
            }
        )

    return backgrounds, anomalies


def parse(pages, suspect_pages=()):
    suspect = set(suspect_pages)

    numbered = []
    for number, raw in enumerate(pages, start=1):
        for line in raw.split("\n"):
            numbered.append((number, line))

    numbered = _dehyphenate_numbered(numbered)

    stream = "\n".join(l for _, l in numbered)
    page_of = [n for n, _ in numbered]

    found, anomalies = parse_stream(stream, page_of)

    backgrounds, conflicts = [], []
    for bg in found:
        if bg["page"] in suspect:
            conflicts.append(
                {"page": bg["page"], "name": bg["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            backgrounds.append(bg)

    backgrounds.sort(key=lambda b: canon.slugify(b["name"]))
    return backgrounds, anomalies, conflicts
