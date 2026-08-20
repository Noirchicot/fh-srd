"""Mechanical fields, derived from what the parsers already read.

The parsers read the PDF and keep what it prints: `"d6 par niveau de Magicien"`,
`"9 m"`, `"2 au choix parmi : Arcanes, Histoire…"`. That is the right thing for
a human reader and the wrong thing for a character builder, which needs `6`,
`9`, and a list of identifiers it can look records up by.

This module adds the second reading **beside** the first. It never removes,
never rewrites, never reorders an existing field. `hit_point_die` stays exactly
as it was; `hit_die` arrives next to it. That rule is not a preference — the
public site renders the printed strings and the attribution suite compares them
to the PDF character for character.

Three refusals are built in, and they are the point of the module:

  * **It reads nothing.** Every value here is a re-reading of a field a
    calibrated parser already produced. No page, no PDF, no second grammar.
  * **It invents nothing.** Every mapping is a closed set the source itself
    enumerates, and a value outside that set raises `DerivationError` naming
    the record and the string. There is no default, no fallback, no zero.
  * **It joins for real.** A skill, feat or tool named in prose becomes an
    identifier only if a record with that identifier exists in the same build,
    in the same language. An unresolvable name stops the build; it does not
    become a plausible-looking id pointing at nothing.

WHERE THE KEYS COME FROM, since two conventions live side by side here and the
difference is deliberate:

  * `ability_keys`, `saving_throw_keys`, `size_key` and the `senses` id are
    **cross-language canonical keys** — `wis`, `medium`, `darkvision` — in the
    French records as much as the English ones. That is what
    `contracts/DERIVATION-FIELDS.md` §3 specifies (its `background.ability_keys`
    example, `["con","int","wis"]`, is the French Sage's Constitution /
    Intelligence / Sagesse), and it is what `fh-char/1` stores.
  * `damage_type_key` is **language-native** (`perforant` / `piercing`), also
    per §3. Normalising to the singular is not a stylistic choice: the SRD
    prints "1d4 perforants" for the dagger and "1 perforant" for the blowgun,
    so slugifying what is printed would give one damage type two keys.

`skill.ability_key` was language-native when this module was written (`sag`,
`for`) and is now canonical too, by the architect's arbitration of 2026-08-08:
`fh-char/1` requires `str dex con int wis cha` of a French character sheet as
much as an English one, so a French skill keyed `sag` could not address the
abilities of its own document. The two therefore **do** join. `parse_skills_fr`
carries the reversal and its reasoning; the FR *monster* export still keys stat
blocks `for`/`sag`, which is the PDF's own printed table and untouched.
"""

import re

import canon


class DerivationError(Exception):
    """A mechanical field could not be derived from what the source prints.

    Always fatal. The alternative — emitting a guess — produces a character
    that is wrong in a way nobody can see.
    """


# The kinds whose records are looked up BY the derivation, and whose OWN
# derivation needs no index in return. They can therefore be derived and
# resolved before any join happens, which makes their identifiers final at
# that point — including a collision suffix, which comes from a content hash
# that nothing afterwards will change. (`tool` does now receive a derived
# field of its own, `ability_key`; what puts it in this group is not that it
# has no field but that deriving it looks nothing up.)
INDEX_KINDS = ("feat", "skill", "tool")

# Index kinds that DO receive derived fields, and so have to be derived and
# resolved BEFORE the kinds that point at them. `class` is here alone: a
# background's feat carries a class in parentheses ("Initié à la magie
# (Clerc)"), while a class's own derivation needs nothing but `skill`. The
# order between these two groups is the whole reason build.py parses every
# kind before writing any of them.
INDEX_KINDS_DERIVED = ("class",)

# The kinds that receive derived fields.
DERIVED_KINDS = ("armor", "background", "class", "species", "spell",
                 "tool", "weapon")


# --------------------------------------------------------------------------
# Closed sets, each enumerated by the SRD itself
# --------------------------------------------------------------------------

# The six abilities, in each language's printed spelling, mapped to the
# canonical key. The French PDF's stat blocks abbreviate Sagesse "Sag" and
# Force "For"; those are NOT the keys used here — see the module docstring.
ABILITY_KEYS = {
    "fr": {
        "Force": "str",
        "Dextérité": "dex",
        "Constitution": "con",
        "Intelligence": "int",
        "Sagesse": "wis",
        "Charisme": "cha",
    },
    "en": {
        "Strength": "str",
        "Dexterity": "dex",
        "Constitution": "con",
        "Intelligence": "int",
        "Wisdom": "wis",
        "Charisma": "cha",
    },
}

# "Une créature ou un objet appartient à une catégorie de taille parmi celles
# ci-dessous : très petite (TP), petite (P), moyenne (M), grande (G), très
# grande (TG) ou gigantesque (Gig)."  — srd:glossary:fr:capacite-de-charge
# "A creature or an object belongs to a size category: Tiny, Small, Medium,
# Large, Huge, or Gargantuan."                       — srd:glossary:en:size
# The two enumerations are the same list in the same order; the alignment is
# the source's own, not an assumption about translation.
SIZE_KEYS = {
    "fr": {
        "TP": "tiny",
        "P": "small",
        "M": "medium",
        "G": "large",
        "TG": "huge",
        "Gig": "gargantuan",
    },
    "en": {
        "Tiny": "tiny",
        "Small": "small",
        "Medium": "medium",
        "Large": "large",
        "Huge": "huge",
        "Gargantuan": "gargantuan",
    },
}

# Only the three physical types appear on a weapon. Both the singular and the
# plural are attested in the source (the blowgun's "1 perforant" against every
# other weapon's "1d8 perforants"), which is exactly why one canonical form is
# required rather than optional.
DAMAGE_TYPE_KEYS = {
    "fr": {
        "contondant": "contondant",
        "contondants": "contondant",
        "perforant": "perforant",
        "perforants": "perforant",
        "tranchant": "tranchant",
        "tranchants": "tranchant",
    },
    "en": {
        "Bludgeoning": "bludgeoning",
        "Piercing": "piercing",
        "Slashing": "slashing",
    },
}

HIT_DICE = (6, 8, 10, 12)


# --------------------------------------------------------------------------
# Grammars, each read off the real records rather than assumed
# --------------------------------------------------------------------------

# "d6 par niveau de Magicien" / "D6 per Wizard level"
_HIT_DIE = re.compile(r"^[dD](\d+)\b")

# "2 au choix parmi : Arcanes, Histoire et Religion"
# "Choose 2: Arcana, History, or Religion"
_MENU_LIST = {
    "fr": re.compile(r"^(\d+) au choix parmi :\s*(.+)$"),
    "en": re.compile(r"^Choose (\d+):\s*(.+)$"),
}
# "3 compétences au choix (cf. « Comment jouer »)"
# "Choose any 3 skills (see “Playing the Game”)"
_MENU_OPEN = {
    "fr": re.compile(r"^(\d+) compétences au choix\b"),
    "en": re.compile(r"^Choose any (\d+) skills\b"),
}
# English puts a comma before its final "or"; French puts none before its "et".
# Splitting on commas alone fuses the last two French options into one name
# that resolves to nothing — which is how a builder loses a skill silently.
_MENU_SPLIT = {
    "fr": re.compile(r",\s*et\s+|,\s*|\s+et\s+"),
    "en": re.compile(r",\s*or\s+|,\s*|\s+or\s+"),
}

# " (cf. « Dons »)" / " (see “Feats”)" — a pointer to another chapter, not part
# of the name.
_CHAPTER_REF = {
    "fr": re.compile(r"\s*\(cf\.[^()]*\)\s*$"),
    "en": re.compile(r"\s*\(see[^()]*\)\s*$"),
}
# A trailing option carried by the feat's own name: "Initié à la magie (Clerc)".
_TRAILING_PAREN = re.compile(r"\s*\(([^()]*)\)\s*$")

# "Choisissez un type de boîte de jeux" / "Choose one kind of Gaming Set"
_TOOL_CHOICE = {
    "fr": re.compile(r"^Choisissez\b"),
    "en": re.compile(r"^Choose\b"),
}

# "9 m", "10,50 m" / "30 feet"
_SPEED = {
    "fr": re.compile(r"^(\d+(?:,\d+)?)\s*m$"),
    "en": re.compile(r"^(\d+)\s*feet$"),
}
# Built FROM `SIZE_KEYS` so the grammar and the closed set cannot drift apart:
# a category added to one is a category the other recognises. Longest first, or
# "P" would match the "TP" it is a suffix of.
def _size_alternation(lang):
    return "|".join(sorted(SIZE_KEYS[lang], key=len, reverse=True))


_SIZE_HEAD = {
    lang: re.compile(r"^(%s)\b" % _size_alternation(lang)) for lang in SIZE_KEYS
}
# "M (moyenne, …) ou P (petite, …), à choisir lors de la sélection de l'espèce"
_SIZE_ALTERNATIVE = {
    "fr": re.compile(r"\bou\s+(%s)\b" % _size_alternation("fr")),
    "en": re.compile(r"\bor\s+(%s)\b" % _size_alternation("en")),
}

# "1d6 perforants" / "1 perforant" / "1d8 Slashing"
_DAMAGE = re.compile(r"^(\d+)(?:d(\d+))?\s+(\S+)$")

# "14 + modificateur de Dex (max 2)" / "11 + Dex modifier" / "16" / "+2"
_AC = {
    "fr": re.compile(
        r"^(?:(?P<base>\d+)(?:\s*\+\s*modificateur de Dex"
        r"(?:\s*\(max (?P<cap>\d+)\))?)?|\+(?P<bonus>\d+))$"
    ),
    "en": re.compile(
        r"^(?:(?P<base>\d+)(?:\s*\+\s*Dex modifier"
        r"(?:\s*\(max (?P<cap>\d+)\))?)?|\+(?P<bonus>\d+))$"
    ),
}

# "Caractéristique d'incantation. Le Charisme est la caractéristique
#  d'incantation de vos sorts de Barde."
# "Spellcasting Ability. Charisma is your spellcasting ability for your Bard
#  spells."
#
# ANCHORED ON THE SUB-HEADING, and that is the whole calibration. Two traps it
# steps over:
#   * The Paladin and the Ranger say "et le Charisme est la caractéristique
#     d'incantation associée" inside their FIGHTING STYLE feature as well. That
#     sentence has no heading, so it is not read.
#   * English writes "is YOUR spellcasting ability" for seven classes and "is
#     THE spellcasting ability" for the Warlock alone. Matching the sentence
#     rather than the heading loses Pact Magic; the heading finds all eight.
_SPELLCASTING_ABILITY = {
    "fr": re.compile(
        r"Caractéristique d[’']incantation\.\s*L(?:e |a |[’'])\s*"
        r"(Force|Dextérité|Constitution|Intelligence|Sagesse|Charisme)\b"
    ),
    "en": re.compile(
        r"Spellcasting Ability\.\s*"
        r"(Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma)\b"
    ),
}

# --- the level-1 weapon-mastery count -------------------------------------
#
# THE COUNT IS PRINTED IN TWO DIFFERENT GRAMMARS, and that is the whole trap
# this block exists for. Barbarian and Fighter state it in their PROGRESSION
# TABLE, in a column the table parser already reads (`resources`). Paladin,
# Ranger and Rogue have no such column: their count exists only in the PROSE
# of the level-1 feature — "the mastery properties of two kinds of weapons of
# your choice with which you have proficiency". A reader that knows only the
# table grammar sees two classes out of five and reports nothing; the builder
# then offers weapon masteries to the Barbarian and the Fighter and to nobody
# else. That is the 2026-08-08 shape of failure, one genre over.
#
# So the count is derived HERE, from the prose, for ALL FIVE classes — the
# grammar every one of them shares — and the table is used as an INDEPENDENT
# WITNESS: `check_weapon_mastery_counts` below requires the two readings to
# agree wherever both exist, and refuses rather than pick one.
#
# The feature's name is also the progression column's label, in both
# languages. That is the source's own doing, not a convenience:
#
#   EN  feature "Weapon Mastery"   · column "Weapon Mastery"
#   FR  feature "Bottes d’arme"    · column "Bottes d’arme"
#
# ⚠️ FRENCH SAYS "BOTTE", NOT "MAÎTRISE". `Maîtrise des armes` is a different
# rule (weapon *proficiency*) printed on the neighbouring page. Anchoring on
# "maîtrise" here would read the wrong thing silently — see
# `weapon_sections.py`, which pays for the same trap in the Equipment chapter.
WEAPON_MASTERY_FEATURE = {"en": "Weapon Mastery", "fr": "Bottes d’arme"}

# The SRD gives the feature to exactly five of its twelve classes.
WEAPON_MASTERY_CLASSES = 5

# "…the mastery properties of two kinds of Simple or Martial Melee weapons…"
# "…recourir à la botte de deux types d’arme de corps à corps courante…"
# "…recourir à la propriété Botte de deux types d’arme de votre choix…"
_WEAPON_MASTERY_COUNT = {
    "en": re.compile(r"mastery properties of (\w+) kinds? of"),
    "fr": re.compile(r"[Bb]otte de (\w+) types? d[’']arme"),
}

# The number words the five features actually print, and no others. A word
# outside this set stops the build instead of becoming a plausible integer.
_NUMBER_WORDS = {
    "en": {"one": 1, "two": 2, "three": 3, "four": 4},
    "fr": {"un": 1, "deux": 2, "trois": 3, "quatre": 4},
}


class WeaponMasteryCountError(RuntimeError):
    """The level-1 weapon-mastery count did not come back for all five classes."""


# "Concentration, jusqu'à 1 heure" / "Concentration up to 10 minutes".
# A STRUCTURED FIELD, not prose: `duration` is present on all 339 spells in
# both languages, and every one of the 133 that concentrate says so as its
# first word. This is the only spell field derived here — see the module
# docstring on `cast_type`, which is not.
_CONCENTRATION = "Concentration"

# --- species traits (the contract's "group B", delivered in part) ----------
# "Vision dans le noir. Vous disposez de la Vision dans le noir sur 18 m."
# "Darkvision. You have Darkvision with a range of 60 feet."
# Anchored on the TRAIT's own sentence: the Drow lineage row says "La portée de
# votre Vision dans le noir passe à 36 m", which is a lineage benefit and must
# not be read as the species' base sense.
#
# The trait's PRINTED NAME is captured rather than typed here, because
# `resolved.senses[]` in `fh-char/1` requires `name` beside `id` and `value`,
# and a name written into this module would be a displayable word invented by
# the engine (law §0.13). It comes off the page or it does not come at all.
_DARKVISION = {
    "fr": re.compile(
        r"(Vision dans le noir)\.\s*Vous disposez de la Vision dans le noir "
        r"sur (\d+(?:,\d+)?) m\."
    ),
    "en": re.compile(
        r"(Darkvision)\.\s*You have Darkvision with a range of (\d+) feet\."
    ),
}
# "Sens aiguisés. Vous bénéficiez de la maîtrise de la compétence Intuition,
#  Perception ou Survie au choix."  /  "Keen Senses. You have proficiency in
#  the Insight, Perception, or Survival skill."
_GRANTED_SKILL_LIST = {
    "fr": re.compile(r"maîtrise de la compétence ([^.]+?) au choix"),
    "en": re.compile(r"proficiency in the ([^.]+?) skill\b"),
}
# "Compétent. Vous recevez la maîtrise d'une compétence de votre choix."
# "Skillful. You gain proficiency in one skill of your choice."
_GRANTED_SKILL_ANY = {
    "fr": re.compile(r"maîtrise d[’']une compétence de votre choix"),
    "en": re.compile(r"proficiency in one skill of your choice"),
}
# The species trait separates its options with "ou" where a class skill menu
# uses "et" — "Intuition, Perception ou Survie" against "Perception et Survie".
# Reusing the menu splitter here produced 'Perception ou Survie' as one name,
# and the join refused it: two lists, two conjunctions, two grammars.
_TRAIT_SPLIT = {
    "fr": re.compile(r",\s*ou\s+|,\s*|\s+ou\s+"),
    "en": re.compile(r",\s*or\s+|,\s*|\s+or\s+"),
}


# --------------------------------------------------------------------------
# The index the joins resolve against
# --------------------------------------------------------------------------


def build_index(kind, lang, resolved_candidates):
    """slug -> record id, for one of `INDEX_KINDS`, from this same build.

    Keyed by the slug of the record's *name*, because that is the join the
    repository already proves works: `tests/test_acceptance_srd_tables.py`
    resolves all 78 class skill options that way against the real exports.
    """
    index = {}
    for cand in resolved_candidates:
        key = canon.slugify(cand["name"])
        if key in index:
            raise DerivationError(
                "%s/%s: two %s records both slugify to %r; a join by name is "
                "ambiguous and must not be resolved by guessing"
                % (lang, kind, kind, key)
            )
        index[key] = canon.record_id("srd", kind, lang, cand["slug"])
    return index


def _note(notes, message):
    """Record something the derivation would not do, without stopping.

    Used ONLY where the rule is "emit nothing and say so" rather than "stop".
    `build.py` prints every note on stderr and counts them in its audit, so a
    note is a report, never a silent skip — which is why a caller that passed
    no list is itself an error rather than a place for the message to vanish.
    """
    if notes is None:
        raise DerivationError(
            "a derivation note had nowhere to be reported: %s" % message)
    notes.append(message)


def _resolve(index, kind, lang, text, where):
    key = canon.slugify(text)
    try:
        return index[kind][key]
    except KeyError:
        raise DerivationError(
            "%s: %s names %r, which resolves to no %s record in this build "
            "(looked for slug %r among %d)"
            % (where, lang, text, kind, key, len(index.get(kind, ())))
        )


# --------------------------------------------------------------------------
# Small readers
# --------------------------------------------------------------------------


def _number(text, where):
    """'10,50' or '10.50' -> 10.5 ; '9' -> 9 (int, not 9.0).

    An integral value is emitted as an integer so that the exported bytes say
    `9` and not `9.0`. Both are the same number; only one is what a reader
    expects to find in a record.
    """
    value = float(text.replace(",", "."))
    return int(value) if value == int(value) else value


def _mapped(table, lang, text, field, where):
    try:
        return table[lang][text]
    except KeyError:
        raise DerivationError(
            "%s: %s is %r, which is not one of the %d values the SRD "
            "enumerates for %s (%s)"
            % (where, field, text, len(table[lang]), field,
               ", ".join(sorted(table[lang])))
        )


def _skill_menu(text, lang, index, where):
    """'2 au choix parmi : …' / 'Choose any 3 skills' -> {count, from}."""
    match = _MENU_OPEN[lang].match(text)
    if match:
        return {"count": int(match.group(1)), "from": "any"}

    match = _MENU_LIST[lang].match(text)
    if not match:
        raise DerivationError(
            "%s: skill menu %r matches neither the listed form nor the open "
            "form; it cannot be turned into a choice without inventing one"
            % (where, text)
        )
    options = [p.strip() for p in _MENU_SPLIT[lang].split(match.group(2)) if p.strip()]
    if not options:
        raise DerivationError("%s: skill menu %r lists nothing" % (where, text))
    return {
        "count": int(match.group(1)),
        "from": [_resolve(index, "skill", lang, opt, where) for opt in options],
    }


# --------------------------------------------------------------------------
# Per-kind derivation
# --------------------------------------------------------------------------


def _derive_class(data, lang, index, where, notes):
    out = {}

    printed = data["hit_point_die"]
    match = _HIT_DIE.match(printed)
    if not match:
        raise DerivationError(
            "%s: hit_point_die is %r, which does not start with a die"
            % (where, printed)
        )
    die = int(match.group(1))
    if die not in HIT_DICE:
        raise DerivationError(
            "%s: hit die d%d is outside the set the SRD uses (%s)"
            % (where, die, ", ".join("d%d" % d for d in HIT_DICE))
        )
    out["hit_die"] = die

    out["saving_throw_keys"] = [
        _mapped(ABILITY_KEYS, lang, name, "saving_throw_proficiencies", where)
        for name in data["saving_throw_proficiencies"]
    ]

    out["skill_choice"] = _skill_menu(
        data["skill_proficiencies"], lang, index, where)

    # The ability a class casts with is NOT its `primary_ability`: the Paladin
    # is primarily Strength and casts on Charisma, the Ranger is primarily
    # Dexterity and casts on Wisdom. Reading `primary_ability` here would give
    # every Paladin in the world the wrong spell save DC.
    #
    # Eight of the twelve classes state it; the Barbarian, Fighter, Monk and
    # Rogue state nothing because they cast nothing, so they get no field.
    found = set()
    for feature in data.get("features") or []:
        for match in _SPELLCASTING_ABILITY[lang].finditer(
                feature.get("description") or ""):
            found.add(match.group(1))
    if len(found) > 1:
        raise DerivationError(
            "%s: the class names %d different spellcasting abilities (%s); "
            "which one a caster uses is not something this module may choose"
            % (where, len(found), ", ".join(sorted(found))))
    if found:
        out["spellcasting_ability_key"] = _mapped(
            ABILITY_KEYS, lang, found.pop(), "spellcasting ability", where)

    count = _weapon_mastery_count(data, lang, where)
    if count is not None:
        out["weapon_mastery_count"] = count
    return out


def _mastery_feature(data, lang):
    """The level-1 weapon-mastery feature of this class, or None.

    Matched on the feature's NAME and its level, never on a keyword in the
    prose: three of the five classes describe the feature in words that also
    appear elsewhere, and one language calls the feature `Bottes d’arme`
    while calling something else entirely `Maîtrise des armes`.
    """
    wanted = WEAPON_MASTERY_FEATURE[lang]
    for feature in data.get("features") or []:
        if feature.get("name") == wanted and feature.get("level") == 1:
            return feature
    return None


def _weapon_mastery_count(data, lang, where):
    """How many weapon masteries this class gets at level 1, or None.

    None means "this class has no weapon-mastery feature", which is the right
    answer for seven of the twelve classes. It is NOT a fallback: a class that
    HAS the feature and whose prose does not state a number stops the build,
    because the alternative is a builder that offers zero choices and looks
    like it worked.
    """
    feature = _mastery_feature(data, lang)
    if feature is None:
        return None

    text = feature.get("description") or ""
    match = _WEAPON_MASTERY_COUNT[lang].search(text)
    if not match:
        raise DerivationError(
            "%s: the level-1 %r feature does not state how many kinds of "
            "weapon it covers, in the grammar the other four classes use "
            "(%s). Its text begins %r"
            % (where, WEAPON_MASTERY_FEATURE[lang],
               _WEAPON_MASTERY_COUNT[lang].pattern, text[:120]))

    word = match.group(1)
    try:
        return _NUMBER_WORDS[lang][word.lower()]
    except KeyError:
        raise DerivationError(
            "%s: the level-1 %r feature says %r kinds of weapon, which is not "
            "one of the number words the SRD prints here (%s)"
            % (where, WEAPON_MASTERY_FEATURE[lang], word,
               ", ".join(sorted(_NUMBER_WORDS[lang]))))


def check_weapon_mastery_counts(class_candidates, progression_records, lang):
    """RECOUNT the five classes, and make the two grammars agree.

    Called by `build.py` once the `class` records of one source are resolved.
    Three refusals, each naming what it saw:

      1. every class carrying the level-1 feature must carry the derived
         count, and there must be exactly `WEAPON_MASTERY_CLASSES` of them;
      2. no class WITHOUT the feature may carry a count;
      3. wherever the progression table also prints the count — its own
         column, for two of the five — the two readings must be equal.

    A total that is merely right is not enough, which is the argument the
    18-skill / 25-tool guard already made in this repository: the classes are
    named, not counted.

    NOT CALLED ON AN EMPTY `class` SET, and that is not a hole. `--fixture`
    is a six-page French spell stub that legitimately yields no class at all;
    on any real source, `build.check_every_genre_yielded` has already refused
    an empty registered genre before this runs.
    """
    label = WEAPON_MASTERY_FEATURE[lang]

    with_feature, with_count = {}, {}
    for cand in class_candidates:
        data = cand["data"]
        if _mastery_feature(data, lang) is not None:
            with_feature[cand["slug"]] = cand["name"]
        if "weapon_mastery_count" in data:
            with_count[cand["slug"]] = data["weapon_mastery_count"]

    silent = sorted(set(with_feature) - set(with_count))
    invented = sorted(set(with_count) - set(with_feature))
    if silent or invented:
        raise WeaponMasteryCountError(
            "%s/class: the level-1 %r feature and the derived "
            "`weapon_mastery_count` do not cover the same classes.\n"
            "  feature but no count: %s\n"
            "  count but no feature: %s"
            % (lang, label, ", ".join(silent) or "(none)",
               ", ".join(invented) or "(none)"))

    if len(with_count) != WEAPON_MASTERY_CLASSES:
        raise WeaponMasteryCountError(
            "%s/class: %d class(es) carry a level-1 weapon-mastery count, and "
            "the SRD gives the feature to %d.\n"
            "  found: %s\n\n"
            "Two of the five state the count in their progression table and "
            "three state it only in the prose of the feature. A reader that "
            "knows one grammar and not the other comes back with a number "
            "that looks plausible and is short by three classes."
            % (lang, len(with_count), WEAPON_MASTERY_CLASSES,
               ", ".join("%s=%d" % kv for kv in sorted(with_count.items()))
               or "(none)"))

    # ---- the second grammar, as a witness --------------------------------
    for record in progression_records:
        keys = [col["key"] for col in record.get("resource_columns", [])
                if col["label"] == label]
        if not keys:
            continue
        key = keys[0]
        level_one = record["levels"][0]
        printed = level_one["resources"].get(key)
        slug = canon.slugify(record["name"])
        derived = with_count.get(slug)
        if derived is None:
            raise WeaponMasteryCountError(
                "%s/class-progression: %r prints a %r column (level 1 = %r) "
                "but no class record of this build derived a count for the "
                "slug %r. The table and the feature disagree about which "
                "classes even have this."
                % (lang, record["name"], label, printed, slug))
        if printed != derived:
            raise WeaponMasteryCountError(
                "%s: %r gets %r weapon masteries at level 1 by its "
                "progression table and %r by the prose of its %r feature. "
                "Two readings of the same rule disagree; nothing here may "
                "choose between them."
                % (lang, record["name"], printed, derived, label))


def _derive_background(data, lang, index, where, notes):
    out = {
        "skill_ids": [
            _resolve(index, "skill", lang, name, where)
            for name in data["skill_proficiencies"]
        ],
        "ability_keys": [
            _mapped(ABILITY_KEYS, lang, name, "ability_scores", where)
            for name in data["ability_scores"]
        ],
    }

    # --- the feat, and the option it was taken with ----------------------
    # "Initié à la magie (Clerc) (cf. « Dons »)": the last group points at
    # another chapter, the one before it is an option the feat itself offers.
    # The chapter pointer is dropped outright; the option is dropped ONLY if
    # the name does not resolve with it, so that a feat legitimately named
    # with a parenthesis keeps it.
    printed = _CHAPTER_REF[lang].sub("", data["feat"]).strip()
    option = None
    if canon.slugify(printed) not in index["feat"]:
        match = _TRAILING_PAREN.search(printed)
        trimmed = _TRAILING_PAREN.sub("", printed).strip()
        if match and trimmed:
            option, printed = match.group(1).strip(), trimmed
    out["feat_id"] = _resolve(index, "feat", lang, printed, where + "#feat")

    # The option is a REFERENCE, never a word: the Acolyte's Magic Initiate
    # grants the Cleric's spell list and the Sage's grants the Wizard's, and a
    # builder has to be able to follow that to a record. Carrying the string
    # "(Magicien)" in a machine field would put a displayable word where an
    # identifier belongs.
    #
    # If the parenthesis resolves to nothing, the field is NOT emitted and the
    # miss is reported. A `feat_option` pointing into the void would be worse
    # than its absence — the builder would follow it and find nothing.
    if option:
        slug = canon.slugify(option)
        if slug in index.get("class", ()):
            out["feat_option"] = {"kind": "class", "id": index["class"][slug]}
        else:
            _note(notes,
                  "%s: the feat is printed %r, and %r resolves to no class "
                  "record; feat_option is not emitted and the option is "
                  "carried only by the printed string"
                  % (where, data["feat"], option))

    # --- the tool, or the choice of one ---------------------------------
    printed = _CHAPTER_REF[lang].sub("", data["tool_proficiency"]).strip()
    if _TOOL_CHOICE[lang].match(printed):
        haystack = canon.slugify(printed)
        matches = [
            slug for slug in index["tool"]
            if slug in haystack
        ]
        if not matches:
            raise DerivationError(
                "%s: tool choice %r names no tool record in this build"
                % (where, printed)
            )
        # Longest wins: "boite-de-jeux" must not lose to a shorter tool slug
        # that happens to be contained in the same sentence.
        longest = max(len(s) for s in matches)
        winners = sorted(s for s in matches if len(s) == longest)
        if len(winners) != 1:
            raise DerivationError(
                "%s: tool choice %r names %d tools at once (%s); which one is "
                "offered is not something this module may decide"
                % (where, printed, len(winners), ", ".join(winners))
            )
        out["tool_choice"] = {"from": [index["tool"][winners[0]]]}
    else:
        out["tool_id"] = _resolve(index, "tool", lang, printed, where + "#tool")

    return out


def _derive_species(data, lang, index, where, notes):
    out = {}

    printed = data["speed"]
    match = _SPEED[lang].match(printed)
    if not match:
        raise DerivationError(
            "%s: speed is %r, which is not a distance in the unit this layer "
            "prints" % (where, printed)
        )
    out["speed_m" if lang == "fr" else "speed_ft"] = _number(match.group(1), where)

    # The SRD lets the Human and the Tiefling be Medium OR Small, chosen at
    # character creation. That is a choice, not a size, and the contract has
    # no field for it — so nothing is emitted, and the omission is reported
    # rather than resolved by picking the first one printed.
    #
    # A size that fits NEITHER shape is a refusal, not another omission: the
    # two cases would otherwise be indistinguishable in the export, and "no
    # size_key" would stop meaning anything.
    printed = data["size"]
    match = _SIZE_HEAD[lang].match(printed)
    if match is None:
        raise DerivationError(
            "%s: size is %r, which does not begin with one of the %d size "
            "categories the SRD enumerates (%s)"
            % (where, printed, len(SIZE_KEYS[lang]),
               ", ".join(sorted(SIZE_KEYS[lang]))))
    if not _SIZE_ALTERNATIVE[lang].search(printed):
        out["size_key"] = _mapped(SIZE_KEYS, lang, match.group(1), "size", where)

    description = data.get("description") or ""

    match = _DARKVISION[lang].search(description)
    if match:
        out["senses"] = [{
            "id": "darkvision",
            "name": match.group(1),
            ("range_m" if lang == "fr" else "range_ft"):
                _number(match.group(2), where),
        }]

    match = _GRANTED_SKILL_LIST[lang].search(description)
    if match:
        options = [
            p.strip() for p in _TRAIT_SPLIT[lang].split(match.group(1)) if p.strip()
        ]
        out["granted_skill_choice"] = {
            "count": 1,
            "from": [_resolve(index, "skill", lang, o, where) for o in options],
        }
    elif _GRANTED_SKILL_ANY[lang].search(description):
        out["granted_skill_choice"] = {"count": 1, "from": "any"}

    return out


def _derive_weapon(data, lang, index, where, notes):
    printed = data["damage"]
    match = _DAMAGE.match(printed)
    if not match:
        raise DerivationError(
            "%s: damage is %r, which is neither 'NdM <type>' nor 'N <type>'"
            % (where, printed)
        )
    count, faces, type_name = match.groups()
    out = {
        "damage_type_key": _mapped(
            DAMAGE_TYPE_KEYS, lang, type_name, "damage", where),
    }
    if faces:
        out["damage_dice"] = "%sd%s" % (count, faces)
    else:
        # The blowgun deals a flat 1 point. "1d1" would be a die the SRD does
        # not print and a roll the table would actually make.
        out["damage_dice"] = None
        out["damage_flat"] = int(count)
    return out


def _derive_armor(data, lang, index, where, notes):
    printed = data["armor_class"]
    match = _AC[lang].match(printed)
    if not match:
        raise DerivationError(
            "%s: armor_class is %r, which is none of the three forms the SRD "
            "prints (a number, a number plus a Dex modifier, or a bonus)"
            % (where, printed)
        )
    if match.group("bonus") is not None:
        # The Shield says "+2". It is added to whatever AC you already have,
        # so it has no base and no Dex cap to speak of.
        return {"ac_base": None, "ac_bonus": int(match.group("bonus"))}

    base = int(match.group("base"))
    if "Dex" not in printed:
        cap = 0                       # heavy armour: Dexterity does not apply
    elif match.group("cap") is not None:
        cap = int(match.group("cap"))
    else:
        cap = None                    # light armour: uncapped
    return {"ac_base": base, "ac_dex_cap": cap}


def _derive_spell(data, lang, index, where, notes):
    """Only `concentration`, and deliberately only that.

    `duration` is a structured field the spell grammar already isolates, it is
    present on all 339 spells in both languages, and every spell that
    concentrates says so as the first word of it. That makes this a reading,
    not an inference.

    `cast_type` is NOT derived here. See the module docstring.
    """
    duration = data.get("duration")
    if not duration:
        raise DerivationError(
            "%s: the spell has no duration, so whether it concentrates cannot "
            "be read" % where)
    return {"concentration": duration.startswith(_CONCENTRATION)}


def _derive_tool(data, lang, index, where, notes):
    """The ability a tool is used with, keyed the same way a skill's is.

    Same notion, same field name, same canonical keys as the `skill` genre —
    `data.ability` stays the displayable word.
    """
    return {
        "ability_key": _mapped(
            ABILITY_KEYS, lang, data["ability"], "ability", where),
    }


_DERIVERS = {
    "armor": _derive_armor,
    "background": _derive_background,
    "class": _derive_class,
    "species": _derive_species,
    "spell": _derive_spell,
    "tool": _derive_tool,
    "weapon": _derive_weapon,
}


def derive(kind, lang, data, index, name="", notes=None):
    """Return the mechanical fields to add BESIDE `data`. Never modifies it.

    A kind with no deriver returns `{}` — that is the normal case, not a
    fallback: seven of the fourteen genres carry no mechanical field.

    `notes` is the channel for the one case the architect ruled must be
    reported rather than raised: an option the source prints that resolves to
    no record. Pass a list; it is appended to, never read.
    """
    deriver = _DERIVERS.get(kind)
    if deriver is None:
        return {}
    if lang not in ABILITY_KEYS:
        raise DerivationError(
            "no derivation grammar is calibrated for lang=%r; the mechanical "
            "fields cannot be produced for %s records" % (lang, kind)
        )
    out = deriver(
        data, lang, index, "srd:%s:%s:%s" % (kind, lang, name or "?"), notes)
    overlap = sorted(set(out) & set(data))
    if overlap:
        # The one thing this module must never do.
        raise DerivationError(
            "srd:%s:%s:%s: derivation would overwrite existing field(s) %s"
            % (kind, lang, name, ", ".join(overlap))
        )
    return out
