"""Species parser for the English SRD 5.2.1.

CALIBRATED against the pinned EN PDF on 2026-08-03, "Character Species"
(p.83-86, "Species Descriptions" p.83). The SRD 5.2.1 subset carries exactly
nine: Dragonborn, Dwarf, Elf, Gnome, Goliath, Halfling, Human, Orc, Tiefling.

WHAT IS NOT HERE, AND WHY THAT NEEDS SAYING RATHER THAN JUST BEING TRUE:
Aasimar, Half-Elf, Half-Orc and Eladrin do not appear anywhere in this
chapter -- there is no `not-in-srd` exclusion for them to produce, the same
position already taken for feats and backgrounds: an importer reading only
the SRD PDF has nothing to diff the missing content against, because the PDF
simply does not contain it. That bookkeeping is for whoever cross-references
a fuller rulebook against this base.

DROW IS A DIFFERENT CASE AND WORTH FLAGGING SEPARATELY: the word is not
absent. It appears, licensed and verbatim, inside the Elf entry's "Elven
Lineages" table as one of three lineage FLAVOURS a player picks when they
choose Elf (High Elf, Drow, Wood Elf) -- not as a standalone species with its
own Creature Type / Size / Speed the way Forgotten Realms sourcebooks present
it. tripwire.py does not flag "Drow" (only aasimar/eladrin/half-elf/half-orc
are listed there) precisely because this usage is legitimate SRD text, not a
product-identity leak. A standalone "Drow" SPECIES record is still
not-in-srd; the word appearing inside Elf's own licensed description is not
the same claim and this parser does not manufacture a species that the
source does not present as one.

Grammar: a bare name line (one of the nine, immediately followed by
"Creature Type:" -- the same false-positive guard used for backgrounds,
since a species name can plausibly appear in running prose, e.g. a
cross-reference), then three colon-labelled fields in a fixed order
(Creature Type, Size, Speed -- Size sometimes wraps: Human's and Tiefling's
read "Medium (...) or Small (...), chosen when you select this species"
across two lines), then free-form description text running to the next
species name or the chapter boundary.

EMBEDDED CHOICE TABLES ARE SWEPT INTO `description` AS PROSE, NOT DECOMPOSED
-- the same call already made for a magic item's random tables and a spell's
embedded companion stat block. Four species (Dragonborn's Draconic
Ancestors, Elf's Elven Lineages, Gnome's Gnomish Lineage, Goliath's Giant
Ancestry, Tiefling's Fiendish Legacies) present a table or list of named
sub-choices. Two of those -- Elf and Tiefling -- are genuine multi-column
PDF tables (Lineage / Level 1 / Level 3 / Level 5), and PyMuPDF's column
reading order reassembles them in an order that does NOT match the visual
table: "Drow" and "Wood Elf"'s cells (a later table column) are emitted
BEFORE the "Elven Lineages" heading and the "High Elf" row that visually
precede them on the page. This is the same known, VISIBLE limitation named
for magic items' embedded random tables -- not a silent one, and named again
here because a class's subclass features (a separate grammar in this same
round) turned out to have no equivalent table trap, so it is species-
specific and worth a fresh reader's attention rather than assuming a
sibling parser's docstring covers it.
"""

import re

import canon
from parse_spells_en import _dehyphenate_numbered

SPECIES = [
    "Dragonborn", "Dwarf", "Elf", "Gnome", "Goliath",
    "Halfling", "Human", "Orc", "Tiefling",
]

FIELDS = [
    ("creature_type", re.compile(r"^Creature Type:\s*(.+)$")),
    ("size", re.compile(r"^Size:\s*(.+)$")),
    ("speed", re.compile(r"^Speed:\s*(.+)$")),
]

CHAPTER_START = "Species Descriptions"
CHAPTER_END = "Feats"


def parse_stream(text, page_of):
    lines = [l.strip("\n") for l in text.split("\n")]
    species, anomalies = [], []

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

    heads = [
        i for i, l in enumerate(stripped)
        if chapter_start < i < chapter_end and l in SPECIES
        and i + 1 < len(stripped) and stripped[i + 1].startswith("Creature Type:")
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
                 "detail": "species %r missing field(s): %s"
                           % (name, ", ".join(missing))}
            )
            continue

        # UNLIKE a spell/item/feat head, this head IS the name line itself --
        # there is no separate name line living ABOVE a stat line that could
        # leak into the slice below and need trimming. `next_head` already
        # points at the NEXT species' own name line, so slicing up to it
        # (exclusive) already excludes that name with nothing left over.
        # Copying the sibling parsers' "trim one extra line for the next
        # entry's name" step here would cut the last sentence of every
        # description that has a following entry -- measured: it did, on 8
        # of 9 species, all but the last (Tiefling, which has no next head to
        # trim against and so was the only one that came out complete).
        desc_end = next_head.get(idx, chapter_end)
        desc_lines = stripped[i:desc_end]
        end = len(desc_lines)
        while end > 0 and not desc_lines[end - 1]:
            end -= 1
        desc_lines = desc_lines[:end]
        paragraphs = []
        for chunk in "\n".join(desc_lines).split("\n\n"):
            joined = " ".join(l for l in chunk.split("\n") if l)
            if joined:
                paragraphs.append(joined)
        description = "\n\n".join(paragraphs)

        if not description:
            anomalies.append(
                {"page": page_at(idx), "line": idx,
                 "detail": "species %r has Creature Type/Size/Speed but no description text" % name}
            )
            continue

        species.append(
            {
                "name": name,
                "creature_type": stats["creature_type"],
                "size": stats["size"],
                "speed": stats["speed"],
                "description": description,
                "page": page_at(idx),
            }
        )

    return species, anomalies


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

    species, conflicts = [], []
    for sp in found:
        if sp["page"] in suspect:
            conflicts.append(
                {"page": sp["page"], "name": sp["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            species.append(sp)

    species.sort(key=lambda s: canon.slugify(s["name"]))
    return species, anomalies, conflicts
