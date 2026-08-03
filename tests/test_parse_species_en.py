"""Calibration checks for the English species parser.

Each scenario reproduces a shape found calibrating parse_species_en.py
against the pinned EN PDF, plus negative controls.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_species_en  # noqa: E402


def page(*blocks):
    return extract.normalise("\n".join(blocks))


def wrap(*species_blocks, suspect=()):
    pages = [page("Character Origins\n\nCharacter Species\n\nSpecies Descriptions\n")] \
        + list(species_blocks) \
        + [page("Feats\n\nFeat Descriptions\n")]
    return parse_species_en.parse(pages, suspect)


def main():
    # -- an ordinary, complete species entry ---------------------------------
    sp, anomalies, conflicts = wrap(page(
        "Dwarf\n"
        "Creature Type: Humanoid\n"
        "Size: Medium (about 4–5 feet tall)\n"
        "Speed: 30 feet\n"
        "\n"
        "As a Dwarf, you have these special traits.\n"
        "\n"
        "Darkvision. You have Darkvision with a range of 120 feet.\n",
    ))
    assert len(sp) == 1 and not anomalies and not conflicts, (sp, anomalies)
    d = sp[0]
    assert d["creature_type"] == "Humanoid"
    assert d["size"] == "Medium (about 4–5 feet tall)"
    assert d["speed"] == "30 feet"
    assert d["description"].startswith("As a Dwarf, you have these special traits.")
    assert d["description"].endswith("120 feet.")
    print("  ok  an ordinary species entry parses cleanly")

    # -- THE REGRESSION THIS SUITE EXISTS TO PIN: unlike a spell/item/feat's -
    # head, a species' head IS its own name line -- there is no separate name
    # line living above a stat line that could leak into the description and
    # need trimming. An earlier version of this parser copied that trim step
    # from the sibling parsers anyway, and it silently ate the LAST SENTENCE
    # of every species description that has a following entry (8 of 9 species
    # in the real PDF, caught only by reading Dragonborn's description
    # end-to-end against the rendered page and finding it stopped mid-word).
    # This reproduces that exact shape: a following entry immediately after,
    # with the FIRST species' final sentence intact.
    sp, anomalies, conflicts = wrap(page(
        "Orc\n"
        "Creature Type: Humanoid\n"
        "Size: Medium (about 6–7 feet tall)\n"
        "Speed: 30 feet\n"
        "\n"
        "As an Orc, you have these special traits.\n"
        "\n"
        "Relentless Endurance. When you are reduced to 0 Hit Points but\n"
        "not killed outright, you can drop to 1 Hit Point instead. Once\n"
        "you use this trait, you can’t do so again until you finish a\n"
        "Long Rest.\n"
        "\n"
        "Tiefling\n"
        "Creature Type: Humanoid\n"
        "Size: Medium (about 4–7 feet tall)\n"
        "Speed: 30 feet\n"
        "\n"
        "As a Tiefling, you have the following special traits.\n",
    ))
    assert len(sp) == 2 and not anomalies, (sp, anomalies)
    orc = [s for s in sp if s["name"] == "Orc"][0]
    assert orc["description"].endswith("finish a Long Rest."), (
        "the last sentence before a following entry must survive intact: %r"
        % orc["description"]
    )
    assert "Tiefling" not in orc["description"]
    print("  ok  regression: the last sentence before a following entry is not trimmed away")

    # -- a wrapped two-line Size field (Human/Tiefling's real shape: "Medium -
    # (...) or Small (...), chosen when you select this species") ----------
    sp, anomalies, conflicts = wrap(page(
        "Human\n"
        "Creature Type: Humanoid\n"
        "Size: Medium (about 4–7 feet tall) or Small (about 2–4\n"
        "feet tall), chosen when you select this species\n"
        "Speed: 30 feet\n"
        "\n"
        "As a Human, you have these special traits.\n"
        "\n"
        "Skillful. You gain proficiency in one skill of your choice.\n",
    ))
    assert len(sp) == 1 and not anomalies, (sp, anomalies)
    assert sp[0]["size"] == (
        "Medium (about 4–7 feet tall) or Small (about 2–4 feet tall), "
        "chosen when you select this species"
    ), sp[0]["size"]
    print("  ok  a Size field wrapping across two lines is joined correctly")

    # -- NEGATIVE CONTROL: a species missing a required field is reported, --
    # not guessed at or silently filled from a neighbour.
    sp, anomalies, conflicts = wrap(page(
        "Gnome\n"
        "Creature Type: Humanoid\n"
        "Speed: 30 feet\n"
        "\n"
        "As a Gnome, you have these special traits.\n",
    ))
    assert len(sp) == 0 and len(anomalies) == 1, (sp, anomalies)
    assert "size" in anomalies[0]["detail"]
    print("  ok  negative control: a missing Size field is reported, not silently skipped")

    print("PASS test_parse_species_en")


if __name__ == "__main__":
    main()
