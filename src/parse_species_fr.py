"""Species parser for the French SRD 5.2.1.

CALIBRATED against the pinned FR PDF on 2026-08-03, "Description des
espèces" (p.88-91, inside "Origines des personnages" p.87-91). The SRD 5.2.1
subset carries exactly nine, the same nine EN has: Drakéide (Dragonborn),
Elfe (Elf), Gnome (Gnome), Goliath (Goliath), Halfelin (Halfling), Humain
(Human), Nain (Dwarf), Orc (Orc), Tieffelin (Tiefling).

Grammar ported from `parse_species_en.py`: a bare name line (one of the
nine, immediately followed by "Type de créature :" -- the same
false-positive guard EN uses, since a species name can plausibly appear in
running prose), then three colon-labelled fields in a fixed order --
**"Type de créature :", "Catégorie de taille :", "Vitesse :"** (not "Cat.
de taille :", the abbreviated form the section's own INTRO prose uses two
paragraphs earlier for "Cat. de taille" as a sub-heading; every actual
per-entry field line spells it out in full) -- then free-form description
text running to the next species name or the chapter boundary. Size wraps
across two lines for several entries (Elfe: "M (moyenne, entre 1,50 m et\\n
1,80 m)"; Humain and Tieffelin both offer a Medium-or-Small choice that
runs onto a third line), the same wrap already handled by the field-value
continuation loop.

THE SAME EMBEDDED-TABLE MISORDERING EN'S PARSER DOCUMENTS ALSO REPRODUCES
IN FRENCH, unsurprisingly since it is a PyMuPDF column-reading artefact of
the page geometry, not a language-specific one: "Lignages elfiques" and
"Héritages fiélons" (Elfe and Tieffelin's own lineage/legacy tables) are
wide, multi-column tables whose cells are read out of visual order and can
be emitted BEFORE the species' own name/head line that visually precedes
them on the page (confirmed reading the raw stream: "Elfe\\nType de
créature : Humanoïde..." is found correctly in sequence, but the "Lignages
elfiques" table content that visually follows it on the page appears
earlier in the extracted stream, ahead of it). Swept into `description` as
prose, the same deliberate, named limitation as EN -- not attempted here
either.

CHAPTER_START = "Description des espèces" (single literal occurrence,
p.88, distinguishing the nine entries from the section's own earlier
explanatory prose "Type de créature" / "Cat. de taille" / "Vitesse" /
"Traits spéciaux" sub-headings). CHAPTER_END = "Dons", the next chapter,
single literal occurrence (p.92).
"""

import re

import canon
from parse_spells import _dehyphenate_numbered

SPECIES = [
    "Drakéide", "Elfe", "Gnome", "Goliath", "Halfelin",
    "Humain", "Nain", "Orc", "Tieffelin",
]

FIELDS = [
    ("creature_type", re.compile(r"^Type de créature\s*:\s*(.+)$")),
    ("size", re.compile(r"^Catégorie de taille\s*:\s*(.+)$")),
    ("speed", re.compile(r"^Vitesse\s*:\s*(.+)$")),
]

CHAPTER_START = "Description des espèces"
CHAPTER_END = "Dons"


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
        and i + 1 < len(stripped) and stripped[i + 1].startswith("Type de créature")
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

        # UNLIKE a spell/item/feat head, this head IS the name line itself
        # -- `next_head` already points at the NEXT species' own name line,
        # so no "trim the next entry's name" step is needed or wanted (see
        # parse_species_en.py's own docstring for the bug this would
        # otherwise reproduce: cutting the last sentence of every
        # description but the last).
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
                 "detail": "species %r has Type de créature/Catégorie de taille/Vitesse "
                           "but no description text" % name}
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
