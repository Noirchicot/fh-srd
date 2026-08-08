"""The acceptance test for the mechanical fields this lot exists to add.

> From the exports alone: a **Wizard** returns `hit_die: 6` and
> `saving_throw_keys: ["int","wis"]`; an **Elf** returns `speed_m: 9`; a
> **Sage** returns two `skill_ids` that really exist in the `skill` genre; a
> **Bard** returns `skill_choice: {count: 3, from: "any"}`; and the
> **Goliath** returns `speed_m: 10.5`. In French **and** in English.

So this file reads `exports/` and nothing else. It imports no parser, opens no
PDF, and imports the pipeline only for `canon.record_id` — the same joining rule
a consumer would use.

**It states values, not counts.** A guard that asserts `len(skill_ids) >= 2`
stays green while the stack returns two wrong identifiers, which is the defect
this project found on 2026-08-08. So every table below names what must be
there: the exact hit die of all twelve classes, the exact ability keys of all
twelve save pairs, the exact skills of all four backgrounds, the exact AC of
all thirteen armours. When a number moves, the test says which one.

**And it states what must NOT be there**, because the first rule of the lot is
that the derivation adds beside and never replaces: the printed strings the
public site renders are asserted still present, still saying what they said.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(ROOT, "exports", "srd")

sys.path.insert(0, os.path.join(ROOT, "src"))
import canon  # noqa: E402


def load(lang, kind):
    with open(os.path.join(EXPORTS, lang, kind + ".json"), encoding="utf-8") as fh:
        return {r["id"]: r for r in json.load(fh)["records"]}


def rid(kind, lang, slug):
    return canon.record_id("srd", kind, lang, slug)


# --------------------------------------------------------------------------
# What must be there. Every value written out, in both languages.
# --------------------------------------------------------------------------

# slug -> (hit_die, saving_throw_keys, skill_choice count)
CLASSES = {
    "fr": {
        "barbare":     (12, ["str", "con"], 2),
        "barde":       (8,  ["dex", "cha"], 3),
        "clerc":       (8,  ["wis", "cha"], 2),
        "druide":      (8,  ["int", "wis"], 2),
        "ensorceleur": (6,  ["con", "cha"], 2),
        "guerrier":    (10, ["str", "con"], 2),
        "magicien":    (6,  ["int", "wis"], 2),
        "moine":       (8,  ["str", "dex"], 2),
        "occultiste":  (8,  ["wis", "cha"], 2),
        "paladin":     (10, ["wis", "cha"], 2),
        "rodeur":      (10, ["str", "dex"], 3),
        "roublard":    (8,  ["dex", "int"], 4),
    },
    "en": {
        "barbarian": (12, ["str", "con"], 2),
        "bard":      (8,  ["dex", "cha"], 3),
        "cleric":    (8,  ["wis", "cha"], 2),
        "druid":     (8,  ["int", "wis"], 2),
        "fighter":   (10, ["str", "con"], 2),
        "monk":      (8,  ["str", "dex"], 2),
        "paladin":   (10, ["wis", "cha"], 2),
        "ranger":    (10, ["str", "dex"], 3),
        "rogue":     (8,  ["dex", "int"], 4),
        "sorcerer":  (6,  ["con", "cha"], 2),
        "warlock":   (8,  ["wis", "cha"], 2),
        "wizard":    (6,  ["int", "wis"], 2),
    },
}

# The one class whose menu the SRD does not list — arbitrated, not a defect.
OPEN_MENU = {"fr": "barde", "en": "bard"}

# slug -> (ability_keys, feat slug, skill slugs, tool slug or None)
BACKGROUNDS = {
    "fr": {
        "acolyte":  (["int", "wis", "cha"], "initie-a-la-magie",
                     ["intuition", "religion"], "materiel-de-calligraphe"),
        "criminel": (["dex", "con", "int"], "vigilant",
                     ["discretion", "escamotage"], "outils-de-voleur"),
        "sage":     (["con", "int", "wis"], "initie-a-la-magie",
                     ["arcanes", "histoire"], "materiel-de-calligraphe"),
        "soldat":   (["str", "dex", "con"], "sauvagerie-martiale",
                     ["athletisme", "intimidation"], None),
    },
    "en": {
        "acolyte":  (["int", "wis", "cha"], "magic-initiate",
                     ["insight", "religion"], "calligrapher-s-supplies"),
        "criminal": (["dex", "con", "int"], "alert",
                     ["sleight-of-hand", "stealth"], "thieves-tools"),
        "sage":     (["con", "int", "wis"], "magic-initiate",
                     ["arcana", "history"], "calligrapher-s-supplies"),
        "soldier":  (["str", "dex", "con"], "savage-attacker",
                     ["athletics", "intimidation"], None),
    },
}

# The one background that chooses its tool instead of being granted one —
# arbitrated. slug -> the tool the choice is made within.
TOOL_CHOICE = {"fr": ("soldat", "boite-de-jeux"), "en": ("soldier", "gaming-set")}

# slug -> (speed in the layer's own unit, size_key or None, darkvision range
#          in the layer's own unit or None)
SPECIES = {
    "fr": {
        "drakeide":  (9,    "medium", 18),
        "elfe":      (9,    "medium", 18),
        "gnome":     (9,    "small",  18),
        "goliath":   (10.5, "medium", None),
        "halfelin":  (9,    "small",  None),
        "humain":    (9,    None,     None),
        "nain":      (9,    "medium", 36),
        "orc":       (9,    "medium", 36),
        "tieffelin": (9,    None,     18),
    },
    "en": {
        "dragonborn": (30, "medium", 60),
        "dwarf":      (30, "medium", 120),
        "elf":        (30, "medium", 60),
        "gnome":      (30, "small",  60),
        "goliath":    (35, "medium", None),
        "halfling":   (30, "small",  None),
        "human":      (30, None,     None),
        "orc":        (30, "medium", 120),
        "tiefling":   (30, None,     60),
    },
}
SPEED_FIELD = {"fr": "speed_m", "en": "speed_ft"}
RANGE_FIELD = {"fr": "range_m", "en": "range_ft"}

# The two species the SRD lets be Medium OR Small. No size is emitted for them
# — the source states a choice, and a choice is not a size.
SIZE_IS_A_CHOICE = {"fr": {"humain", "tieffelin"}, "en": {"human", "tiefling"}}

# The two species that are granted a skill. slug -> the skills offered, or
# "any" when the source grants a free choice.
GRANTED_SKILL = {
    "fr": {"elfe": ["intuition", "perception", "survie"], "humain": "any"},
    "en": {"elf": ["insight", "perception", "survival"], "human": "any"},
}

# slug -> (ac_base, ac_dex_cap, ac_bonus). `...` means the field must be absent.
ARMOR = {
    "fr": {
        "armure-matelassee":     (11, None, ...),
        "armure-de-cuir":        (11, None, ...),
        "armure-de-cuir-cloute": (12, None, ...),
        "armure-de-peaux":       (12, 2,    ...),
        "chemise-de-mailles":    (13, 2,    ...),
        "armure-d-ecailles":     (14, 2,    ...),
        "cuirasse":              (14, 2,    ...),
        "demi-plate":            (15, 2,    ...),
        "broigne":               (14, 0,    ...),
        "cotte-de-mailles":      (16, 0,    ...),
        "clibanion":             (17, 0,    ...),
        "harnois":               (18, 0,    ...),
        "bouclier":              (None, ..., 2),
    },
    "en": {
        "padded-armor":          (11, None, ...),
        "leather-armor":         (11, None, ...),
        "studded-leather-armor": (12, None, ...),
        "hide-armor":            (12, 2,    ...),
        "chain-shirt":           (13, 2,    ...),
        "scale-mail":            (14, 2,    ...),
        "breastplate":           (14, 2,    ...),
        "half-plate-armor":      (15, 2,    ...),
        "ring-mail":             (14, 0,    ...),
        "chain-mail":            (16, 0,    ...),
        "splint-armor":          (17, 0,    ...),
        "plate-armor":           (18, 0,    ...),
        "shield":                (None, ..., 2),
    },
}

# A sample of weapons spanning every damage type and both damage shapes.
# slug -> (damage_dice, damage_flat or ..., damage_type_key)
WEAPONS = {
    "fr": {
        "dague":             ("1d4",  ..., "perforant"),
        "epee-longue":       ("1d8",  ..., "tranchant"),
        "epee-a-deux-mains": ("2d6",  ..., "tranchant"),
        "masse-d-armes":     ("1d6",  ..., "contondant"),
        "hache-a-deux-mains":("1d12", ..., "tranchant"),
        "sarbacane":         (None,   1,   "perforant"),
    },
    "en": {
        "dagger":     ("1d4",  ..., "piercing"),
        "longsword":  ("1d8",  ..., "slashing"),
        "greatsword": ("2d6",  ..., "slashing"),
        "mace":       ("1d6",  ..., "bludgeoning"),
        "greataxe":   ("1d12", ..., "slashing"),
        "blowgun":    (None,   1,   "piercing"),
    },
}

# The printed fields the derivation must NOT have touched: kind -> the fields
# a reader (and the attribution suite, and the public site) still expects.
PRINTED = {
    "class": ("hit_point_die", "saving_throw_proficiencies", "skill_proficiencies"),
    "background": ("ability_scores", "feat", "skill_proficiencies", "tool_proficiency"),
    "species": ("size", "speed", "description"),
    "weapon": ("damage",),
    "armor": ("armor_class",),
}

ABILITY_KEYS = {"str", "dex", "con", "int", "wis", "cha"}
SIZE_KEYS = {"tiny", "small", "medium", "large", "huge", "gargantuan"}


def check_classes(lang):
    classes = load(lang, "class")
    skills = load(lang, "skill")
    assert set(classes) == {rid("class", lang, s) for s in CLASSES[lang]}, (
        "the twelve classes are not the twelve expected: %s"
        % sorted(classes))

    for slug, (die, saves, count) in sorted(CLASSES[lang].items()):
        data = classes[rid("class", lang, slug)]["data"]
        assert data["hit_die"] == die, (
            "%s/%s: hit_die is %r, expected %r (printed: %r)"
            % (lang, slug, data["hit_die"], die, data["hit_point_die"]))
        assert data["saving_throw_keys"] == saves, (
            "%s/%s: saving_throw_keys is %r, expected %r (printed: %r)"
            % (lang, slug, data["saving_throw_keys"], saves,
               data["saving_throw_proficiencies"]))
        assert set(saves) <= ABILITY_KEYS, saves

        choice = data["skill_choice"]
        assert choice["count"] == count, (
            "%s/%s: skill_choice count is %r, expected %r"
            % (lang, slug, choice["count"], count))
        if slug == OPEN_MENU[lang]:
            # ARBITRATED (contract §4, B1): the SRD gives the Bard no list.
            assert choice["from"] == "any", (
                "%s/%s: the Bard chooses from any skill; a list here would be "
                "a list the source does not print: %r" % (lang, slug, choice))
        else:
            assert isinstance(choice["from"], list) and choice["from"], choice
            for skill_id in choice["from"]:
                assert skill_id in skills, (
                    "%s/%s: skill_choice offers %r, which is not a skill "
                    "record" % (lang, slug, skill_id))
            assert len(set(choice["from"])) == len(choice["from"]), choice
    print("  ok  [%s] twelve classes: every hit die, save pair and skill menu "
          "is the value named in this file" % lang)


def check_backgrounds(lang):
    backgrounds = load(lang, "background")
    skills = load(lang, "skill")
    feats = load(lang, "feat")
    tools = load(lang, "tool")
    assert set(backgrounds) == {rid("background", lang, s) for s in BACKGROUNDS[lang]}

    for slug, (abilities, feat, skill_slugs, tool) in sorted(
            BACKGROUNDS[lang].items()):
        data = backgrounds[rid("background", lang, slug)]["data"]

        assert data["ability_keys"] == abilities, (
            "%s/%s: ability_keys is %r, expected %r (printed: %r)"
            % (lang, slug, data["ability_keys"], abilities,
               data["ability_scores"]))

        want = [rid("skill", lang, s) for s in skill_slugs]
        assert data["skill_ids"] == want, (
            "%s/%s: skill_ids is %r, expected %r"
            % (lang, slug, data["skill_ids"], want))
        for skill_id in data["skill_ids"]:
            assert skill_id in skills, (
                "%s/%s: skill_ids names %r, which is not a skill record"
                % (lang, slug, skill_id))
            assert skills[skill_id]["data"]["ability_key"], skill_id

        assert data["feat_id"] == rid("feat", lang, feat), (
            "%s/%s: feat_id is %r, expected the %r feat (printed: %r)"
            % (lang, slug, data["feat_id"], feat, data["feat"]))
        assert data["feat_id"] in feats, data["feat_id"]

        if tool is None:
            # ARBITRATED (contract §4, B2): the Soldier chooses a kind of
            # Gaming Set. A choice is not a granted proficiency.
            assert "tool_id" not in data, (
                "%s/%s: the source says 'choose', so no tool is granted: %r"
                % (lang, slug, data.get("tool_id")))
            choice_slug, within = TOOL_CHOICE[lang]
            assert slug == choice_slug, slug
            assert data["tool_choice"] == {"from": [rid("tool", lang, within)]}, (
                "%s/%s: tool_choice is %r, expected the choice to be made "
                "within %r" % (lang, slug, data["tool_choice"], within))
            assert rid("tool", lang, within) in tools
        else:
            assert data["tool_id"] == rid("tool", lang, tool), (
                "%s/%s: tool_id is %r, expected %r (printed: %r)"
                % (lang, slug, data["tool_id"], tool, data["tool_proficiency"]))
            assert data["tool_id"] in tools, data["tool_id"]
            assert "tool_choice" not in data, data
    print("  ok  [%s] four backgrounds: abilities, feat, tool and both skills "
          "each resolve to a record that exists" % lang)


def check_species(lang):
    species = load(lang, "species")
    skills = load(lang, "skill")
    assert set(species) == {rid("species", lang, s) for s in SPECIES[lang]}

    for slug, (speed, size, darkvision) in sorted(SPECIES[lang].items()):
        data = species[rid("species", lang, slug)]["data"]

        assert data[SPEED_FIELD[lang]] == speed, (
            "%s/%s: %s is %r, expected %r (printed: %r)"
            % (lang, slug, SPEED_FIELD[lang], data[SPEED_FIELD[lang]], speed,
               data["speed"]))

        if size is None:
            assert slug in SIZE_IS_A_CHOICE[lang], slug
            assert "size_key" not in data, (
                "%s/%s: the SRD offers two sizes here; emitting one would be "
                "picking for the player: %r" % (lang, slug, data.get("size_key")))
        else:
            assert data["size_key"] == size, (
                "%s/%s: size_key is %r, expected %r (printed: %r)"
                % (lang, slug, data.get("size_key"), size, data["size"]))
            assert size in SIZE_KEYS

        if darkvision is None:
            assert "senses" not in data, (
                "%s/%s: this species has no Darkvision trait in the SRD, so it "
                "must carry no sense: %r" % (lang, slug, data.get("senses")))
        else:
            assert data["senses"] == [
                {"id": "darkvision", RANGE_FIELD[lang]: darkvision}], (
                "%s/%s: senses is %r, expected Darkvision at %r"
                % (lang, slug, data.get("senses"), darkvision))

        granted = GRANTED_SKILL[lang].get(slug)
        if granted is None:
            assert "granted_skill_choice" not in data, (lang, slug, data)
        elif granted == "any":
            assert data["granted_skill_choice"] == {"count": 1, "from": "any"}, (
                "%s/%s: %r" % (lang, slug, data.get("granted_skill_choice")))
        else:
            want = [rid("skill", lang, s) for s in granted]
            assert data["granted_skill_choice"] == {"count": 1, "from": want}, (
                "%s/%s: granted_skill_choice is %r, expected %r"
                % (lang, slug, data.get("granted_skill_choice"), want))
            for skill_id in want:
                assert skill_id in skills, skill_id
    print("  ok  [%s] nine species: speed, size, Darkvision and granted skill "
          "are each the value named in this file" % lang)


def check_armor(lang):
    armor = load(lang, "armor")
    assert set(armor) == {rid("armor", lang, s) for s in ARMOR[lang]}
    for slug, (base, cap, bonus) in sorted(ARMOR[lang].items()):
        data = armor[rid("armor", lang, slug)]["data"]
        assert data["ac_base"] == base, (
            "%s/%s: ac_base is %r, expected %r (printed: %r)"
            % (lang, slug, data["ac_base"], base, data["armor_class"]))
        if cap is ...:
            # ARBITRATED (contract §4, B4): the Shield is a modifier. It has
            # no base to cap Dexterity against.
            assert "ac_dex_cap" not in data, (lang, slug, data)
        else:
            assert data["ac_dex_cap"] == cap, (
                "%s/%s: ac_dex_cap is %r, expected %r (printed: %r)"
                % (lang, slug, data.get("ac_dex_cap"), cap, data["armor_class"]))
        if bonus is ...:
            assert "ac_bonus" not in data, (lang, slug, data)
        else:
            assert data["ac_bonus"] == bonus, (lang, slug, data)
    print("  ok  [%s] thirteen armours: every base, Dex cap and bonus is the "
          "value named in this file" % lang)


def check_weapons(lang):
    weapons = load(lang, "weapon")
    assert len(weapons) == 38, len(weapons)
    for slug, (dice, flat, type_key) in sorted(WEAPONS[lang].items()):
        data = weapons[rid("weapon", lang, slug)]["data"]
        assert data["damage_dice"] == dice, (
            "%s/%s: damage_dice is %r, expected %r (printed: %r)"
            % (lang, slug, data["damage_dice"], dice, data["damage"]))
        assert data["damage_type_key"] == type_key, (
            "%s/%s: damage_type_key is %r, expected %r (printed: %r)"
            % (lang, slug, data["damage_type_key"], type_key, data["damage"]))
        if flat is ...:
            assert "damage_flat" not in data, (lang, slug, data)
        else:
            # ARBITRATED (contract §4, B3): the Blowgun deals a flat 1. "1d1"
            # would be a die the table would actually roll.
            assert data["damage_dice"] is None, (lang, slug, data)
            assert data["damage_flat"] == flat, (lang, slug, data)

    # every weapon in the base carries the three fields, with a type from the
    # language's own closed set
    types = {r["data"]["damage_type_key"] for r in weapons.values()}
    assert len(types) == 3, types
    flat_damage = sorted(
        r["id"] for r in weapons.values() if r["data"]["damage_dice"] is None)
    assert flat_damage == [rid("weapon", lang, "sarbacane" if lang == "fr"
                               else "blowgun")], flat_damage
    print("  ok  [%s] thirty-eight weapons: three damage types, and exactly "
          "one weapon without a die" % lang)


def check_nothing_was_replaced(lang):
    """The first rule of this lot: added beside, never instead of."""
    for kind, fields in sorted(PRINTED.items()):
        for record in load(lang, kind).values():
            for field in fields:
                assert field in record["data"], (
                    "%s: %s lost its printed field %r — the derivation must "
                    "add beside, never replace" % (lang, record["id"], field))
                assert record["data"][field] not in (None, "", []), (
                    "%s: %s emptied its printed field %r"
                    % (lang, record["id"], field))
    # spelled out on the record the contract itself quotes
    wizard = load(lang, "class")[
        rid("class", lang, "magicien" if lang == "fr" else "wizard")]["data"]
    expected = ("d6 par niveau de Magicien" if lang == "fr"
                else "D6 per Wizard level")
    assert wizard["hit_point_die"] == expected, wizard["hit_point_die"]
    assert wizard["hit_die"] == 6, wizard["hit_die"]
    print("  ok  [%s] every printed field the site renders is still present "
          "and unchanged beside its mechanical twin" % lang)


def negative_control():
    """The checks above must be able to fail."""
    fr_wizard = load("fr", "class")[rid("class", "fr", "magicien")]["data"]
    assert fr_wizard["saving_throw_keys"] != ["for", "sag"], (
        "the French saves must be the canonical keys the contract names, not "
        "the French layer's own ability abbreviations")
    assert fr_wizard["hit_die"] != 8, "a d8 Wizard would mean the die was read "
    "from the wrong class"

    # a skill the SRD does not have must not resolve, so the joins above are
    # not vacuously true
    skills = load("fr", "skill")
    assert rid("skill", "fr", "pilotage") not in skills

    # the Goliath's speed is the source's decimal comma, not a truncation
    goliath = load("fr", "species")[rid("species", "fr", "goliath")]["data"]
    assert goliath["speed_m"] == 10.5 and goliath["speed_m"] != 10, goliath

    # the Shield must not have been given a base AC of 2
    shield = load("en", "armor")[rid("armor", "en", "shield")]["data"]
    assert shield["ac_base"] is None and shield["ac_bonus"] == 2, shield

    # the Blowgun must not have been written as a die
    blowgun = load("en", "weapon")[rid("weapon", "en", "blowgun")]["data"]
    assert blowgun["damage_dice"] != "1d1", blowgun
    print("  ok  negative control: French saves are not 'for/sag', an unknown "
          "skill does not resolve, 10,50 m is not 10, the Shield has no base "
          "AC and the Blowgun has no die")


def main():
    for lang in ("fr", "en"):
        check_classes(lang)
        check_backgrounds(lang)
        check_species(lang)
        check_armor(lang)
        check_weapons(lang)
        check_nothing_was_replaced(lang)
    negative_control()
    print("PASS test_acceptance_derived_fields")


if __name__ == "__main__":
    main()
