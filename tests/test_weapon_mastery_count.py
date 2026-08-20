"""The level-1 weapon-mastery count, and the guard that recounts it.

THE DEFECT THIS FILE CLOSES, measured on the exports of 2026-08-20: the count
was present for **two** of the five classes that get the feature. Barbarian
and Fighter state it in their progression table, which the table parser
already read; Paladin, Ranger and Rogue state it **only in the prose of the
feature**, and nothing read that. So a builder could offer weapon masteries
to two classes and to nobody else, with every test green and every export
file present.

Two halves:

  1. unit — the derivation reads the prose grammar all five classes share,
     and `check_weapon_mastery_counts` refuses on the three ways this can go
     wrong (a class with the feature and no count, a count for fewer than
     five classes, and the two grammars disagreeing);
  2. acceptance — the same five classes, in both languages, read out of
     `exports/` and nothing else.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(ROOT, "exports", "srd")

sys.path.insert(0, os.path.join(ROOT, "src"))

import canon  # noqa: E402
import derive_mechanics as dm  # noqa: E402

# The SRD's five, in each language's own spelling, with the count each one
# prints. Stated here so the test can fail for the right reason instead of
# agreeing with whatever the export happens to say. Fighter's 3 is the
# arbitration of 2026-08-20 ("the SRD is right, fix FH").
EXPECTED = {
    "en": {"barbarian": 2, "fighter": 3, "paladin": 2, "ranger": 2, "rogue": 2},
    "fr": {"barbare": 2, "guerrier": 3, "paladin": 2, "rodeur": 2,
           "roublard": 2},
}

# Which of the five ALSO print the count in their progression table. The other
# three are the whole point of this file.
IN_THE_TABLE = {"en": {"barbarian", "fighter"}, "fr": {"barbare", "guerrier"}}

PROSE = {
    "en": {
        "barbarian": "Your training with weapons allows you to use the mastery "
                     "properties of two kinds of Simple or Martial Melee weapons "
                     "of your choice.",
        "fighter": "Your training with weapons allows you to use the mastery "
                   "properties of three kinds of Simple or Martial weapons of "
                   "your choice.",
        "rogue": "Your training with weapons allows you to use the mastery "
                 "properties of two kinds of weapons of your choice with which "
                 "you have proficiency.",
    },
    "fr": {
        "barbare": "Votre entraînement martial vous permet de recourir à la "
                   "botte de deux types d’arme de corps à corps courante ou de "
                   "guerre de votre choix.",
        "guerrier": "Votre entraînement martial vous permet de recourir à la "
                    "botte de trois types d’arme courante ou de guerre de "
                    "votre choix.",
        "roublard": "Votre entraînement martial vous permet de recourir à la "
                    "propriété Botte de deux types d’arme de votre choix parmi "
                    "celles dont vous avez la maîtrise.",
    },
}


def klass(name, lang, description=None, level=1):
    """One `class` candidate, shaped as build.py hands them to the guard."""
    features = []
    if description is not None:
        features.append({
            "name": dm.WEAPON_MASTERY_FEATURE[lang],
            "level": level,
            "description": description,
        })
    data = {"name": name, "features": features}
    count = dm._weapon_mastery_count(data, lang, "test:%s" % name)
    if count is not None:
        data["weapon_mastery_count"] = count
    return {"name": name, "slug": canon.slugify(name), "data": data}


def progression(name, lang, level_one_value):
    label = dm.WEAPON_MASTERY_FEATURE[lang]
    key = canon.slugify(label).replace("-", "_")
    return {
        "name": name,
        "resource_columns": [{"key": key, "label": label}],
        "levels": [{"level": 1, "resources": {key: level_one_value}}],
    }


def refuses(fn, needle, why):
    try:
        fn()
    except dm.WeaponMasteryCountError as exc:
        assert needle in str(exc), "wrong refusal (%r not in): %s" % (needle, exc)
        print("  ok  %s" % why)
        return
    raise AssertionError("no refusal: %s" % why)


def unit():
    # -- the prose grammar, both languages ---------------------------------
    for lang, cases in PROSE.items():
        for name, text in cases.items():
            got = klass(name, lang, text)["data"]["weapon_mastery_count"]
            want = EXPECTED[lang][canon.slugify(name)]
            assert got == want, (lang, name, got, want)
    print("  ok  the prose grammar reads the count for both languages, "
          "including the three classes with no table column")

    # -- a class with no such feature gets no field, and that is correct ----
    plain = klass("Wizard", "en", description=None)
    assert "weapon_mastery_count" not in plain["data"]
    print("  ok  a class without the feature carries no count (7 of 12)")

    # -- a feature whose prose states no number STOPS, it does not default --
    try:
        klass("Broken", "en", "Your training with weapons is impressive.")
    except dm.DerivationError as exc:
        assert "does not state how many" in str(exc), exc
        print("  ok  a feature with no number refuses instead of meaning zero")
    else:
        raise AssertionError("a numberless feature must not become a count")

    # -- a number word outside the closed set STOPS ------------------------
    try:
        klass("Broken", "en",
              "…use the mastery properties of eleventeen kinds of weapons.")
    except dm.DerivationError as exc:
        assert "eleventeen" in str(exc), exc
        print("  ok  a number word outside the SRD's own set refuses, naming it")
    else:
        raise AssertionError("an unknown number word must not be guessed")

    # -- THE REAL DEFECT: only two of five ---------------------------------
    two_only = [klass("Barbarian", "en", PROSE["en"]["barbarian"]),
                klass("Fighter", "en", PROSE["en"]["fighter"])]
    refuses(
        lambda: dm.check_weapon_mastery_counts(two_only, [], "en"),
        "short by three classes",
        "a build that found the count for 2 of the 5 classes REFUSES "
        "(the 2026-08-20 defect)")

    # -- a class carrying the feature but no derived count ------------------
    silent = list(two_only)
    mute = klass("Rogue", "en", PROSE["en"]["rogue"])
    del mute["data"]["weapon_mastery_count"]
    silent.append(mute)
    refuses(
        lambda: dm.check_weapon_mastery_counts(silent, [], "en"),
        "feature but no count",
        "a class with the feature and no count REFUSES, naming the class")

    # -- the five, agreeing with the table: passes -------------------------
    five = [klass(n.capitalize(), "en", PROSE["en"].get(n, PROSE["en"]["rogue"]))
            for n in ("barbarian", "fighter", "paladin", "ranger", "rogue")]
    five[0] = klass("Barbarian", "en", PROSE["en"]["barbarian"])
    five[1] = klass("Fighter", "en", PROSE["en"]["fighter"])
    tables = [progression("Barbarian", "en", 2), progression("Fighter", "en", 3)]
    dm.check_weapon_mastery_counts(five, tables, "en")
    print("  ok  five classes, two witnesses agreeing: accepted")

    # -- THE TWO GRAMMARS DISAGREEING --------------------------------------
    refuses(
        lambda: dm.check_weapon_mastery_counts(
            five, [progression("Fighter", "en", 2)], "en"),
        "Two readings of the same rule disagree",
        "the table saying 2 where the prose says 3 REFUSES rather than choose")

    # -- a table column for a class that derived nothing --------------------
    refuses(
        lambda: dm.check_weapon_mastery_counts(
            five, [progression("Bard", "en", 2)], "en"),
        "no class record of this build derived a count",
        "a progression column with no matching class record REFUSES")

    # -- ⚠️ the French feature is `Bottes d’arme`, never `Maîtrise…` -------
    assert dm.WEAPON_MASTERY_FEATURE["fr"] == "Bottes d’arme"
    assert "maîtrise" not in dm._WEAPON_MASTERY_COUNT["fr"].pattern.lower()
    print("  ok  the French anchor is `botte`, and `maîtrise` appears nowhere "
          "in its pattern")


def acceptance():
    missing = [
        os.path.join(EXPORTS, lang, name + ".json")
        for lang in ("en", "fr") for name in ("class", "class-progression")
    ]
    missing = [p for p in missing if not os.path.exists(p)]
    if missing:
        print("SKIP acceptance — exports not built: %s" % missing[0])
        return

    for lang, expected in sorted(EXPECTED.items()):
        with open(os.path.join(EXPORTS, lang, "class.json"), encoding="utf-8") as fh:
            classes = json.load(fh)["records"]
        got = {r["slug"]: r["data"]["weapon_mastery_count"]
               for r in classes if "weapon_mastery_count" in r["data"]}
        assert got == expected, (lang, got, expected)

        with open(os.path.join(EXPORTS, lang, "class-progression.json"),
                  encoding="utf-8") as fh:
            progressions = json.load(fh)["records"]

        label = dm.WEAPON_MASTERY_FEATURE[lang]
        witnessed = {}
        for rec in progressions:
            for col in rec["data"]["resource_columns"]:
                if col["label"] == label:
                    slug = rec["data"]["class"].rsplit(":", 1)[-1]
                    witnessed[slug] = rec["data"]["levels"][0]["resources"][col["key"]]
        assert set(witnessed) == IN_THE_TABLE[lang], (lang, sorted(witnessed))
        for slug, printed in witnessed.items():
            assert printed == expected[slug], (lang, slug, printed, expected[slug])

        print("  ok  %s: 5 classes carry the count (%s); %d of them are also "
              "witnessed by their progression table, and agree"
              % (lang,
                 ", ".join("%s=%d" % kv for kv in sorted(expected.items())),
                 len(witnessed)))


def main():
    unit()
    acceptance()
    print("PASS test_weapon_mastery_count")


if __name__ == "__main__":
    main()
