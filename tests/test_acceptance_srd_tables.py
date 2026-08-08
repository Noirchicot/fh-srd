"""The acceptance test for the two tables this lot exists to add.

> A **level 3 Wizard** can be given its spell slots, and a **level 1 Rogue**
> can choose its skills — **from the exports alone**, with no value hard-coded
> anywhere else.

So this file reads `exports/` and nothing else. It imports no parser, opens no
PDF and knows no rule: every number it asserts on is fetched from a record, and
the two "expected" values it does state outright (four level-1 slots and two
level-2 slots for a level 3 Wizard; four skill choices for a Rogue) are there
so the test can fail for the right reason rather than agreeing with whatever
the file happens to say. Both languages, because a builder Eric's table can
actually use has to work in French.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(ROOT, "exports", "srd")

sys.path.insert(0, os.path.join(ROOT, "src"))
import canon  # noqa: E402

# The class whose skill menu is a prose reference rather than a list ("Choose
# any 3 skills"), in both languages. Named, not skipped by a wildcard.
OPEN_MENU = {"Bard", "Barde"}

# How each language writes "choose N from this list", and how it separates the
# last option. Read off the twelve class records, not invented.
MENU_PREFIX = {
    "en": re.compile(r"^Choose \d+:\s*"),
    "fr": re.compile(r"^\d+ au choix parmi :\s*"),
}
# English puts a comma before its final "or" ("Perception, or Survival");
# French puts none before its "et" ("Persuasion et Tromperie"). Splitting on
# commas alone leaves the last two French options fused into one unresolvable
# name -- which is exactly how a builder would silently lose a skill choice.
MENU_SPLIT = {
    "en": re.compile(r",\s*or\s+|,\s*|\s+or\s+"),
    "fr": re.compile(r",\s*et\s+|,\s*|\s+et\s+"),
}


def load(lang, kind):
    with open(os.path.join(EXPORTS, lang, kind + ".json"), encoding="utf-8") as fh:
        payload = json.load(fh)
    return {r["name"]: r for r in payload["records"]}


def menu_options(text, lang):
    body = MENU_PREFIX[lang].sub("", text)
    return [part.strip() for part in MENU_SPLIT[lang].split(body) if part.strip()]


def main():
    for lang, wizard_name, rogue_name in (("en", "Wizard", "Rogue"),
                                          ("fr", "Magicien", "Roublard")):
        classes = load(lang, "class")
        progressions = load(lang, "class-progression")
        skills = load(lang, "skill")

        # ---- A LEVEL 3 WIZARD GETS ITS SPELL SLOTS ------------------------
        wizard = progressions[wizard_name]
        assert wizard["data"]["class"] == classes[wizard_name]["id"], wizard["data"]
        level3 = [l for l in wizard["data"]["levels"] if l["level"] == 3]
        assert len(level3) == 1, "a progression must have exactly one level 3 row"
        level3 = level3[0]

        slots = level3["spell_slots"]
        assert len(slots) == wizard["data"]["spell_slot_levels"] == 9, slots
        assert slots[0] == 4 and slots[1] == 2, slots
        assert all(s == 0 for s in slots[2:]), slots
        assert level3["proficiency_bonus"] == 2, level3
        total = sum(slots)
        assert total == 6, total

        # the resource columns are self-describing: a builder reads the label
        # from the record, it does not carry a per-class table of its own
        keys = [c["key"] for c in wizard["data"]["resource_columns"]]
        assert set(keys) == set(level3["resources"]), (keys, level3["resources"])
        assert all(c["label"] for c in wizard["data"]["resource_columns"])
        print("  ok  [%s] a level 3 %s draws 4 level-1 and 2 level-2 slots from "
              "the export" % (lang, wizard_name))

        # ---- A LEVEL 1 ROGUE CHOOSES ITS SKILLS ---------------------------
        rogue = classes[rogue_name]
        menu = rogue["data"]["skill_proficiencies"]
        options = menu_options(menu, lang)
        assert len(options) == 10, (menu, options)
        assert menu.startswith("4" if lang == "fr" else "Choose 4"), menu

        chosen = []
        for option in options:
            record_id = canon.record_id("srd", "skill", lang, canon.slugify(option))
            match = [s for s in skills.values() if s["id"] == record_id]
            assert match, (
                "%s: the %s's skill menu offers %r, which resolves to no skill "
                "record (%s)" % (lang, rogue_name, option, record_id))
            chosen.append(match[0])

        for skill in chosen:
            assert skill["data"]["ability"], skill["id"]
            assert skill["data"]["ability_key"] in (
                {"str", "dex", "con", "int", "wis", "cha"} if lang == "en"
                else {"for", "dex", "con", "int", "sag", "cha"}), skill["data"]
            assert skill["data"]["example_uses"].endswith("."), skill["id"]
        print("  ok  [%s] all ten skills the %s may choose from resolve to skill "
              "records with an ability" % (lang, rogue_name))

        # ---- and the same holds for every class with a listed menu --------
        resolved = 0
        for name, record in sorted(classes.items()):
            if name in OPEN_MENU:
                continue
            for option in menu_options(record["data"]["skill_proficiencies"], lang):
                record_id = canon.record_id(
                    "srd", "skill", lang, canon.slugify(option))
                assert any(s["id"] == record_id for s in skills.values()), (
                    "%s: %s's menu offers %r, unresolvable" % (lang, name, option))
                resolved += 1
        assert resolved > 70, resolved
        print("  ok  [%s] %d skill choices across eleven classes all resolve"
              % (lang, resolved))

        # ---- every class has a progression, and it covers levels 1..20 ----
        assert set(progressions) == set(classes), (
            set(classes) ^ set(progressions))
        for name, record in sorted(progressions.items()):
            levels = [l["level"] for l in record["data"]["levels"]]
            assert levels == list(range(1, 21)), (name, levels)
            for entry in record["data"]["levels"]:
                assert entry["proficiency_bonus"] == 2 + (entry["level"] - 1) // 4
        print("  ok  [%s] all twelve classes carry a full 1..20 progression"
              % lang)

        # ---- eighteen skills, each with an ability ------------------------
        assert len(skills) == 18, len(skills)
        abilities = {s["data"]["ability_key"] for s in skills.values()}
        assert len(abilities) == 5, abilities  # no SRD skill uses Constitution
        print("  ok  [%s] the eighteen SRD skills are present, across five "
              "abilities" % lang)

    # -- NEGATIVE CONTROL ---------------------------------------------------
    # The checks above must be capable of failing: an unresolvable option and
    # a wrong slot count both have to be caught, or "green" means nothing.
    skills = load("en", "skill")
    assert not any(
        s["id"] == canon.record_id("srd", "skill", "en", canon.slugify("Piloting"))
        for s in skills.values()), "a skill the SRD does not have must not resolve"
    wizard = load("en", "class-progression")["Wizard"]["data"]
    level3 = [l for l in wizard["levels"] if l["level"] == 3][0]
    assert level3["spell_slots"] != [4, 3, 0, 0, 0, 0, 0, 0, 0], (
        "the level 4 row's slots must not be what level 3 returns")
    print("  ok  negative control: an unknown skill does not resolve, and level "
          "3 is not level 4")

    print("PASS test_acceptance_srd_tables")


if __name__ == "__main__":
    main()
