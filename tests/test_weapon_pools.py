"""WHICH weapons a class may choose from — the pools, and the guards.

THE HOLE THIS FILE CLOSES: `class.weapon_mastery_count` said a Barbarian gets
**two** weapon masteries and nothing anywhere said **two of what**. The answer
lived in prose, in three different sentences, and a builder cannot read prose.
Lot 19 shipped the number; this is the set it counts.

Two fields, and they are not the same field:

  * `weapon_proficiency_ids` — every weapon the class may use. TWELVE classes.
  * `weapon_mastery_from`    — the weapons its level-1 feature may unlock a
    mastery on. FIVE classes, and for three of them it IS the pool above.

⛔ NEITHER IS A TABLE OF FIVE CLASSES WRITTEN BY HAND. What the module holds
is the reading of two closed sets of SENTENCES; the membership comes from the
`weapon` records of the same build. This file proves both halves: that the
sentences are read (unit), and that what comes out of a real build is the set
the SRD's own weapon table produces when you recompute it from the other side
(acceptance).

Run: python3 tests/test_weapon_pools.py
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(ROOT, "exports", "srd")

sys.path.insert(0, os.path.join(ROOT, "src"))

import canon  # noqa: E402
import derive_mechanics as dm  # noqa: E402

# The twelve classes, in each language's own spelling, with the size of each
# pool. Stated here so the test fails for the right reason instead of agreeing
# with whatever the export happens to hold.
#
#   38 = every weapon · 28 = the melee ones · 19 = 14 simple + 5 martial
#   with Finesse or Light · 17 = 14 simple + 3 martial with Light · 14 = simple
EXPECTED = {
    "en": {
        "barbarian": (38, 28), "bard": (14, None), "cleric": (14, None),
        "druid": (14, None), "fighter": (38, 38), "monk": (17, None),
        "paladin": (38, 38), "ranger": (38, 38), "rogue": (19, 19),
        "sorcerer": (14, None), "warlock": (14, None), "wizard": (14, None),
    },
    "fr": {
        "barbare": (38, 28), "barde": (14, None), "clerc": (14, None),
        "druide": (14, None), "ensorceleur": (14, None), "guerrier": (38, 38),
        "magicien": (14, None), "moine": (17, None), "occultiste": (14, None),
        "paladin": (38, 38), "rodeur": (38, 38), "roublard": (19, 19),
    },
}

# ⚠️ THE WEAPON A HAND-WRITTEN TABLE GETS WRONG. The Hand Crossbow is a
# MARTIAL RANGED weapon that carries Light — so it is in the Rogue's pool (its
# sentence asks for a property, not a range) and out of the Barbarian's (whose
# feature asks for Melee). Named here because it is the single row that tells
# a derived pool from a recopied one.
HAND_CROSSBOW = {"en": "hand-crossbow", "fr": "arbalete-de-poing"}
ROGUE = {"en": "rogue", "fr": "roublard"}
BARBARIAN = {"en": "barbarian", "fr": "barbare"}

# Property names as each language prints them, for the recount below. Read off
# the `weapon-property` records, never translated across.
LIGHT = {"en": "Light", "fr": "Légère"}
FINESSE = {"en": "Finesse", "fr": "Finesse"}


def _weapon(name, slug, category, weapon_range, properties):
    return {"name": name, "slug": slug, "data": {
        "weapon_category": category, "weapon_range": weapon_range,
        "properties": properties}}


PROPERTY_INDEX = {
    "en": {"finesse": "srd:weapon-property:en:finesse",
           "light": "srd:weapon-property:en:light",
           "thrown": "srd:weapon-property:en:thrown",
           "versatile": "srd:weapon-property:en:versatile"},
    "fr": {"finesse": "srd:weapon-property:fr:finesse",
           "legere": "srd:weapon-property:fr:legere",
           "lancer": "srd:weapon-property:fr:lancer",
           "polyvalente": "srd:weapon-property:fr:polyvalente"},
}

# A miniature weapon table, built through the REAL catalogue reader: 2 simple
# melee, 1 simple ranged, 2 martial melee (one Finesse+Light), 1 martial
# ranged carrying Light — the Hand Crossbow's shape, in small.
SMALL = {
    "en": dm.weapon_catalogue([
        _weapon("Dagger", "dagger", "simple", "melee",
                "Finesse, Light, Thrown (Range 20/60)"),
        _weapon("Mace", "mace", "simple", "melee", None),
        _weapon("Sling", "sling", "simple", "ranged", None),
        _weapon("Longsword", "longsword", "martial", "melee",
                "Versatile (1d10)"),
        _weapon("Scimitar", "scimitar", "martial", "melee", "Finesse, Light"),
        _weapon("Hand Crossbow", "hand-crossbow", "martial", "ranged", "Light"),
    ], "en", PROPERTY_INDEX["en"]),
    "fr": dm.weapon_catalogue([
        _weapon("Dague", "dague", "simple", "melee",
                "Finesse, Lancer (portée 6/18), Légère"),
        _weapon("Masse d’armes", "masse-d-armes", "simple", "melee", None),
        _weapon("Fronde", "fronde", "simple", "ranged", None),
        _weapon("Épée longue", "epee-longue", "martial", "melee",
                "Polyvalente (1d10)"),
        _weapon("Cimeterre", "cimeterre", "martial", "melee", "Finesse, Légère"),
        _weapon("Arbalète de poing", "arbalete-de-poing", "martial", "ranged",
                "Légère"),
    ], "fr", PROPERTY_INDEX["fr"]),
}

# The four sentences, per language, with what the miniature table yields:
# simple = 3 · simple+martial = 6 · +Light martial = 5 · +Finesse|Light = 5.
SMALL_POOL = {
    "en": {
        "Simple weapons": 3,
        "Simple and Martial weapons": 6,
        "Simple weapons and Martial weapons that have the Light property": 5,
        "Simple weapons and Martial weapons that have the Finesse or Light "
        "property": 5,
    },
    "fr": {
        "Armes courantes": 3,
        "Armes courantes et armes de guerre": 6,
        "Armes courantes ; et armes de guerre dotées de la propriété Légère": 5,
        "Armes courantes et armes de guerre dotées de la propriété Finesse ou "
        "Légère": 5,
    },
}

# The three restriction forms, in the prose each class actually prints.
MASTERY_PROSE = {
    "en": {
        "melee": "Your training with weapons allows you to use the mastery "
                 "properties of two kinds of Simple or Martial Melee weapons "
                 "of your choice, such as Greataxes and Handaxes.",
        "as-printed": "Your training with weapons allows you to use the "
                      "mastery properties of three kinds of Simple or Martial "
                      "weapons of your choice.",
        "proficiency": "Your training with weapons allows you to use the "
                       "mastery properties of two kinds of weapons of your "
                       "choice with which you have proficiency, such as "
                       "Longswords and Javelins.",
    },
    "fr": {
        "melee": "Votre entraînement martial vous permet de recourir à la "
                 "botte de deux types d’arme de corps à corps courante ou de "
                 "guerre de votre choix, par exemple la hache à deux mains.",
        "as-printed": "Votre entraînement martial vous permet de recourir à "
                      "la botte de trois types d’arme courante ou de guerre "
                      "de votre choix.",
        "proficiency": "Votre entraînement martial vous permet de recourir à "
                       "la propriété Botte de deux types d’arme de votre "
                       "choix parmi celles dont vous avez la maîtrise, par "
                       "exemple l’épée longue et la javeline.",
    },
}

ALL_WEAPONS = {"en": "Simple and Martial weapons",
               "fr": "Armes courantes et armes de guerre"}


def klass(lang, proficiencies, mastery_prose=None, name="Test"):
    """One `class` record, shaped as the parsers hand them to the derivation."""
    features = []
    if mastery_prose is not None:
        features.append({"name": dm.WEAPON_MASTERY_FEATURE[lang], "level": 1,
                         "description": mastery_prose})
    return {"weapon_proficiencies": proficiencies, "features": features}


def derive(lang, data, catalogue=None, index=None, name="Test"):
    return dm.derive("class", lang, dict(
        data,
        hit_point_die={"en": "D8 per Test level",
                       "fr": "d8 par niveau de Test"}[lang],
        saving_throw_proficiencies=[],
        skill_proficiencies={"en": "Choose any 2 skills",
                             "fr": "2 compétences au choix"}[lang],
    ), index or {"weapon-property": PROPERTY_INDEX[lang]}, name,
        catalogue=catalogue if catalogue is not None else SMALL[lang])


def refuses(fn, needle, why, error=dm.DerivationError):
    try:
        fn()
    except error as exc:
        assert needle in str(exc), "wrong refusal (%r not in): %s" % (needle, exc)
        print("  ok  %s" % why)
        return
    raise AssertionError("no refusal: %s" % why)


def candidate(lang, slug, pool, count=None, mastery=None):
    data = {"weapon_proficiency_ids": list(pool)}
    if count is not None:
        data["weapon_mastery_count"] = count
    if mastery is not None:
        data["weapon_mastery_from"] = list(mastery)
    return {"slug": slug, "name": slug.capitalize(), "data": data}


# --------------------------------------------------------------------------
# unit — the sentences are READ, and everything else is refused
# --------------------------------------------------------------------------


def unit_properties():
    """A property's arguments are not another property."""
    assert dm.split_printed_properties(
        "Ammunition (Range 30/120; Bolt), Light, Loading") == [
            "Ammunition", "Light", "Loading"]
    assert dm.split_printed_properties(
        "Chargement, Deux mains, Munitions (portée 24/96 ; flèches)") == [
            "Chargement", "Deux mains", "Munitions"]
    assert dm.split_printed_properties(
        "Heavy, Reach, Two-Handed (unless mounted)") == [
            "Heavy", "Reach", "Two-Handed"]
    assert dm.split_printed_properties("") == []
    print("  ok  a property's parenthesis is its argument, not a second "
          "property — in both languages' punctuation")

    refuses(lambda: dm.weapon_catalogue(
        [_weapon("Parrying Dagger", "parrying-dagger", "simple", "melee",
                 "Parrying")], "en", PROPERTY_INDEX["en"]),
        "Parrying",
        "a weapon printed with a property that resolves to no record refuses, "
        "naming it")

    refuses(lambda: dm.weapon_catalogue(
        [_weapon("Siege Ram", "siege-ram", "exotic", "melee", None)],
        "en", PROPERTY_INDEX["en"]),
        "exotic",
        "a weapon category outside {simple, martial} refuses, naming it")

    refuses(lambda: dm.weapon_catalogue(
        [_weapon("Dagger", "dagger", "simple", "thrown-only", None)],
        "en", PROPERTY_INDEX["en"]),
        "thrown-only",
        "a weapon range outside {melee, ranged} refuses, naming it")

    refuses(lambda: dm.weapon_catalogue(
        [_weapon("Dagger", "dagger", "simple", "melee", "Light")], "en", {}),
        "indexed none",
        "a catalogue with no weapon-property records to resolve against "
        "refuses rather than match nothing")


def unit_proficiency():
    for lang, sentences in sorted(SMALL_POOL.items()):
        assert set(sentences) == set(dm.WEAPON_PROFICIENCIES[lang]), (
            "the four sentences this test states and the four the module "
            "reads are not the same set (%s)" % lang)
        for printed, size in sorted(sentences.items()):
            ids = derive(lang, klass(lang, printed))["weapon_proficiency_ids"]
            assert len(ids) == size, (lang, printed, len(ids), size)
            assert ids == sorted(ids), "a pool is exported sorted by id"
            assert len(set(ids)) == len(ids), "a weapon appears once"
    print("  ok  the four proficiency sentences of each language are read, "
          "and only those four (8 sentences, 2 languages)")

    # ⚠️ THE MONK'S FRENCH SEMICOLON. "Armes courantes ; et armes de guerre…"
    # is not the Rogue's sentence with a word changed; keying on the printed
    # string reads both, and neither falls back on the other.
    monk = "Armes courantes ; et armes de guerre dotées de la propriété Légère"
    assert monk in dm.WEAPON_PROFICIENCIES["fr"]
    assert len(derive("fr", klass("fr", monk))["weapon_proficiency_ids"]) == 5

    refuses(lambda: derive("en", klass("en", "Simple and Exotic weapons")),
            "Simple and Exotic weapons",
            "a fifth proficiency sentence refuses, quoting itself")
    refuses(lambda: derive("en", klass("en", None)),
            "prints no `weapon_proficiencies`",
            "a class printing no proficiency sentence at all refuses")
    refuses(lambda: derive("en", klass("en", "Simple weapons"), catalogue=()),
            "no weapon catalogue",
            "a build with no weapons refuses instead of an empty pool")

    # GUARD 1 — the empty pool, which is the defect that hides best.
    martial_only = dm.weapon_catalogue(
        [_weapon("Longsword", "longsword", "martial", "melee", None)],
        "en", PROPERTY_INDEX["en"])
    refuses(lambda: derive("en", klass("en", "Simple weapons"),
                           catalogue=martial_only),
            "selected NO weapon",
            "GUARD 1: a pool that comes back empty refuses (the field would "
            "otherwise be present, and the builder would offer nothing)")

    # GUARD 2 — a narrowing that narrows nothing.
    all_light = dm.weapon_catalogue([
        _weapon("Dagger", "dagger", "simple", "melee", "Light"),
        _weapon("Scimitar", "scimitar", "martial", "melee", "Light"),
        _weapon("Shortsword", "shortsword", "martial", "melee", "Light"),
    ], "en", PROPERTY_INDEX["en"])
    refuses(lambda: derive("en", klass(
        "en", "Simple weapons and Martial weapons that have the Light "
              "property"), catalogue=all_light),
            "removed nothing",
            "GUARD 2a: a property restriction that selects every Martial "
            "weapon refuses — a lost restriction looks like a bigger shop")


def unit_mastery():
    for lang, prose in sorted(MASTERY_PROSE.items()):
        sizes = {}
        for form, text in sorted(prose.items()):
            out = derive(lang, klass(lang, ALL_WEAPONS[lang], text))
            sizes[form] = len(out["weapon_mastery_from"])
        # 6 weapons in the miniature table, 4 of them melee.
        assert sizes == {"melee": 4, "as-printed": 6, "proficiency": 6}, (
            lang, sizes)
    print("  ok  the three restriction forms are read in both languages: "
          "Melee narrows, `Simple or Martial` does not, and `with which you "
          "have proficiency` is the class's own pool")

    # A class WITHOUT the feature gets no pool — seven of the twelve.
    assert "weapon_mastery_from" not in derive(
        "en", klass("en", "Simple weapons"))
    print("  ok  a class without the level-1 feature carries no pool (7 of 12)")

    # A feature that states its NUMBER in the grammar the count reads and
    # then restricts in a way nobody calibrated. The count comes back; the
    # pool must not.
    refuses(lambda: derive("en", klass(
        "en", ALL_WEAPONS["en"],
        "Your training with weapons allows you to use the mastery properties "
        "of two kinds of Exotic weapons of your choice.")),
        "matches 0 of the 3",
        "a fourth restriction form refuses, instead of falling back on the "
        "widest of the three")

    # GUARD 2b — the Barbarian's "Melee" has to cost something.
    melee_only = dm.weapon_catalogue([
        _weapon("Mace", "mace", "simple", "melee", None),
        _weapon("Longsword", "longsword", "martial", "melee", None),
    ], "en", PROPERTY_INDEX["en"])
    refuses(lambda: derive("en", klass("en", ALL_WEAPONS["en"],
                                       MASTERY_PROSE["en"]["melee"]),
                           catalogue=melee_only),
            "restriction removed nothing",
            "GUARD 2b: a Melee restriction that selects every weapon refuses")

    # A pool reaching past what the class may even wield.
    refuses(lambda: derive("en", klass("en", "Simple weapons",
                                       MASTERY_PROSE["en"]["as-printed"])),
            "not proficient with",
            "a mastery pool holding weapons the class cannot use refuses, "
            "rather than being trimmed into shape here")

    # ⚠️ `maîtrise` is allowed in the FR *proficiency* form — the sentence is
    # about proficiency — but the feature is still anchored on `Bottes d’arme`.
    assert dm.WEAPON_MASTERY_FEATURE["fr"] == "Bottes d’arme"
    assert "maîtrise" not in dm._WEAPON_MASTERY_COUNT["fr"].pattern.lower()
    forms = dict((name, pattern)
                 for name, pattern, _r in dm._MASTERY_POOL_FORMS["fr"])
    assert "maîtrise" in forms["proficiency"].pattern
    assert "maîtrise" not in forms["melee"].pattern
    assert "maîtrise" not in forms["as-printed"].pattern
    print("  ok  `maîtrise` appears only in the French form that is ABOUT "
          "proficiency, and never as the feature's anchor")


def unit_guard():
    pool = ["srd:weapon:en:club", "srd:weapon:en:dagger"]
    twelve = [candidate("en", "c%02d" % n, pool) for n in range(12)]
    for n in range(5):
        twelve[n]["data"]["weapon_mastery_count"] = 2
        twelve[n]["data"]["weapon_mastery_from"] = pool
    dm.check_weapon_pools(twelve, "en")
    print("  ok  twelve classes with a pool, five of them with a mastery "
          "pool: accepted")

    blind = [dict(c, data=dict(c["data"])) for c in twelve]
    del blind[4]["data"]["weapon_mastery_from"]
    refuses(lambda: dm.check_weapon_pools(blind, "en"),
            "count but no pool",
            "GUARD 3: a class with a COUNT and no POOL refuses, naming it",
            error=dm.WeaponPoolError)

    invented = [dict(c, data=dict(c["data"])) for c in twelve]
    invented[7]["data"]["weapon_mastery_from"] = pool
    refuses(lambda: dm.check_weapon_pools(invented, "en"),
            "pool but no count",
            "GUARD 3: a class with a POOL and no COUNT refuses, naming it",
            error=dm.WeaponPoolError)

    empty = [dict(c, data=dict(c["data"])) for c in twelve]
    empty[9]["data"]["weapon_proficiency_ids"] = []
    refuses(lambda: dm.check_weapon_pools(empty, "en"),
            "carry no `weapon_proficiency_ids`",
            "GUARD 1, recounted: an empty pool refuses at the build level too",
            error=dm.WeaponPoolError)

    refuses(lambda: dm.check_weapon_pools(twelve[:11], "en"),
            "and the SRD has 12 classes",
            "eleven classes out of twelve refuses",
            error=dm.WeaponPoolError)

    six = [dict(c, data=dict(c["data"])) for c in twelve]
    six[5]["data"]["weapon_mastery_count"] = 2
    six[5]["data"]["weapon_mastery_from"] = pool
    refuses(lambda: dm.check_weapon_pools(six, "en"),
            "and the SRD gives the level-1",
            "six mastery pools where the SRD has five refuses",
            error=dm.WeaponPoolError)


# --------------------------------------------------------------------------
# acceptance — the real exports, recomputed from the other side
# --------------------------------------------------------------------------


def acceptance():
    for lang in ("en", "fr"):
        for name in ("class", "weapon", "weapon-property"):
            path = os.path.join(EXPORTS, lang, name + ".json")
            if not os.path.exists(path):
                print("SKIP acceptance — exports not built: %s" % path)
                return

    for lang in ("en", "fr"):
        weapons = {r["id"]: r["data"] for r in load(lang, "weapon")}
        classes = {r["slug"]: r["data"] for r in load(lang, "class")}
        assert len(weapons) == 38, (lang, len(weapons))

        # The pools, RECOMPUTED here from the weapon table alone, so that this
        # test does not simply agree with the file it is checking.
        simple = {i for i, d in weapons.items() if d["weapon_category"] == "simple"}
        martial = {i for i, d in weapons.items() if d["weapon_category"] == "martial"}
        melee = {i for i, d in weapons.items() if d["weapon_range"] == "melee"}

        def carrying(names):
            wanted = {canon.slugify(n) for n in names}
            out = set()
            for i, d in weapons.items():
                heads = {canon.slugify(h) for h in
                         dm.split_printed_properties(d["properties"] or "")}
                if heads & wanted:
                    out.add(i)
            return out

        light = carrying([LIGHT[lang]])
        finesse_or_light = carrying([FINESSE[lang], LIGHT[lang]])
        assert len(simple) == 14 and len(martial) == 24, (lang, len(simple))
        assert len(melee) == 28, (lang, len(melee))
        assert len(martial & finesse_or_light) == 5, (
            lang, sorted(martial & finesse_or_light))
        assert len(martial & light) == 3, (lang, sorted(martial & light))

        recomputed = {
            14: simple,
            17: simple | (martial & light),
            19: simple | (martial & finesse_or_light),
            38: simple | martial,
        }

        expected = EXPECTED[lang]
        assert set(classes) == set(expected), (lang, sorted(classes))
        with_pool = set()
        for slug, (prof_size, mastery_size) in sorted(expected.items()):
            data = classes[slug]
            prof = data["weapon_proficiency_ids"]
            assert len(prof) == prof_size, (lang, slug, len(prof), prof_size)
            assert set(prof) == recomputed[prof_size], (
                "%s/%s: the pool of %d is not the set the weapon table gives"
                % (lang, slug, prof_size))
            assert all(i in weapons for i in prof), (lang, slug)

            if mastery_size is None:
                assert "weapon_mastery_from" not in data, (lang, slug)
                continue
            with_pool.add(slug)
            pool = data["weapon_mastery_from"]
            assert len(pool) == mastery_size, (lang, slug, len(pool))
            assert set(pool) <= set(prof), (
                "%s/%s: a mastery it cannot wield" % (lang, slug))
            if mastery_size == 28:
                assert set(pool) == melee, (lang, slug)

        counted = {s for s, d in classes.items() if "weapon_mastery_count" in d}
        assert with_pool == counted, (lang, sorted(with_pool), sorted(counted))
        assert len(with_pool) == 5, (lang, sorted(with_pool))

        # ⚠️ The row that tells a derived pool from a recopied one.
        hc = "srd:weapon:%s:%s" % (lang, HAND_CROSSBOW[lang])
        assert weapons[hc]["weapon_category"] == "martial"
        assert weapons[hc]["weapon_range"] == "ranged"
        assert hc in classes[ROGUE[lang]]["weapon_mastery_from"], lang
        assert hc not in classes[BARBARIAN[lang]]["weapon_mastery_from"], lang

        print("  ok  %s: 12 pools (%s) and 5 mastery pools, every id a real "
              "weapon record; the Hand Crossbow is in the Rogue's and out of "
              "the Barbarian's"
              % (lang, ", ".join("%s=%d" % (s, v[0])
                                 for s, v in sorted(expected.items()))))


def load(lang, kind):
    with open(os.path.join(EXPORTS, lang, kind + ".json"), encoding="utf-8") as fh:
        return json.load(fh)["records"]


def main():
    unit_properties()
    unit_proficiency()
    unit_mastery()
    unit_guard()
    acceptance()
    print("PASS test_weapon_pools")


if __name__ == "__main__":
    main()
