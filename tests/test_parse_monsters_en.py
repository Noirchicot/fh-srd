"""Calibration checks for the English Monsters (stat block) parser.

Each scenario reproduces a shape found calibrating parse_monsters_en.py
against the pinned EN PDF, plus a negative control.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_monsters_en as monsters  # noqa: E402


def page(*blocks):
    return extract.normalise("\n".join(blocks))


def wrap(*raw_pages, suspect=()):
    pages = (
        [page("Monsters A–Z\n\n" + raw_pages[0])]
        + [page(p) for p in raw_pages[1:]]
    )
    return monsters.parse(pages, suspect)


def main():
    # -- an ordinary, minimal, complete stat block ---------------------------
    found, anomalies, conflicts = wrap(
        "Basilisk\n"
        "Basilisk\n\n"
        "Medium Monstrosity, Unaligned\n\n"
        "AC 15\n\n"
        "Initiative −1 (9)\n"
        "HP 52 (8d8 + 16)\n"
        "Speed 20 ft.\n\n"
        "MOD SAVE\nMOD SAVE\nMOD SAVE\n"
        "Str 16 +3\n+3\nDex 8\n−1\n−1\nCon 15 +2\n+2\nInt 2\n−4 −4\nWis 8\n−1\n−1\nCha 7\n−2\n−2\n\n"
        "Senses Darkvision 60 ft.; Passive Perception 9\n"
        "Languages None\n"
        "CR 3 (XP 700; PB +2)\n\n"
        "Actions\n\n"
        "Bite. Melee Attack Roll: +5, reach 5 ft. Hit: 10 (2d6 + 3)\n"
        "Piercing damage plus 7 (2d6) Poison damage.\n"
    )
    assert len(found) == 1 and not anomalies and not conflicts, (found, anomalies)
    b = found[0]
    assert b["name"] == "Basilisk" and b["size_type"] == "Medium Monstrosity"
    assert b["alignment"] == "Unaligned" and b["tags"] is None
    assert b["abilities"]["dex"] == {"score": 8, "mod": -1, "save": -1}
    assert b["traits"] == [] and len(b["actions"]) == 1
    print("  ok  an ordinary, minimal, complete stat block parses cleanly")

    # -- THE ABILITY-TABLE TRAP: no per-line rule describes this region -----
    # (see module docstring) -- a negative modifier can land on its own
    # physical line while a zero modifier AND save both stay inline, in the
    # SAME stat block. Reproduces Animated Armor's Wis/Int rows exactly.
    found, anomalies, conflicts = wrap(
        "Animated Armor\n"
        "Medium Construct, Unaligned\n\n"
        "AC 18\n\n"
        "Initiative +2 (12)\n"
        "HP 33 (6d8 + 6)\n"
        "Speed 25 ft.\n\n"
        "MOD SAVE\nMOD SAVE\nMOD SAVE\n"
        "Str 14 +2\n+2\nDex 11 +0 +0\nCon 13 +1\n+1\nInt 1\n−5\n−5\nWis 3\n−4 −4\nCha 1\n−5\n−5\n\n"
        "Senses Blindsight 60 ft.; Passive Perception 6\n"
        "Languages None\n"
        "CR 1 (XP 200; PB +2)\n\n"
        "Actions\n\n"
        "Slam. Melee Attack Roll: +4, reach 5 ft. Hit: 5 (1d6 + 2)\n"
        "Bludgeoning damage.\n"
    )
    assert len(found) == 1 and not anomalies, (found, anomalies)
    ab = found[0]["abilities"]
    assert ab["dex"] == {"score": 11, "mod": 0, "save": 0}
    assert ab["int"] == {"score": 1, "mod": -5, "save": -5}
    assert ab["wis"] == {"score": 3, "mod": -4, "save": -4}
    print("  ok  the ability table's inconsistent line-per-row shape is handled by token, not line")

    # -- THE MISSING-BLANK TRAP: some stat blocks run Speed straight into ---
    # the ability table's "MOD SAVE" header with no blank line at all
    # (reproduces Bandit Captain and Frost Giant exactly).
    found, anomalies, conflicts = wrap(
        "Bandit Captain\n"
        "Medium or Small Humanoid, Neutral\n\n"
        "AC 15\n\n"
        "Initiative +3 (13)\n"
        "HP 52 (8d8 + 16)\n"
        "Speed 30 ft.\n"
        "MOD SAVE\nMOD SAVE\nMOD SAVE\n"
        "Str 15 +2\n+4\nDex 16 +3\n+5\nCon 14 +2\n+2\nInt 14 +2\n+2\nWis 11 +0 +2\nCha 14 +2\n+2\n\n"
        "Senses Passive Perception 10\n"
        "Languages Common\n"
        "CR 2 (XP 450; PB +2)\n\n"
        "Actions\n\n"
        "Scimitar. Melee Attack Roll: +5, reach 5 ft. Hit: 6 (1d6 + 3)\n"
        "Slashing damage.\n"
    )
    assert len(found) == 1 and not anomalies, (
        "a stat block with no blank line before the ability table's header "
        "must still parse: %s / %s" % (found, anomalies)
    )
    assert found[0]["size_type"] == "Medium or Small Humanoid"
    print("  ok  a missing blank line before the ability table header does not break the parse")

    # -- THE PAGE-SEAM TRAP: an action starting the very first line of a ----
    # new page, with no blank line at the seam, must still be recognised as
    # its own entry rather than swallowed into the previous action's
    # description (reproduces Air Elemental's Whirlwind exactly).
    found, anomalies, conflicts = wrap(
        "Air Elemental\n"
        "Air Elemental\n\n"
        "Large Elemental, Neutral\n\n"
        "AC 15\n\n"
        "Initiative +5 (15)\n"
        "HP 90 (12d10 + 24)\n"
        "Speed 10 ft., Fly 90 ft. (hover)\n\n"
        "MOD SAVE\nMOD SAVE\nMOD SAVE\n"
        "Str 14 +2\n+2\nDex 20 +5\n+5\nCon 14 +2\n+2\nInt 6\n−2\n−2\nWis 10 +0 +0\nCha 6\n−2\n−2\n\n"
        "Senses Darkvision 60 ft.; Passive Perception 10\n"
        "Languages Primordial (Auran)\n"
        "CR 5 (XP 1,800; PB +3)\n\n"
        "Actions\n\n"
        "Multiattack. The elemental makes two Thunderous\n"
        "Slam attacks.\n\n"
        "Thunderous Slam. Melee Attack Roll: +8, reach 10 ft.\n"
        "Hit: 14 (2d8 + 5) Thunder damage.",
        "Whirlwind (Recharge 4–6). Strength Saving Throw: DC\n"
        "13, one Medium or smaller creature in the elemental’s\n"
        "space. Failure: 24 (4d10 + 2) Thunder damage.\n",
    )
    assert len(found) == 1 and not anomalies, (found, anomalies)
    action_names = [a["name"] for a in found[0]["actions"]]
    assert action_names == ["Multiattack", "Thunderous Slam", "Whirlwind (Recharge 4–6)"], (
        "an action starting a fresh page with no blank line at the seam must "
        "not be swallowed into the previous action's description: %s" % action_names
    )
    print("  ok  a page transition with no blank line still separates two actions")

    # -- THE "Success:"/"Failure:" TRAP: a saving-throw effect clause uses a -
    # colon, not a period, and must never be mistaken for a new entry, even
    # though its own first sentence ends in a period within the same short
    # prefix a real entry name would use (reproduces Aboleth's Consume
    # Memories -> "Success: Half damage." exactly).
    found, anomalies, conflicts = wrap(
        "Aboleth\n"
        "Aboleth\n\n"
        "Large Aberration, Lawful Evil\n\n"
        "AC 17\n\n"
        "Initiative +7 (17)\n"
        "HP 150 (20d10 + 40)\n"
        "Speed 10 ft., Swim 40 ft.\n\n"
        "MOD SAVE\nMOD SAVE\nMOD SAVE\n"
        "Str 21 +5\n+5\nDex 9\n−1\n+3\nCon 15 +2\n+6\nInt 18 +4\n+8\nWis 15 +2\n+6\nCha 18 +4\n+4\n\n"
        "Senses Darkvision 120 ft.; Passive Perception 20\n"
        "Languages Deep Speech; telepathy 120 ft.\n"
        "CR 10 (XP 5,900, or 7,200 in lair; PB +4)\n\n"
        "Actions\n\n"
        "Consume Memories. Intelligence Saving Throw: DC 16,\n"
        "one creature within 30 feet. Failure: 10 (3d6) Psychic damage.\n\n"
        "Success: Half damage. Failure or Success: The aboleth\n"
        "gains the target’s memories if the target is Humanoid.\n\n"
        "Dominate Mind (2/Day). Wisdom Saving Throw: DC 16.\n"
    )
    assert len(found) == 1 and not anomalies, (found, anomalies)
    names = [a["name"] for a in found[0]["actions"]]
    assert names == ["Consume Memories", "Dominate Mind (2/Day)"], (
        "'Success:'/'Failure:' must fold into the preceding entry, not "
        "become one of its own: %s" % names
    )
    assert "Success: Half damage" in found[0]["actions"][0]["description"]
    print("  ok  a colon-introduced saving-throw clause is not mistaken for a new entry")

    # -- LEGENDARY ACTIONS: the fixed intro paragraph must be carved out, ---
    # not read as an entry named "Legendary Action Uses: 3 (4 in Lair)"
    found, anomalies, conflicts = wrap(
        "Ancient Black Dragon\n"
        "Gargantuan Dragon (Chromatic), Chaotic Evil\n\n"
        "AC 22\n\n"
        "Initiative +16 (26)\n"
        "HP 367 (21d20 + 147)\n"
        "Speed 40 ft., Fly 80 ft., Swim 40 ft.\n\n"
        "MOD SAVE\nMOD SAVE\nMOD SAVE\n"
        "Str 27 +8\n+8\nDex 14 +2\n+9\nCon 25 +7\n+7\nInt 16 +3\n+3\nWis 15 +2\n+9\nCha 22 +6\n+6\n\n"
        "Senses Blindsight 60 ft.; Passive Perception 26\n"
        "Languages Common, Draconic\n"
        "CR 21 (XP 33,000; PB +7)\n\n"
        "Actions\n\n"
        "Multiattack. The dragon makes three Rend attacks.\n\n"
        "Legendary Actions\n"
        "Legendary Action Uses: 3 (4 in Lair). Immediately after\n"
        "another creature’s turn, the dragon can expend a use to\n"
        "take one of the following actions.\n\n"
        "Pounce. The dragon moves up to half its Speed, and it\n"
        "makes one Rend attack.\n"
    )
    assert len(found) == 1 and not anomalies, (found, anomalies)
    la = found[0]["legendary_actions"]
    assert la["intro"].startswith("Legendary Action Uses: 3 (4 in Lair).")
    assert [o["name"] for o in la["options"]] == ["Pounce"]
    print("  ok  the Legendary Actions intro paragraph is carved out, not read as a bogus entry")

    # -- Traits is genuinely optional: a stat block that goes straight from -
    # CR to Actions must not be treated as missing anything (Animated Armor)
    found, anomalies, conflicts = wrap(
        "Animated Flying Sword\n\n"
        "Small Construct, Unaligned\n\n"
        "AC 17\n\n"
        "Initiative +4 (14)\n"
        "HP 14 (4d6)\n"
        "Speed 5 ft., Fly 50 ft. (hover)\n\n"
        "MOD SAVE\nMOD SAVE\nMOD SAVE\n"
        "Str 12 +1\n+1\nDex 15 +2\n+4\nCon 11 +0 +0\nInt 1\n−5\n−5\nWis 5\n−3\n−3\nCha 1\n−5\n−5\n\n"
        "Immunities Poison, Psychic\n"
        "Senses Blindsight 60 ft.; Passive Perception 7\n"
        "Languages None\n"
        "CR 1/4 (XP 50; PB +2)\n\n"
        "Actions\n\n"
        "Slash. Melee Attack Roll: +4, reach 5 ft. Hit: 6 (1d8 + 2)\n"
        "Slashing damage.\n"
    )
    assert len(found) == 1 and not anomalies, (found, anomalies)
    assert found[0]["traits"] == [] and found[0]["immunities"] == "Poison, Psychic"
    print("  ok  a stat block with no Traits section at all is not treated as an anomaly")

    # -- NEGATIVE CONTROL: an ordinary complete stat block is not wrongly ---
    # excluded
    found, anomalies, conflicts = wrap(
        "Owlbear\n"
        "Owlbear\n\n"
        "Large Monstrosity, Unaligned\n\n"
        "AC 13\n\n"
        "Initiative +1 (11)\n"
        "HP 59 (7d10 + 21)\n"
        "Speed 40 ft.\n\n"
        "MOD SAVE\nMOD SAVE\nMOD SAVE\n"
        "Str 20 +5\n+5\nDex 12 +1\n+1\nCon 17 +3\n+3\nInt 3\n−4 −4\nWis 12 +1\n+1\nCha 7\n−2\n−2\n\n"
        "Senses Darkvision 60 ft.; Passive Perception 11\n"
        "Languages None\n"
        "CR 3 (XP 700; PB +2)\n\n"
        "Actions\n\n"
        "Multiattack. The owlbear makes two attacks: one with its Beak and\n"
        "one with its Claws.\n\n"
        "Beak. Melee Attack Roll: +7, reach 5 ft. Hit: 10 (1d10 + 5)\n"
        "Piercing damage.\n"
    )
    assert len(found) == 1 and not anomalies and not conflicts, (
        "an ordinary, complete stat block must parse cleanly: %s / %s" % (found, anomalies)
    )
    print("  ok  negative control: an ordinary complete stat block is not wrongly excluded")

    print("PASS test_parse_monsters_en")


if __name__ == "__main__":
    main()
