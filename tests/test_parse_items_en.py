"""Calibration checks for the English magic item parser.

Each scenario reproduces a shape found calibrating parse_items_en.py against
the pinned EN PDF, plus a negative control. Built with `extract.normalise()`
so paragraph-break behaviour matches the real pipeline.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_items_en  # noqa: E402

CHAPTER_START = "Magic Items A–Z\n"
CHAPTER_END_BLOCK = "Monsters\n\nStat Block Overview\n"


def page(*blocks):
    raw = "\n".join(blocks)
    return extract.normalise(raw)


def wrap(*item_blocks, suspect=()):
    """Sandwich item blocks between the chapter start and end anchors, on
    their own pages, so the chapter-bounding logic behaves like it does on
    the real document without needing the real document."""
    pages = [page(CHAPTER_START)] + list(item_blocks) + [page(CHAPTER_END_BLOCK)]
    return parse_items_en.parse(pages, suspect)


def main():
    # -- ordinary entry: name, type line, blank, description -------------
    items, anomalies, conflicts = wrap(page(
        "Bag of Beans\nWondrous Item, Rare\n",
        "This heavy cloth bag contains 3d4 dry beans when found.\n",
    ))
    assert len(items) == 1 and not anomalies and not conflicts, (items, anomalies)
    it = items[0]
    assert it["category"] == "wondrous-item" and it["subtype"] is None
    assert it["rarity"] == "Rare" and it["attunement"] is False
    print("  ok  ordinary entry: name / type / description")

    # -- subtype in parens, attunement detected ----------------------------
    items, anomalies, conflicts = wrap(page(
        "Amulet of Health\nWondrous Item, Rare (Requires Attunement)\n",
        "Your Constitution is 19 while you wear this amulet.\n",
    ))
    assert len(items) == 1 and not anomalies
    it = items[0]
    assert it["attunement"] is True
    assert it["rarity"] == "Rare (Requires Attunement)"
    print("  ok  attunement detected from the type line")

    # -- wrapped rarity clause, subtype present ----------------------------
    items, anomalies, conflicts = wrap(page(
        "Armor of Vulnerability\nArmor (Any Light, Medium, or Heavy), Rare (Requires\n"
        "Attunement)\n",
        "While wearing this armor, you have Resistance to one damage type.\n",
    ))
    assert len(items) == 1 and not anomalies
    it = items[0]
    assert it["subtype"] == "Any Light, Medium, or Heavy"
    assert it["rarity"] == "Rare (Requires Attunement)", it["rarity"]
    assert it["attunement"] is True
    print("  ok  a wrapped rarity clause is reassembled, not truncated")

    # -- THE TRAP: a generic "+1, +2, or +3" item's NAME is itself shaped --
    # like a type line, sitting directly above the real one. Reproduces
    # Armor, +1, +2, or +3 exactly.
    items, anomalies, conflicts = wrap(
        page("Some Other Item\nWondrous Item, Common\n", "Filler text.\n"),
        page(
            "Armor, +1, +2, or +3\nArmor (Any Light, Medium, or Heavy), Rare (+1), Very\n"
            "Rare (+2), or Legendary (+3)\n",
            "You have a bonus to Armor Class while wearing this armor.\n",
        ),
    )
    names = [it["name"] for it in items]
    assert "Armor, +1, +2, or +3" in names, names
    assert not anomalies, anomalies
    armor = next(it for it in items if it["name"] == "Armor, +1, +2, or +3")
    assert armor["rarity"] == "Rare (+1), Very Rare (+2), or Legendary (+3)", armor["rarity"]
    print("  ok  a name shaped like a type line is not mistaken for one")

    # -- the name itself wraps onto two lines ------------------------------
    items, anomalies, conflicts = wrap(page(
        "Amulet of Proof against Detection\nand Location\n"
        "Wondrous Item, Uncommon (Requires Attunement)\n",
        "While wearing this amulet, you can't be targeted by Divination spells.\n",
    ))
    assert len(items) == 1 and not anomalies, (items, anomalies)
    assert items[0]["name"] == "Amulet of Proof against Detection and Location", items[0]["name"]
    print("  ok  a name that wraps onto two lines is reassembled")

    # -- THE BUG FOUND BY MEASURING THE REAL COUNT: the rarity clause can --
    # wrap such that NOTHING follows the comma on the type line itself
    # ("Armor (Any Medium or Heavy, Except Hide Armor)," / "Uncommon" on the
    # next line alone). A regex requiring at least one character after the
    # comma silently dropped this and 3 other real items with no anomaly
    # raised at all -- caught only because the total came out 4 short of a
    # second, independent run. Reproduces Adamantine Armor exactly.
    items, anomalies, conflicts = wrap(page(
        "Adamantine Armor\nArmor (Any Medium or Heavy, Except Hide Armor),\n"
        "Uncommon\n",
        "This suit of armor is reinforced with adamantine.\n",
    ))
    assert len(items) == 1 and not anomalies, (
        "a rarity clause with nothing after the comma on its own line must "
        "not be silently dropped: %s / %s" % (items, anomalies)
    )
    assert items[0]["rarity"] == "Uncommon", items[0]["rarity"]
    assert items[0]["subtype"] == "Any Medium or Heavy, Except Hide Armor"
    print("  ok  a rarity clause with nothing after the comma is not silently dropped")

    # -- a genuinely unparseable block is excluded, not half-filled --------
    items, anomalies, conflicts = wrap(
        page("Wondrous Item, Rare\n"),  # no plausible name line above it at all
        page("Good Item\nWondrous Item, Common\n", "A fine description.\n"),
    )
    names = [it["name"] for it in items]
    assert "Good Item" in names, names
    assert any(a for a in anomalies), "the nameless block should have been excluded"
    print("  ok  a block with no plausible name is excluded, not guessed at")

    # -- NEGATIVE CONTROL: an ordinary entry is not wrongly excluded -------
    items, anomalies, conflicts = wrap(page(
        "Ordinary Ring\nRing, Uncommon (Requires Attunement)\n",
        "It does something ordinary.\n",
    ))
    assert len(items) == 1 and not anomalies and not conflicts, (
        "an ordinary, complete item must parse cleanly: %s / %s" % (items, anomalies)
    )
    print("  ok  negative control: an ordinary complete item is not wrongly excluded")

    print("PASS test_parse_items_en")


if __name__ == "__main__":
    main()
