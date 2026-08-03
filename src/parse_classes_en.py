"""Class parser for the English SRD 5.2.1.

CALIBRATED against the pinned EN PDF on 2026-08-03, "Classes" (p.28-82). All
twelve SRD classes, each with exactly one subclass (the SRD 5.2.1 subset
carries one per class; the 2024 books' fuller subclass lists are outside the
CC-BY grant -- ATTRIBUTION.md already names this: "44 of 48 subclasses" not
in the SRD).

THE RECORD SHAPE, DECIDED AND WORTH EXPLAINING WHY: one record per class,
subclass NESTED inside it rather than a separate `kind`. Three things made
that the right call rather than the merely convenient one:

  1. The schema's `record_link` table models cross-layer relations
     (`overrides`, `extends`, `translation_of`...) -- none of which describes
     "this subclass belongs to this class" within the SAME layer. Inventing a
     new relation kind for a 1:1, always-present, never-shared composition
     would be machinery for a shape that never varies in this SRD subset.
  2. Every class has EXACTLY one subclass here (unlike, say, a spell's many
     classes, or an item's many rarities-in-one-entry). A one-to-one,
     always-present child is a field, not a foreign relationship -- the same
     reasoning already applied to a magic item's rarity clause and a
     background's equipment list: don't force structure the source's own
     shape doesn't ask for.
  3. A consumer wanting "everything a level-3 Barbarian has" needs the class
     and its subclass in the same read. Splitting them into two `kind`s
     bodies a query that is not the SRD's actual granularity: SRD 5.2.1
     itself presents a subclass as part of its class's own chapter, not as
     an independent, freestanding entity a player could pick without a
     class.

The full progression TABLE (Proficiency Bonus by level, and each class's own
resource column -- Rages, Sorcery Points, spell slots per level, and so on)
is DELIBERATELY NOT DECOMPOSED this round, the same call already made for
Equipment in the prior lot and for a magic item's embedded random tables:
a genuine multi-column table, a different extraction problem from a
stat-block-shaped entry. Unlike Equipment, this one turned out to be row-
coherent in the extracted text (a blank-line-separated group of N lines per
level, matching the column count) rather than fully scrambled -- worth
recording for whoever calibrates it later, since that is a meaningfully
easier starting point than Equipment's tables were. What this pass captures
instead is every named class and subclass FEATURE via its own "Level N:
Feature Name" heading, in reading order -- which is what a player actually
reads to know what they get and when; the numeric table is a lookup grid for
the same information, not additional rules text.

ALSO DELIBERATELY NOT CAPTURED: each spell-list class's own "<Class> Spell
List" section (Bard, Cleric, Druid, Paladin, Ranger, Sorcerer, Warlock,
Wizard). It is redundant with data already in the EN spell catalogue --
every spell record already carries a `classes` list read off its own head
line (see parse_spells_en.py) -- and it is its own table grammar (Spell /
School / Special columns) that would need separate calibration for no new
information. Cross-checked, not merely assumed: every spell this parser's
class chapters mention by name already resolves against `srd:spell:en:*`.

Sorcerer's "Metamagic Options" and Warlock's "Eldritch Invocation Options"
sections -- named, prerequisite-gated choice catalogues that are their own
third grammar, distinct from both the "Level N: Feature" shape and a spell
list's table shape -- are likewise deferred rather than rushed into a
same-round grammar under time pressure. They bound the "core class features"
region (see `_OPTIONS_HEADING` below) so their content does not leak into an
adjacent feature's description, but their own content is not parsed into
records this round.

THE CORE TRAITS TABLE ("Core Barbarian Traits" etc.) has NO colon separator
at all, unlike every other stat-block grammar in this pipeline -- it is
label-then-value with no delimiter, and PyMuPDF's column layout sometimes
puts the value on the label's OWN line ("Weapon Proficiencies Simple and
Martial weapons") and sometimes on the line(s) after it ("Primary Ability" /
"Strength"), inconsistently, per field, per class. "Saving Throw" is a
special case again: its label itself wraps to two physical lines ("Saving
Throw" / "Proficiencies") before any value appears. Measured across all
twelve classes: the field ORDER is perfectly consistent (Primary Ability,
Hit Point Die, Saving Throw Proficiencies, Skill Proficiencies, Weapon
Proficiencies, [Tool Proficiencies -- Bard/Druid/Monk/Rogue only], Armor
Training, Starting Equipment), so `_parse_core_traits` walks that fixed
sequence rather than pattern-matching a colon that isn't there.

TWO FIELDS ARE DECOMPOSED INTO A LIST, the rest stay raw source text -- the
same "grant vs. choice" line already drawn for backgrounds: `saving_throw_
proficiencies` is always an unconditional "X and Y" (never "or", checked on
all twelve), so it becomes a 2-element list. `primary_ability` stays raw text
even though it looks similar, because it genuinely mixes "and" (Paladin:
"Strength and Charisma", both matter) with "or" (Fighter: "Strength or
Dexterity", a real choice) -- flattening both into a list would erase a
distinction that changes what the field means. `skill_proficiencies`,
`weapon_proficiencies`, `tool_proficiencies`, `armor_training` and
`starting_equipment` are all "choose N from this menu" clauses, kept as the
source's own text, the same call already made for a magic item's rarity
clause and a spell's components.

A BUG CAUGHT BY MANUAL VERIFICATION, WORTH NAMING BECAUSE THE SAME MISTAKE
WAS ALMOST MADE HERE TOO: `parse_species_en.py` was first written by copying
the spell/item "trim one extra line for the next entry's name" step,
because every OTHER parser in this pipeline has its head line living BELOW
the entry's name. Species and this class/feature grammar don't -- "Level 1:
Rage" and "Dragonborn" both ARE the name, not a stat line underneath one --
so slicing up to the next head already excludes it, and that trim step
would have silently eaten the last sentence of every feature and every
species but the last one in its chapter. Caught reading Dragonborn's
description end-to-end against the PDF and finding it stopped mid-sentence.
Neither `_collect_features` nor the class/subclass boundary logic below
performs that trim, on purpose.
"""

import re

import canon
from parse_spells_en import _dehyphenate_numbered

CLASSES = [
    "Barbarian", "Bard", "Cleric", "Druid", "Fighter", "Monk",
    "Paladin", "Ranger", "Rogue", "Sorcerer", "Warlock", "Wizard",
]

CORE_LABELS = [
    ("primary_ability", "Primary Ability", False),
    ("hit_point_die", "Hit Point Die", False),
    ("saving_throw_proficiencies", "Saving Throw", True),
    ("skill_proficiencies", "Skill Proficiencies", False),
    ("weapon_proficiencies", "Weapon Proficiencies", False),
    ("tool_proficiencies", "Tool Proficiencies", False),
    ("armor_training", "Armor Training", False),
    ("starting_equipment", "Starting Equipment", False),
]
OPTIONAL_LABELS = {"tool_proficiencies"}

FEATURE_HEAD = re.compile(r"^Level (\d+): (.+)$")
_OPTIONS_HEADING = re.compile(r"^\S.* Options$")

CHAPTER_START = "Classes"
CHAPTER_END = "Character Origins"


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


def _parse_core_traits(stripped, i, end_limit):
    """Walk the fixed label sequence of a "Core X Traits" table.

    Returns (traits_dict, index_after, error) -- error is None on success, a
    human-readable string naming exactly which label failed otherwise. Never
    guesses past a mismatch: a class whose table does not match this shape is
    reported and excluded whole, not partially filled.
    """
    traits = {}
    li = 0
    while li < len(CORE_LABELS):
        key, label, two_line = CORE_LABELS[li]
        if i >= end_limit:
            return None, i, "ran out of lines before label %r" % label
        line = stripped[i]
        exact = line == label
        inline = (not exact) and line.startswith(label + " ")
        if not (exact or inline):
            if key in OPTIONAL_LABELS:
                li += 1
                continue
            return None, i, "expected label %r at line %d, found %r" % (label, i, line)

        if exact:
            i += 1
            if two_line:
                if i < end_limit and stripped[i] == "Proficiencies":
                    i += 1
                else:
                    return None, i, "'Saving Throw' not followed by 'Proficiencies'"
            inline_value = ""
        else:
            inline_value = line[len(label):].strip()
            i += 1

        value_parts = [inline_value] if inline_value else []
        while i < end_limit and stripped[i]:
            value_parts.append(stripped[i])
            i += 1
        if i < end_limit and not stripped[i]:
            i += 1  # consume the blank separator between fields
        traits[key] = " ".join(value_parts).strip()
        li += 1

    return traits, i, None


def _collect_features(stripped, page_of, start, end):
    """"Level N: Feature Name" headings, in reading order, within [start, end).

    No next-entry-name trim: the head IS the name here (see module docstring).
    """
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

    # Each class's own span runs from its "Core X Traits" anchor to the NEXT
    # class's anchor, or to the chapter boundary for Wizard (the last one).
    # Anchored on the exact, known class names -- twelve of them, fixed --
    # rather than a generic pattern, the same discipline already used for a
    # magic item's category word and a feat's category word.
    anchors = {}
    for cls in CLASSES:
        needle = "Core %s Traits" % cls
        for i in range(chapter_start, chapter_end):
            if stripped[i] == needle:
                anchors[cls] = i
                break

    missing_anchor = [cls for cls in CLASSES if cls not in anchors]
    for cls in missing_anchor:
        anomalies.append(
            {"page": page_at(chapter_start), "line": chapter_start,
             "detail": "class %r has no 'Core %s Traits' anchor in the Classes chapter" % (cls, cls)}
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

        subclass_needle = "%s Subclass:" % cls
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

        # Core-features region ends at the FIRST of: this class's own spell
        # list heading, an "... Options" heading (Sorcerer/Warlock only), or
        # the subclass heading itself -- whichever comes first. All three are
        # optional except the subclass heading, which always bounds it.
        core_features_end = subclass_idx
        spell_list_needle = "%s Spell List" % cls
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
                 "detail": "class %r has a core traits table but no 'Level N:' feature" % cls}
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

        # Subclass name: text after "Subclass:" on its own head line, plus
        # any continuation lines (the name wraps for Barbarian, Bard, Druid,
        # Monk, Sorcerer -- measured) up to the blank line that separates it
        # from the tagline/intro prose.
        head_line = stripped[subclass_idx]
        name_parts = [head_line[len(subclass_needle):].strip()]
        j = subclass_idx + 1
        while j < end and stripped[j]:
            name_parts.append(stripped[j])
            j += 1
        subclass_name = re.sub(r"\s+", " ", " ".join(p for p in name_parts if p)).strip()
        if j < end and not stripped[j]:
            j += 1  # consume the blank line after the name block

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
            s.strip() for s in re.split(r"\s+and\s+", traits["saving_throw_proficiencies"])
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
