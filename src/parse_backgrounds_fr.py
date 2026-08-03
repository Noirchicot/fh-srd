"""Background parser for the French SRD 5.2.1.

CALIBRATED against the pinned FR PDF on 2026-08-03, "Description des
historiques" (p.87, inside "Origines des personnages" p.87-91). Ported from
`parse_backgrounds_en.py`: same five colon-labelled fields in the same
FIXED order, no free-standing description paragraph after them -- a
background entry in the SRD IS its stat block here too, in both languages.

FIELD LABELS, confirmed by reading all four entries end to end rather than
assumed by translating EN's: "Valeurs de caractéristique :" (Ability
Scores), "Don :" (Feat), "Maîtrises de compétence :" (Skill Proficiencies
-- PLURAL "Maîtrises"), "Maîtrise d'outils :" (Tool Proficiency -- SINGULAR
"Maîtrise", a different word from the previous field despite sharing the
same root; the two must not be matched by one shared prefix), "Équipement :"
(Equipment). Same fixed order EN uses.

`skill_proficiencies` splits on " et " (French "and") rather than EN's
" and "; checked on all four entries, never "ou" (or) -- these are
unconditional grants, the same call already made for EN.

CHAPTER_START = "Description des historiques" (a literal heading directly
above "Acolyte", distinguishing this from the section's own earlier
"Historiques de personnage" title, which precedes explanatory prose, not
the four entries themselves). CHAPTER_END = "Espèces des personnages", the
next section heading, single literal occurrence right after Soldat's own
Equipment field ends.
"""

import re

import canon
from parse_spells import _dehyphenate_numbered

NAMES = ["Acolyte", "Criminel", "Sage", "Soldat"]

FIELDS = [
    ("ability_scores_raw", re.compile(r"^Valeurs de caractéristique\s*:\s*(.+)$")),
    ("feat", re.compile(r"^Don\s*:\s*(.+)$")),
    ("skill_proficiencies_raw", re.compile(r"^Maîtrises de compétence\s*:\s*(.+)$")),
    ("tool_proficiency", re.compile(r"^Maîtrise d[’']outils\s*:\s*(.+)$")),
    ("equipment", re.compile(r"^Équipement\s*:\s*(.+)$")),
]

CHAPTER_START = "Description des historiques"
CHAPTER_END = "Espèces des personnages"


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

    heads = [
        i for i, l in enumerate(stripped)
        if chapter_start < i < chapter_end and l in NAMES
        and i + 1 < len(stripped) and stripped[i + 1].startswith("Valeurs de caractéristique")
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
            s.strip() for s in re.split(r"\s+et\s+", stats["skill_proficiencies_raw"])
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
