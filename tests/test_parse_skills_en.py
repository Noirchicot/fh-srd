"""Calibration checks for the English Skills table parser."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_skills_en as skills  # noqa: E402

# The eighteen rows have to be present for the parser's own count check to
# pass; only the ones a test is actually about are written out in full.
FILLER = [
    ("Animal Handling", "Wisdom"), ("Arcana", "Intelligence"),
    ("Athletics", "Strength"), ("Deception", "Charisma"),
    ("History", "Intelligence"), ("Insight", "Wisdom"),
    ("Intimidation", "Charisma"), ("Investigation", "Intelligence"),
    ("Medicine", "Wisdom"), ("Nature", "Intelligence"),
    ("Perception", "Wisdom"), ("Performance", "Charisma"),
    ("Persuasion", "Charisma"), ("Religion", "Intelligence"),
    ("Sleight of Hand", "Dexterity"), ("Stealth", "Dexterity"),
    ("Survival", "Wisdom"),
]


def page(*blocks):
    return extract.normalise("\n".join(blocks))


def wrap(rows, filler_from=0, trailer=""):
    """One page: some rows, the header, the rest of the eighteen, a trailer."""
    body = "\n\n".join(rows)
    rest = "\n\n".join(
        "%s\n%s\nExample text for %s." % (name, ability, name)
        for name, ability in FILLER[filler_from:]
    )
    return skills.parse([page(body + "\n\nSkills\n\nSkill\nAbility\nExample Uses\n\n"
                             + rest + trailer)])


def main():
    # -- an ordinary row ----------------------------------------------------
    found, anomalies, conflicts = wrap(
        ["Acrobatics\nDexterity\nStay on your feet in a tricky situation, or "
         "perform an acrobatic stunt."]
    )
    assert not anomalies and not conflicts, (anomalies, conflicts)
    assert len(found) == 18, len(found)
    acro = found[0]
    assert acro["name"] == "Acrobatics" and acro["ability"] == "Dexterity"
    assert acro["ability_key"] == "dex"
    assert acro["example_uses"].endswith("acrobatic stunt.")
    print("  ok  an ordinary Name / Ability / Example Uses row parses cleanly")

    # -- THE FIELD BOUNDARY: Example Uses wraps with no delimiter; only the -
    # ability line of the NEXT row says where the previous one stopped.
    found, anomalies, _ = wrap(
        ["Acrobatics\nDexterity\nStay on your feet in a tricky situation,\n"
         "or perform an acrobatic stunt."]
    )
    assert not anomalies, anomalies
    assert found[0]["example_uses"] == (
        "Stay on your feet in a tricky situation, or perform an acrobatic stunt."
    ), found[0]["example_uses"]
    print("  ok  a wrapped Example Uses cell is joined, not truncated")

    # -- the header sits BETWEEN two runs of rows, not above them, and must -
    # not be read as a row of its own ("Skill" is not a skill).
    found, anomalies, _ = wrap(
        ["Acrobatics\nDexterity\nStay on your feet."]
    )
    assert not anomalies, anomalies
    assert "Skill" not in [s["name"] for s in found]
    assert [s["name"] for s in found][:2] == ["Acrobatics", "Animal Handling"]
    print("  ok  the displaced header block does not become a nineteenth skill")

    # -- ability keys are the stat blocks' own abbreviations ----------------
    found, _, _ = wrap(["Acrobatics\nDexterity\nStay on your feet."])
    keys = {s["name"]: s["ability_key"] for s in found}
    assert keys["Athletics"] == "str" and keys["Arcana"] == "int"
    assert keys["Survival"] == "wis" and keys["Deception"] == "cha"
    print("  ok  ability_key matches the abbreviations used in monster stat blocks")

    # -- NEGATIVE CONTROL 1: a missing row must be reported, not shipped ----
    found, anomalies, _ = wrap(
        ["Acrobatics\nDexterity\nStay on your feet."], filler_from=1)
    assert anomalies and "17 rows, expected 18" in anomalies[0]["detail"], anomalies
    print("  ok  negative control: a table short of eighteen rows fails loudly")

    # -- NEGATIVE CONTROL 2: an ability with no Example Uses line is an -----
    # anomaly, not a skill with an empty description
    found, anomalies, _ = wrap(["Acrobatics\nDexterity"])
    assert any("no Example Uses" in a["detail"] for a in anomalies), anomalies
    assert "Acrobatics" not in [s["name"] for s in found]
    print("  ok  negative control: a row with no Example Uses cell is excluded, loudly")

    # -- NEGATIVE CONTROL 3: no header at all -------------------------------
    found, anomalies, _ = skills.parse([page("Acrobatics\nDexterity\nStay on your feet.")])
    assert not found and anomalies and "header not found" in anomalies[0]["detail"]
    print("  ok  negative control: no header means no records and a stated reason")

    print("PASS test_parse_skills_en")


if __name__ == "__main__":
    main()
