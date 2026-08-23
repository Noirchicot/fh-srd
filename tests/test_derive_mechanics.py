"""The derivation's refusals — the half of it that is supposed to say no.

`test_acceptance_derived_fields.py` proves the fields come out right on the
real base. This file proves the module **stops** on everything else, because a
derivation that guesses is worse than one that is missing: a wrong hit die or a
skill id pointing at nothing produces a character that is plausible and false.

Every case below is a `DerivationError`, and the message is checked for the
string a reader would need — the offending value, or the name that did not
resolve. "It raised something" is not the assertion; "it said what" is.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import derive_mechanics as dm  # noqa: E402

INDEX = {
    "skill": {
        "arcanes": "srd:skill:fr:arcanes",
        "histoire": "srd:skill:fr:histoire",
        "intuition": "srd:skill:fr:intuition",
    },
    "feat": {"vigilant": "srd:feat:fr:vigilant",
             "initie-a-la-magie": "srd:feat:fr:initie-a-la-magie"},
    "tool": {"outils-de-voleur": "srd:tool:fr:outils-de-voleur",
             "boite-de-jeux": "srd:tool:fr:boite-de-jeux"},
    "class": {"clerc": "srd:class:fr:clerc",
              "magicien": "srd:class:fr:magicien"},
    # The weapon pools resolve every property name against these, so that
    # "Légère" is a record and not a word this test happens to know.
    "weapon-property": {
        "finesse": "srd:weapon-property:fr:finesse",
        "lancer": "srd:weapon-property:fr:lancer",
        "legere": "srd:weapon-property:fr:legere",
    },
}


def _weapon(name, slug, category, weapon_range, properties):
    return {"name": name, "slug": slug, "data": {
        "weapon_category": category, "weapon_range": weapon_range,
        "properties": properties}}


# Five weapons instead of thirty-eight, built through the REAL catalogue
# reader: two simple, three martial, one of them ranged and Light. Enough for
# every clause the four proficiency sentences state.
CATALOGUE = dm.weapon_catalogue([
    _weapon("Dague", "dague", "simple", "melee",
            "Finesse, Lancer (portée 6/18), Légère"),
    _weapon("Massue", "massue", "simple", "melee", None),
    _weapon("Cimeterre", "cimeterre", "martial", "melee", "Finesse, Légère"),
    _weapon("Épée longue", "epee-longue", "martial", "melee", None),
    _weapon("Arbalète de poing", "arbalete-de-poing", "martial", "ranged",
            "Légère"),
], "fr", INDEX["weapon-property"])

CLASS = {
    "hit_point_die": "d6 par niveau de Magicien",
    "saving_throw_proficiencies": ["Intelligence", "Sagesse"],
    "skill_proficiencies": "2 au choix parmi : Arcanes et Histoire",
    "weapon_proficiencies": "Armes courantes",
}


def refuses(kind, data, must_say, note, lang="fr", index=None):
    try:
        dm.derive(kind, lang, data, INDEX if index is None else index, "T",
                  catalogue=CATALOGUE)
    except dm.DerivationError as exc:
        assert must_say in str(exc), (
            "%s: it refused, but the message does not contain %r:\n    %s"
            % (note, must_say, exc))
        return
    raise AssertionError("%s: no refusal — the derivation accepted %r"
                         % (note, data))


def main():
    # -- it does derive, when the source says so ---------------------------
    out = dm.derive("class", "fr", CLASS, INDEX, "Magicien",
                    catalogue=CATALOGUE)
    assert out["hit_die"] == 6, out
    assert out["saving_throw_keys"] == ["int", "wis"], out
    assert out["skill_choice"] == {
        "count": 2, "from": ["srd:skill:fr:arcanes", "srd:skill:fr:histoire"]}, out
    assert set(out) & set(CLASS) == set(), "it must not touch a printed field"
    print("  ok  it derives the Wizard's three fields from the printed strings")

    # -- a genre with no mechanical field gets nothing, and that is normal --
    assert dm.derive("monster", "fr", {"name": "x"}, INDEX, "x") == {}
    # ⚠️ `glossary` joined the derivers at lot 98, for `tag_key` alone. A null
    # tag yields a null key: 111 of the 152 entries carry no tag, and the
    # extractor refused to invent the closed list the SRD does not print. That
    # refusal is not filled in here either.
    assert dm.derive("glossary", "en", {"name": "x"}, INDEX, "x") == {"tag_key": None}
    assert dm.derive("glossary", "fr", {"name": "x", "tag": "etat"},
                     INDEX, "x") == {"tag_key": "condition"}
    print("  ok  the genres with no mechanical field get an empty add, and a "
          "glossary entry with no tag gets a null key rather than a guess")

    # -- the three fields added on the architect's second addendum ----------
    caster = dict(CLASS, features=[
        {"name": "Sorts", "level": 1, "description":
         "Caractéristique d’incantation. L’Intelligence est la "
         "caractéristique d’incantation de vos sorts de Magicien."}])
    assert dm.derive("class", "fr", caster, INDEX, "Magicien",
                     catalogue=CATALOGUE)["spellcasting_ability_key"] == "int"
    # a class that casts nothing says nothing, and gets nothing
    assert "spellcasting_ability_key" not in dm.derive(
        "class", "fr", dict(CLASS, features=[]), INDEX, "Barbare",
        catalogue=CATALOGUE)
    # and a class naming two would be a choice this module may not make
    refuses("class", dict(CLASS, features=[
        {"description": "Caractéristique d’incantation. La Sagesse est la "
                        "caractéristique d’incantation de vos sorts."},
        {"description": "Caractéristique d’incantation. Le Charisme est la "
                        "caractéristique d’incantation de vos sorts."}]),
            "two different spellcasting abilities"
            .replace("two", "2"), "a class naming two casting abilities")

    # ⚠️ A spell fixture carries its school and its classes since lot 98: the
    # deriver reads them, and it refuses a spell that has none rather than
    # shipping a null key. The printed French words stay in `school` and
    # `classes`; the English keys arrive beside them.
    assert dm.derive("spell", "fr",
                     {"duration": "Concentration, jusqu’à 1 heure",
                      "school": "invocation", "classes": ["Magicien", "Barde"]},
                     INDEX, "S") == {"concentration": True,
                                     "school_key": "conjuration",
                                     "class_keys": ["Wizard", "Bard"]}
    assert dm.derive("spell", "fr",
                     {"duration": "instantanée", "school": "evocation",
                      "classes": []},
                     INDEX, "S") == {"concentration": False,
                                     "school_key": "evocation",
                                     "class_keys": []}
    refuses("spell", {"duration": "", "school": "evocation"},
            "no duration", "a spell with no duration")
    # ⛔ `invocation` is French for CONJURATION, and `evocation` means the same
    # word in both. Five of the eight schools are spelled identically across the
    # two catalogues, which is exactly why sampling this field used to conclude
    # it was already stable.
    refuses("spell", {"duration": "instantanée", "school": "conjuration"},
            "conjuration", "an English school name in the French layer")

    assert dm.derive("tool", "fr", {"ability": "Sagesse"}, INDEX, "T") == {
        "ability_key": "wis"}
    refuses("tool", {"ability": "Sagacité"}, "Sagacité",
            "a tool ability outside the six")
    print("  ok  spellcasting ability, concentration and tool ability each "
          "come from the source or not at all")

    # -- an unknown hit die is not rounded to the nearest one --------------
    refuses("class", dict(CLASS, hit_point_die="d7 par niveau de Machin"),
            "d7", "a die outside {6,8,10,12}")
    refuses("class", dict(CLASS, hit_point_die="un dé par niveau"),
            "does not start with a die", "prose where a die was expected")

    # -- an ability the SRD does not have is not silently dropped ----------
    refuses("class", dict(CLASS, saving_throw_proficiencies=["Sagacité"]),
            "Sagacité", "an ability name outside the six")

    # -- a skill menu in a shape nobody calibrated stops the build ---------
    refuses("class", dict(CLASS, skill_proficiencies="deux compétences"),
            "matches neither", "an unrecognised skill menu")
    refuses("class", dict(CLASS,
                          skill_proficiencies="2 au choix parmi : Pilotage"),
            "Pilotage", "a menu offering a skill that is not a record")

    # -- a background whose feat, tool or skill does not resolve ----------
    background = {
        "ability_scores": ["Constitution", "Intelligence"],
        "feat": "Vigilant (cf. « Dons »)",
        "skill_proficiencies": ["Arcanes", "Histoire"],
        "tool_proficiency": "outils de voleur",
    }
    out = dm.derive("background", "fr", background, INDEX, "Criminel")
    assert out["feat_id"] == "srd:feat:fr:vigilant", out
    assert out["tool_id"] == "srd:tool:fr:outils-de-voleur", out
    assert out["ability_keys"] == ["con", "int"], out

    assert "feat_option" not in out, "a feat printed without an option gets none"

    # the feat's own parenthetical option is dropped from the NAME only to make
    # the join, and only after the full name has been tried — and it comes back
    # as a reference, never as the printed word
    out = dm.derive("background", "fr",
                    dict(background, feat="Initié à la magie (Clerc) (cf. « Dons »)"),
                    INDEX, "Acolyte")
    assert out["feat_id"] == "srd:feat:fr:initie-a-la-magie", out
    assert out["feat_option"] == {"kind": "class", "id": "srd:class:fr:clerc"}, out

    # an option that resolves to nothing is NOT emitted, and it is reported.
    # A feat_option pointing into the void would be worse than its absence.
    notes = []
    out = dm.derive("background", "fr",
                    dict(background, feat="Initié à la magie (Barghest) (cf. « Dons »)"),
                    INDEX, "Acolyte", notes)
    assert out["feat_id"] == "srd:feat:fr:initie-a-la-magie", out
    assert "feat_option" not in out, out
    assert len(notes) == 1, notes
    assert "Barghest" in notes[0] and "no class record" in notes[0], notes[0]

    # and it must have somewhere to be reported: swallowing the note is itself
    # the failure this guards against
    try:
        dm.derive("background", "fr",
                  dict(background, feat="Initié à la magie (Barghest) (cf. « Dons »)"),
                  INDEX, "Acolyte")
    except dm.DerivationError as exc:
        assert "nowhere to be reported" in str(exc), exc
    else:
        raise AssertionError("a note with no channel must not vanish")
    print("  ok  the feat option is a reference, absent when it resolves to "
          "nothing, and its absence is reported rather than swallowed")

    refuses("background", dict(background, feat="Chanceux (cf. « Dons »)"),
            "Chanceux", "a feat with no record")
    refuses("background", dict(background, tool_proficiency="lyre de concert"),
            "lyre de concert", "a tool with no record")
    refuses("background", dict(background, skill_proficiencies=["Pilotage"]),
            "Pilotage", "a background skill with no record")
    refuses("background",
            dict(background, tool_proficiency="Choisissez un ustensile quelconque"),
            "names no tool record", "a choice naming no tool at all")

    # -- a speed or size the layer does not print ------------------------
    species = {"speed": "9 m", "size": "M (moyenne)", "description": ""}
    out = dm.derive("species", "fr", species, INDEX, "Elfe")
    assert out == {"speed_m": 9, "size_key": "medium"}, out
    assert isinstance(out["speed_m"], int), "9 must not be exported as 9.0"
    assert dm.derive("species", "fr", dict(species, speed="10,50 m"),
                     INDEX, "Goliath")["speed_m"] == 10.5

    refuses("species", dict(species, speed="30 feet"),
            "30 feet", "an English speed in the French layer")
    refuses("species", dict(species, size="XL (énorme)"),
            "size", "a size category outside the six")

    # -- damage and armour class ------------------------------------------
    # ⚠️ `property_list` joined these two since lot 92. A weapon with no
    # `properties` string gets an EMPTY list, which is the answer for the three
    # weapons that carry none -- not a missing field.
    # ⛔ ENGLISH KEY, FRENCH PRINTED WORD. `damage` still reads "1d6 perforants"
    # -- that is what a page shows -- and `damage_type_key` is `piercing` on
    # both sides since lot 98. A field named `_key` that held French was the
    # most misleading thing in the layer.
    assert dm.derive("weapon", "fr", {"damage": "1d6 perforants"}, INDEX, "D") == {
        "damage_dice": "1d6", "damage_type_key": "piercing", "property_list": []}
    assert dm.derive("weapon", "fr", {"damage": "1 perforant"}, INDEX, "S") == {
        "damage_dice": None, "damage_flat": 1, "damage_type_key": "piercing",
        "property_list": []}
    assert dm.derive("weapon", "fr",
                     {"damage": "1d6 perforants", "mastery": "Renversement"},
                     INDEX, "D")["mastery_key"] == "Topple"
    assert dm.derive("weapon", "fr",
                     {"damage": "1d6 perforants",
                      "properties": "Finesse, Légère"}, INDEX, "D")["property_list"] == [
        {"key": "finesse", "label": "Finesse"}, {"key": "light", "label": "Légère"}]
    refuses("weapon", {"damage": "1d6 perforants", "properties": "Tournoyante"},
            "Tournoyante", "a weapon property the SRD does not print")
    refuses("weapon", {"damage": "1d6 psychiques"},
            "psychiques", "a damage type no SRD weapon deals")
    refuses("weapon", {"damage": "beaucoup"}, "beaucoup", "damage as prose")

    # ⛔ NO REQUIREMENT IS None, NOT ZERO. Ten of the thirteen armors ask for no
    # Strength at all, and a zero would read as "asks for Strength 0".
    assert dm.derive("armor", "fr", {"armor_class": "+2"}, INDEX, "B") == {
        "ac_base": None, "ac_bonus": 2, "strength_min": None}
    assert dm.derive("armor", "fr", {"armor_class": "16"}, INDEX, "C") == {
        "ac_base": 16, "ac_dex_cap": 0, "strength_min": None}
    # ⚠️ Three shapes for one value across the catalogues: `For 13` here,
    # `Str 13` in English, a bare `"13"` at 5eTools, an integer at Foundry. The
    # number is the only part that crosses, so it is the part that gets a field.
    assert dm.derive("armor", "fr",
                     {"armor_class": "16", "strength": "For 13"},
                     INDEX, "C")["strength_min"] == 13
    assert dm.derive("armor", "en",
                     {"armor_class": "16", "strength": "Str 15"},
                     INDEX, "C")["strength_min"] == 15
    refuses("armor", {"armor_class": "16", "strength": "beaucoup de Force"},
            "beaucoup de Force", "a Strength requirement in prose")
    refuses("armor", {"armor_class": "13 + modificateur de For"},
            "13 + modificateur de For", "an AC formula in an unknown shape")
    print("  ok  every unreadable value is refused, and the message names it")

    # -- a language with no calibrated grammar is refused, not defaulted ---
    refuses("class", CLASS, "no derivation grammar", "an uncalibrated language",
            lang="de")

    # -- and it can never overwrite ---------------------------------------
    refuses("weapon", {"damage": "1d6 perforants", "damage_dice": "9d9"},
            "would overwrite", "a record that already carries a derived name")
    print("  ok  it refuses an uncalibrated language and refuses to overwrite")

    # -- the index itself refuses an ambiguous join -----------------------
    try:
        dm.build_index("skill", "fr", [
            {"name": "Intuition", "slug": "intuition"},
            {"name": "intuition", "slug": "intuition-abc123"},
        ])
    except dm.DerivationError as exc:
        assert "ambiguous" in str(exc), exc
    else:
        raise AssertionError("two names slugifying alike must not be indexed")
    print("  ok  two records that slugify alike are refused as a join target")

    print("PASS test_derive_mechanics")


if __name__ == "__main__":
    main()
