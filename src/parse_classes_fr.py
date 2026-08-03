"""Class parser for the French SRD 5.2.1.

CALIBRATED against the pinned FR PDF on 2026-08-03, "Classes" (p.30-86).
All twelve SRD classes, each with exactly one subclass -- ported from
`parse_classes_en.py`, same record shape (subclass nested inside its class,
same three reasons given there for not inventing a `record_link` edge for
a 1:1, always-present, same-layer composition), same deliberate omissions
(the numeric level-progression table, each caster's own "Liste des sorts de
X" section).

THE CORE TRAITS TABLE HAS A DIFFERENT LAYOUT FROM EN'S, not just different
words: EN's label sometimes sits INLINE with its value on one line
("Weapon Proficiencies Simple and Martial weapons") and sometimes the value
follows on a separate line, inconsistently, per field. The French table is
more UNIFORM but has its own trap -- the label and its value are always on
SEPARATE lines, but the label's own WRAP POINT is not fixed: "Formation aux
armures" wraps as "Formation\naux armures" for Barbare but "Formation aux\n
armures" for Barde (measured on the real pinned pages). A parser that
hard-codes either 2-line split breaks on the other class. Fixed by joining
candidate lines with a space and comparing the JOINED text against the
label's own full string, rather than matching a fixed line count --
`_match_label` tries 1, 2, then 3 physical lines and accepts whichever
joins to the exact label. Once a label is found, French additionally
guarantees (checked across all twelve classes) that a REAL blank line
always separates the value from the next label -- so, unlike EN, there is
no inline-vs-next-line ambiguity to resolve for the value itself: it is
simply "every line up to the next blank line".

Eight labels, same fixed order as EN (Primary Ability, Hit Point Die,
Saving Throw Proficiencies, Skill Proficiencies, Weapon Proficiencies,
[Tool Proficiencies -- Barde/Druide/Moine/Roublard only, exactly the same
four classes as EN's Bard/Druid/Monk/Rogue], Armor Training, Starting
Equipment): "Caractéristique principale", "Dé de vie", "Maîtrise des jets
de sauvegarde", "Maîtrises de compétence", "Maîtrises d'arme", "Maîtrises
d'outils", "Formation aux armures", "Équipement de départ".

`saving_throw_proficiencies` splits on " et " (French "and"), the same call
already made for backgrounds -- always exactly two, joined by "et", never
"ou" (checked on all twelve). `primary_ability` stays raw text for the same
reason EN's does: it genuinely mixes "et" (Force et Charisme, Paladin --
both matter) with "ou" (Force ou Dextérité, Guerrier -- a real choice).

FEATURE_HEAD reads "Niveau N : Nom" -- note the SPACE before the colon,
where EN's "Level N:" has none; the two languages' typesetting habits
differ here the same way ordinals differ in the spell parser.

THE "... OPTIONS" SUB-SECTION HEADING PUTS THE WORD FIRST IN FRENCH, not
last -- "Options de Métamagie" (Ensorceleur), "Options de Manifestation
occulte" (Occultiste), where EN's own "Metamagic Options" / "Eldritch
Invocation Options" puts it last. `_OPTIONS_HEADING` is anchored on the
line STARTING with "Options ", not ending with it -- translating EN's
regex verbatim (anchored on the tail) would silently never match anything
in this document.

THE SUBCLASS HEADING NEEDLE IS "Sous-classe de <Classe> :" (WITH the
colon) -- deliberately, because the bare phrase "Sous-classe de <Classe>"
(no colon) ALSO appears, elsewhere, as a feature NAME inside the numeric
level-progression table ("Savoir primal, Sous-classe de Barbare", one of
the table's own class-feature-by-level cells) and as a bare cross-
reference ("Sous-classe de Roublard, Visée appliquée" -- a comma, not a
colon). Requiring the colon is what tells the real heading apart from
both; checked exhaustively, the colon form is a single, literal occurrence
per class.

CHAPTER_START = "Classes" (single literal occurrence, p.30). CHAPTER_END =
"Historiques de personnage" -- the chapter that follows is titled "Origines
des personnages", but that title itself wraps across two physical lines
("Origines des\npersonnages") at an inconsistent point depending on the
page, so its own immediate first sub-heading ("Historiques de personnage",
a single literal occurrence, p.87) is used as the boundary instead, the
same discipline already applied to bound the background and species
parsers' own chapters.
"""

import re

import canon
from parse_spells import _dehyphenate_numbered

CLASSES = [
    "Barbare", "Barde", "Clerc", "Druide", "Ensorceleur", "Guerrier",
    "Magicien", "Moine", "Occultiste", "Paladin", "Rôdeur", "Roublard",
]

# Ensorceleur and Occultiste both start with a vowel sound, so French
# elides "de" -- but NOT the same way in every phrase, measured rather than
# guessed from one example: "Traits de base DE L'Ensorceleur" (the article
# "le" survives, contracted to "l'") but "Sous-classe D'Ensorceleur" and
# "Liste des sorts D'Ensorceleur" (no article at all, direct "de"->"d'").
# Applying one elision rule to all three anchors was tried first and
# silently swallowed both classes' entire content into their neighbours'
# spans (Druide's subclass came back with 20 features, Moine's with 18 --
# both anchors simply never matched, so `span_end` extended straight past
# them to the next class that DID match).
_ELIDED = {"Ensorceleur", "Occultiste"}


def _traits_needle(cls):
    return "Traits de base de l’%s" % cls if cls in _ELIDED else "Traits de base du %s" % cls


def _subclass_needle(cls):
    return "Sous-classe d’%s :" % cls if cls in _ELIDED else "Sous-classe de %s :" % cls


def _spell_list_needle(cls):
    return "Liste des sorts d’%s" % cls if cls in _ELIDED else "Liste des sorts de %s" % cls

CORE_LABELS = [
    ("primary_ability", "Caractéristique principale", False),
    ("hit_point_die", "Dé de vie", False),
    ("saving_throw_proficiencies", "Maîtrise des jets de sauvegarde", False),
    ("skill_proficiencies", "Maîtrises de compétence", False),
    ("weapon_proficiencies", "Maîtrises d’arme", False),
    ("tool_proficiencies", "Maîtrises d’outils", True),
    ("armor_training", "Formation aux armures", False),
    ("starting_equipment", "Équipement de départ", False),
]

FEATURE_HEAD = re.compile(r"^Niveau (\d+)\s*:\s*(.+)$")
_OPTIONS_HEADING = re.compile(r"^Options\s+\S.*$")

CHAPTER_START = "Classes"
CHAPTER_END = "Historiques de personnage"


def _paragraphs(lines):
    end = len(lines)
    while end > 0 and not lines[end - 1]:
        end -= 1
    lines = lines[:end]
    paragraphs = []
    for chunk in "\n".join(lines).split("\n\n"):
        joined = " ".join(l for l in chunk.split("\n") if l)
        if joined:
            paragraphs.append(joined)
    return "\n\n".join(paragraphs)


def _match_label(stripped, i, end_limit, label_text, max_lines=3):
    """How many physical lines starting at i join (space-separated) to
    exactly `label_text`. None if no prefix of up to `max_lines` lines
    does -- see module docstring: the wrap point is not fixed.
    """
    joined = ""
    for k in range(max_lines):
        if i + k >= end_limit or not stripped[i + k]:
            break
        joined = (joined + " " + stripped[i + k]).strip() if joined else stripped[i + k]
        if joined == label_text:
            return k + 1
        if len(joined) > len(label_text):
            break
    return None


def _parse_core_traits(stripped, i, end_limit):
    """Walk the fixed label sequence of a "Traits de base de X" table.

    Returns (traits_dict, index_after, error). A value is every line from
    just after its label to the next real blank line -- see module
    docstring: unlike EN, French always separates value from next label
    with a genuine blank line, so no inline-vs-next-line ambiguity exists
    here to resolve.
    """
    traits = {}
    li = 0
    while li < len(CORE_LABELS):
        key, label_text, optional = CORE_LABELS[li]
        if i >= end_limit:
            if optional:
                li += 1
                continue
            return None, i, "ran out of lines before label %r" % label_text
        consumed = _match_label(stripped, i, end_limit, label_text)
        if consumed is None:
            if optional:
                li += 1
                continue
            return None, i, "expected label %r at line %d, found %r" % (label_text, i, stripped[i])
        i += consumed
        value_parts = []
        while i < end_limit and stripped[i]:
            value_parts.append(stripped[i])
            i += 1
        if i < end_limit and not stripped[i]:
            i += 1  # consume the blank separator between fields
        traits[key] = " ".join(value_parts).strip()
        li += 1

    return traits, i, None


def _collect_features(stripped, page_of, start, end):
    heads = [i for i in range(start, end) if FEATURE_HEAD.match(stripped[i])]
    features = []
    for pos, idx in enumerate(heads):
        m = FEATURE_HEAD.match(stripped[idx])
        desc_start = idx + 1
        desc_end = heads[pos + 1] if pos + 1 < len(heads) else end
        description = _paragraphs(stripped[desc_start:desc_end])
        features.append(
            {
                "level": int(m.group(1)),
                "name": m.group(2).strip(),
                "description": description,
                "page": page_of[idx] if idx < len(page_of) else page_of[-1],
            }
        )
    return features


def parse_stream(text, page_of):
    lines = [l.strip("\n") for l in text.split("\n")]
    classes, anomalies = [], []

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

    anchors = {}
    for cls in CLASSES:
        needle = _traits_needle(cls)
        for i in range(chapter_start, chapter_end):
            if stripped[i] == needle:
                anchors[cls] = i
                break

    missing_anchor = [cls for cls in CLASSES if cls not in anchors]
    for cls in missing_anchor:
        anomalies.append(
            {"page": page_at(chapter_start), "line": chapter_start,
             "detail": "class %r has no %r anchor in the Classes chapter" % (cls, _traits_needle(cls))}
        )

    ordered = sorted((idx, cls) for cls, idx in anchors.items())
    span_end = {}
    for pos, (idx, cls) in enumerate(ordered):
        following = ordered[pos + 1][0] if pos + 1 < len(ordered) else chapter_end
        span_end[cls] = following

    for cls in CLASSES:
        if cls not in anchors:
            continue
        start = anchors[cls]
        end = span_end[cls]

        traits_start = start + 1
        while traits_start < end and not stripped[traits_start]:
            traits_start += 1
        traits, after_traits, err = _parse_core_traits(stripped, traits_start, end)
        if err:
            anomalies.append(
                {"page": page_at(start), "line": start,
                 "detail": "class %r core traits table: %s" % (cls, err)}
            )
            continue

        subclass_needle = _subclass_needle(cls)
        subclass_idx = None
        for i in range(after_traits, end):
            if stripped[i].startswith(subclass_needle):
                subclass_idx = i
                break
        if subclass_idx is None:
            anomalies.append(
                {"page": page_at(start), "line": start,
                 "detail": "class %r has no %r heading before the next class" % (cls, subclass_needle)}
            )
            continue

        core_features_end = subclass_idx
        spell_list_needle = _spell_list_needle(cls)
        for i in range(after_traits, subclass_idx):
            if stripped[i] == spell_list_needle:
                core_features_end = min(core_features_end, i)
                break
        for i in range(after_traits, subclass_idx):
            if _OPTIONS_HEADING.match(stripped[i]):
                core_features_end = min(core_features_end, i)
                break

        first_feature = None
        for i in range(after_traits, core_features_end):
            if FEATURE_HEAD.match(stripped[i]):
                first_feature = i
                break
        if first_feature is None:
            anomalies.append(
                {"page": page_at(start), "line": start,
                 "detail": "class %r has a core traits table but no 'Niveau N :' feature" % cls}
            )
            continue

        description = _paragraphs(stripped[after_traits:first_feature])
        features = _collect_features(stripped, page_of, first_feature, core_features_end)
        empty = [f["name"] for f in features if not f["description"]]
        if empty:
            anomalies.append(
                {"page": page_at(start), "line": start,
                 "detail": "class %r has feature(s) with no description text: %s"
                           % (cls, ", ".join(empty))}
            )
            continue

        head_line = stripped[subclass_idx]
        name_parts = [head_line[len(subclass_needle):].strip()]
        j = subclass_idx + 1
        while j < end and stripped[j]:
            name_parts.append(stripped[j])
            j += 1
        subclass_name = re.sub(r"\s+", " ", " ".join(p for p in name_parts if p)).strip()
        if j < end and not stripped[j]:
            j += 1

        subclass_first_feature = None
        for i in range(j, end):
            if FEATURE_HEAD.match(stripped[i]):
                subclass_first_feature = i
                break
        if not subclass_name or subclass_first_feature is None:
            anomalies.append(
                {"page": page_at(subclass_idx), "line": subclass_idx,
                 "detail": "class %r subclass heading did not resolve to a name and features"
                           % cls}
            )
            continue

        subclass_description = _paragraphs(stripped[j:subclass_first_feature])
        subclass_features = _collect_features(
            stripped, page_of, subclass_first_feature, end
        )
        empty_sub = [f["name"] for f in subclass_features if not f["description"]]
        if not subclass_description or empty_sub:
            anomalies.append(
                {"page": page_at(subclass_idx), "line": subclass_idx,
                 "detail": "class %r subclass %r missing description text: intro=%s features=%s"
                           % (cls, subclass_name, bool(subclass_description), ", ".join(empty_sub))}
            )
            continue

        saving_throw = [
            s.strip() for s in re.split(r"\s+et\s+", traits["saving_throw_proficiencies"])
            if s.strip()
        ]
        if len(saving_throw) != 2:
            anomalies.append(
                {"page": page_at(start), "line": start,
                 "detail": "class %r has %d saving throw proficiency(ies), expected 2: %r"
                           % (cls, len(saving_throw), traits["saving_throw_proficiencies"])}
            )
            continue

        classes.append(
            {
                "name": cls,
                "primary_ability": traits["primary_ability"],
                "hit_point_die": traits["hit_point_die"],
                "saving_throw_proficiencies": saving_throw,
                "skill_proficiencies": traits["skill_proficiencies"],
                "weapon_proficiencies": traits["weapon_proficiencies"],
                "tool_proficiencies": traits.get("tool_proficiencies") or None,
                "armor_training": traits["armor_training"],
                "starting_equipment": traits["starting_equipment"],
                "description": description,
                "features": features,
                "subclass": {
                    "name": subclass_name,
                    "description": subclass_description,
                    "features": subclass_features,
                },
                "page": page_at(start),
            }
        )

    return classes, anomalies


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

    classes, conflicts = [], []
    for cls in found:
        if cls["page"] in suspect:
            conflicts.append(
                {"page": cls["page"], "name": cls["name"],
                 "detail": "page text disputed between PyMuPDF and pdftotext"}
            )
        else:
            classes.append(cls)

    classes.sort(key=lambda c: canon.slugify(c["name"]))
    return classes, anomalies, conflicts
