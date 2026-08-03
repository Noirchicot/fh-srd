"""Calibration checks for the English class parser.

Each scenario reproduces a shape found calibrating parse_classes_en.py
against the pinned EN PDF, plus negative controls. This is the heaviest
grammar of the three parsers in this round -- a "Core X Traits" table with
no colon separator and per-field wrapping, named "Level N: Feature" headings
nested two deep (class, then subclass), and an "... Options" section
(Sorcerer, Warlock) that must bound the core-features region without being
parsed itself.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_classes_en  # noqa: E402


def page(*blocks):
    return extract.normalise("\n".join(blocks))


def wrap(*class_blocks, suspect=()):
    pages = [page("Classes\n")] + list(class_blocks) + [page("Character Origins\n")]
    classes, anomalies, conflicts = parse_classes_en.parse(pages, suspect)
    # These fixtures deliberately include only one or two of the twelve real
    # SRD classes -- the parser correctly notices the other ten/eleven have
    # no "Core X Traits" anchor anywhere in the chapter and reports it (a
    # REAL safety check: if a future SRD reissue silently dropped a class,
    # this is what would catch it). That is expected noise from a partial
    # fixture, not a finding any scenario below is testing for, so it is
    # filtered out here rather than asserted on in every single scenario.
    real = [a for a in anomalies if "anchor in the Classes chapter" not in a["detail"]]
    return classes, real, conflicts


BARBARIAN = (
    "Barbarian\n"
    "\n"
    "Core Barbarian Traits\n"
    "\n"
    "Primary Ability\n"
    "Strength\n"
    "\n"
    "Hit Point Die\n"
    "D12 per Barbarian level\n"
    "\n"
    "Saving Throw\n"
    "Proficiencies\n"
    "Strength and Constitution\n"
    "\n"
    "Skill Proficiencies\n"
    "Choose 2: Athletics, Intimidation, or Survival\n"
    "\n"
    "Weapon Proficiencies Simple and Martial weapons\n"
    "\n"
    "Armor Training\n"
    "Light and Medium armor and Shields\n"
    "\n"
    "Starting Equipment\n"
    "Choose A or B: (A) Greataxe, and 15 GP; or (B) 75 GP\n"
    "\n"
    "Becoming a Barbarian …\n"
    "\n"
    "Level 1: Rage\n"
    "You can imbue yourself with a primal power called Rage.\n"
    "\n"
    "Level 3: Barbarian Subclass\n"
    "You gain a Barbarian subclass of your choice.\n"
    "\n"
    "Barbarian Subclass:\n"
    "Path of the Berserker\n"
    "\n"
    "Channel Rage into Violent Fury\n"
    "\n"
    "Barbarians who walk the Path of the Berserker are fierce fighters.\n"
    "\n"
    "Level 3: Frenzy\n"
    "You deal extra damage to the first target you hit on your turn.\n"
)

# A caster with Tool Proficiencies present (the optional field), a Spell
# List AND a named "... Options" section both sitting between the core
# features and the subclass heading, and a subclass name that WRAPS onto a
# second line -- the shape that broke a naive single-line regex calibrating
# Monk's "Warrior of the\nOpen Hand" and Sorcerer's "Draconic\nSorcery".
SORCERER = (
    "Sorcerer\n"
    "\n"
    "Core Sorcerer Traits\n"
    "\n"
    "Primary Ability\n"
    "Charisma\n"
    "\n"
    "Hit Point Die\n"
    "D6 per Sorcerer level\n"
    "\n"
    "Saving Throw\n"
    "Proficiencies\n"
    "Constitution and Charisma\n"
    "\n"
    "Skill Proficiencies\n"
    "Choose 2: Arcana, Deception, or Religion\n"
    "\n"
    "Weapon Proficiencies Simple weapons\n"
    "\n"
    "Tool Proficiencies\n"
    "Choose 3 Musical Instruments\n"
    "\n"
    "Armor Training\n"
    "None\n"
    "\n"
    "Starting Equipment\n"
    "Choose A or B: (A) Spear, and 28 GP; or (B) 50 GP\n"
    "\n"
    "Becoming a Sorcerer …\n"
    "\n"
    "Level 1: Innate Sorcery\n"
    "Your innate magic is fueled by your Sorcerous origin.\n"
    "\n"
    "Level 2: Metamagic\n"
    "You gain two Metamagic options of your choice.\n"
    "\n"
    "Metamagic Options\n"
    "\n"
    "Careful Spell\n"
    "Cost: 1 Sorcery Point\n"
    "\n"
    "When you cast a spell that forces other creatures to make a saving throw.\n"
    "\n"
    "Sorcerer Spell List\n"
    "\n"
    "Cantrips (Level 0 Sorcerer Spells)\n"
    "\n"
    "Spell\n"
    "School\n"
    "Special\n"
    "\n"
    "Sorcerer Subclass: Draconic\n"
    "Sorcery\n"
    "\n"
    "Breathe the Magic of Dragons\n"
    "\n"
    "Your innate magic comes from the gift of a dragon.\n"
    "\n"
    "Level 3: Draconic Resilience\n"
    "Your Hit Point maximum increases.\n"
)


def main():
    # -- a minimal but complete class, ending the document (no next class' --
    # anchor to bound it -- the chapter-end anchor must do that job) -------
    classes, anomalies, conflicts = wrap(page(BARBARIAN))
    assert len(classes) == 1 and not anomalies and not conflicts, (classes, anomalies)
    barb = classes[0]
    assert barb["primary_ability"] == "Strength"
    assert barb["saving_throw_proficiencies"] == ["Strength", "Constitution"]
    assert barb["weapon_proficiencies"] == "Simple and Martial weapons"
    assert barb["tool_proficiencies"] is None
    assert [f["name"] for f in barb["features"]] == ["Rage", "Barbarian Subclass"]
    assert barb["subclass"]["name"] == "Path of the Berserker"
    assert barb["subclass"]["description"].startswith("Channel Rage into Violent Fury")
    assert [f["name"] for f in barb["subclass"]["features"]] == ["Frenzy"]
    print("  ok  a minimal complete class parses cleanly, traits table and both feature levels")

    # -- the wrapped inline-vs-stacked label mix in one table: "Weapon ------
    # Proficiencies X" (value on the label's own line) next to "Primary
    # Ability" / "Strength" (value on the line below) and "Saving Throw" /
    # "Proficiencies" (the label ITSELF spans two lines) -- all three shapes
    # in the same table, exactly as the real PDF prints them.
    assert barb["hit_point_die"] == "D12 per Barbarian level"
    assert barb["armor_training"] == "Light and Medium armor and Shields"
    print("  ok  inline-value, stacked-value and two-line-label fields all resolve correctly")

    # -- Tool Proficiencies (optional), an "... Options" section AND a Spell -
    # List both sitting between core features and the subclass heading, and
    # a subclass name that wraps onto a second line ("Draconic" / "Sorcery")
    classes, anomalies, conflicts = wrap(page(SORCERER))
    assert len(classes) == 1 and not anomalies and not conflicts, (classes, anomalies)
    sorc = classes[0]
    assert sorc["tool_proficiencies"] == "Choose 3 Musical Instruments"
    assert [f["name"] for f in sorc["features"]] == ["Innate Sorcery", "Metamagic"], (
        "the Metamagic Options catalogue and the Spell List table must not "
        "leak into the core feature list: %s" % [f["name"] for f in sorc["features"]]
    )
    assert "Careful Spell" not in [f["name"] for f in sorc["features"]]
    assert sorc["subclass"]["name"] == "Draconic Sorcery", sorc["subclass"]["name"]
    assert [f["name"] for f in sorc["subclass"]["features"]] == ["Draconic Resilience"]
    print("  ok  Tool Proficiencies, an Options section, a Spell List and a wrapped "
          "subclass name are all handled without leaking into the feature list")

    # -- two classes back to back: the first class's span must stop at the --
    # second's own "Core X Traits" anchor, not run into it.
    classes, anomalies, conflicts = wrap(page(BARBARIAN), page(SORCERER))
    assert len(classes) == 2 and not anomalies, (len(classes), anomalies)
    names = sorted(c["name"] for c in classes)
    assert names == ["Barbarian", "Sorcerer"]
    print("  ok  two classes in sequence are correctly bounded against each other")

    # -- NEGATIVE CONTROL: a class with no subclass heading at all is -------
    # reported and excluded, not returned half-filled without one.
    broken = BARBARIAN.split("Barbarian Subclass:\n")[0]  # cut before the subclass
    classes, anomalies, conflicts = wrap(page(broken))
    assert len(classes) == 0 and len(anomalies) == 1, (classes, anomalies)
    assert "Subclass:" in anomalies[0]["detail"]
    print("  ok  negative control: a class missing its subclass heading is reported, not half-filled")

    # -- NEGATIVE CONTROL: a required core-traits label out of order/missing
    broken2 = BARBARIAN.replace("Armor Training\nLight and Medium armor and Shields\n\n", "")
    classes, anomalies, conflicts = wrap(page(broken2))
    assert len(classes) == 0 and len(anomalies) == 1, (classes, anomalies)
    assert "Armor Training" in anomalies[0]["detail"]
    print("  ok  negative control: a missing required core-traits label is reported, not skipped")

    print("PASS test_parse_classes_en")


if __name__ == "__main__":
    main()
