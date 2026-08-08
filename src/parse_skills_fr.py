"""Skill table parser for the French SRD 5.2.1.

CALIBRATED against the pinned FR PDF on 2026-08-08, the "Compétences" table
("Comment jouer", p.9). All 18 SRD skills, 0 anomalies.

The shape is the English one -- Name / Ability / Example Uses, one field per
line, rows separated by blank lines, the second line drawn from a closed set
of six ability names -- and the two real differences are both French's own:

  * **The split is 14/4, not 7/11.** The same columns_of() displacement that
    breaks the English table into two runs breaks this one differently,
    because French skill names are longer and the printed column is wider.
    The parser does not care where the header lands; it is recorded because
    the number changing is not evidence of a parse failure.
  * **French wraps mid-word, and the SRD's own layout hyphenates it.**
    "déduire le fonction-" / "nement des choses" is one word split by the
    typesetter, and four of the eighteen Example Uses cells wrap at all
    (English's longest fits on one line every time). `_dehyphenate_numbered`
    from the FR spell grammar already merges these; without it the exported
    text would read "fonction- nement", complete-looking and wrong.

ALPHABETICAL ORDER IS FRENCH'S, NOT ENGLISH'S, and the two do not correspond:
"Discrétion" (Stealth) sits fourth in the French table and fifteenth in the
English one. That is not a discrepancy to reconcile -- it is why this
repository does not pretend `srd:skill:fr:discretion` and `srd:skill:en:stealth`
are the same record (see the README's note on the absent `translation_of`
edge). Both files are sorted by their own slug.

`ability_key` uses the abbreviations the French stat blocks already use --
`for`, `sag` -- not `str`, `wis`. The FR monster export keys its ability
scores that way because the French PDF prints "For" and "Sag"; a skill that
keyed them in English would be the only French record in the base that needs
a translation table to join.
"""

import canon
from parse_spells import _dehyphenate_numbered

# The six abilities as the "Compétences" table spells them, mapped to the
# abbreviation the French stat blocks use (parse_monsters_fr.ABILITIES).
ABILITIES = {
    "Force": "for",
    "Dextérité": "dex",
    "Constitution": "con",
    "Intelligence": "int",
    "Sagesse": "sag",
    "Charisme": "cha",
}

TABLE_HEADER = ["Compétence", "Caractéristique", "Exemples d’application"]

EXPECTED_SKILLS = 18


def _find_seq(stripped, seq):
    for i in range(len(stripped) - len(seq) + 1):
        if all(stripped[i + k] == seq[k] for k in range(len(seq))):
            return i
    return None


def _groups(stripped, page_of, lo, hi):
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
        return [], [{"page": 0, "line": 0,
                     "detail": "table « Compétences » : en-tête introuvable"}]

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
                 "detail": "compétence %r : caractéristique %r sans ligne d'exemples"
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
             "detail": "table « Compétences » : %d lignes lues, %d attendues"
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
