"""Calibration checks for the English background parser.

Each scenario reproduces a shape found calibrating parse_backgrounds_en.py
against the pinned EN PDF, plus negative controls.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_backgrounds_en  # noqa: E402


def page(*blocks):
    return extract.normalise("\n".join(blocks))


def wrap(*bg_blocks, suspect=()):
    pages = [page("Character Origins\n\nCharacter Backgrounds\n\nBackground Descriptions\n")] \
        + list(bg_blocks) \
        + [page("Character Species\n\nDragonborn\n")]
    return parse_backgrounds_en.parse(pages, suspect)


def main():
    # -- an ordinary, complete background -----------------------------------
    bgs, anomalies, conflicts = wrap(page(
        "Acolyte\n"
        "Ability Scores: Intelligence, Wisdom, Charisma\n"
        "Feat: Magic Initiate (Cleric) (see “Feats”)\n"
        "Skill Proficiencies: Insight and Religion\n"
        "Tool Proficiency: Calligrapher’s Supplies\n"
        "Equipment: Choose A or B: (A) Calligrapher’s Supplies, Book\n"
        "(prayers), Holy Symbol, Parchment (10 sheets), Robe, 8 GP;\n"
        "or (B) 50 GP\n",
    ))
    assert len(bgs) == 1 and not anomalies and not conflicts, (bgs, anomalies)
    b = bgs[0]
    assert b["ability_scores"] == ["Intelligence", "Wisdom", "Charisma"]
    assert b["skill_proficiencies"] == ["Insight", "Religion"]
    assert b["feat"] == "Magic Initiate (Cleric) (see “Feats”)"
    assert b["equipment"].startswith("Choose A or B: (A) Calligrapher")
    assert b["equipment"].endswith("or (B) 50 GP")
    print("  ok  an ordinary background parses cleanly, with fixed-count fields as lists")

    # -- THE TRAP: a background's field block ends exactly on a page's last -
    # line, with the next background's name starting the next page. No blank
    # line exists at that seam (each page is normalised independently) --
    # the same shape already found and fixed for spells (Charm Monster, 11 FR
    # durations) and now guarded here defensively even though the pinned
    # PDF's four backgrounds happen to fit without tripping it.
    pages = (
        [page("Character Origins\n\nCharacter Backgrounds\n\nBackground Descriptions\n")]
        + [page(
            "Criminal\n"
            "Ability Scores: Dexterity, Constitution, Intelligence\n"
            "Feat: Alert (see “Feats”)\n"
            "Skill Proficiencies: Sleight of Hand and Stealth\n"
            "Tool Proficiency: Thieves’ Tools\n"
            "Equipment: Choose A or B: (A) 2 Daggers, Thieves’ Tools,\n"
            "Crowbar, 2 Pouches, Traveler’s Clothes, 16 GP; or (B) 50 GP",  # no blank line: page ends here
        )]
        + [page("Sage\nAbility Scores: Constitution, Intelligence, Wisdom\n"
                "Feat: Magic Initiate (Wizard) (see “Feats”)\n"
                "Skill Proficiencies: Arcana and History\n"
                "Tool Proficiency: Calligrapher’s Supplies\n"
                "Equipment: Choose A or B: (A) Quarterstaff, 8 GP; or (B) 50 GP\n")]
        + [page("Character Species\n\nDragonborn\n")]
    )
    bgs, anomalies, conflicts = parse_backgrounds_en.parse(pages)
    assert len(bgs) == 2 and not anomalies, (
        "a page seam right after the last field must not bleed into the next "
        "background: %s / %s" % (bgs, anomalies)
    )
    criminal = [b for b in bgs if b["name"] == "Criminal"][0]
    assert criminal["equipment"].endswith("16 GP; or (B) 50 GP"), criminal["equipment"]
    assert "Sage" not in criminal["equipment"]
    print("  ok  a page break right after the last field does not swallow the next background")

    # -- NEGATIVE CONTROL: a background whose ability scores don't have three
    # is a genuine anomaly, not something to guess through.
    bgs, anomalies, conflicts = wrap(page(
        "Soldier\n"
        "Ability Scores: Strength, Dexterity\n"
        "Feat: Savage Attacker (see “Feats”)\n"
        "Skill Proficiencies: Athletics and Intimidation\n"
        "Tool Proficiency: Choose one kind of Gaming Set\n"
        "Equipment: Choose A or B: (A) Spear, 14 GP; or (B) 50 GP\n",
    ))
    assert len(bgs) == 0 and len(anomalies) == 1, (bgs, anomalies)
    assert "ability score" in anomalies[0]["detail"]
    print("  ok  negative control: a malformed ability-score count is reported, not guessed")

    print("PASS test_parse_backgrounds_en")


if __name__ == "__main__":
    main()
