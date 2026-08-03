"""Calibration checks for the English feat parser.

Each scenario reproduces a shape found calibrating parse_feats_en.py against
the pinned EN PDF, plus a negative control.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_feats_en  # noqa: E402


def page(*blocks):
    return extract.normalise("\n".join(blocks))


def wrap(*feat_blocks, suspect=()):
    pages = [page("Feats\n")] + list(feat_blocks) + [page("Equipment\n\nCoins\n")]
    return parse_feats_en.parse(pages, suspect)


def main():
    # -- no prerequisite at all --------------------------------------------
    feats, anomalies, conflicts = wrap(page(
        "Alert\nOrigin Feat\n",
        "You gain the following benefits.\n",
    ))
    assert len(feats) == 1 and not anomalies and not conflicts, (feats, anomalies)
    f = feats[0]
    assert f["category"] == "origin" and f["prerequisite"] is None
    print("  ok  a feat with no prerequisite parses cleanly")

    # -- a single-line, fully-closed prerequisite ---------------------------
    feats, anomalies, conflicts = wrap(page(
        "Ability Score Improvement\nGeneral Feat (Prerequisite: Level 4+)\n",
        "Increase one ability score of your choice by 2.\n",
    ))
    assert len(feats) == 1 and not anomalies
    assert feats[0]["prerequisite"] == "Prerequisite: Level 4+"
    print("  ok  a single-line prerequisite is captured")

    # -- THE TRAP: the prerequisite clause wraps and does NOT close on the -
    # head's own line at all ("General Feat (Prerequisite: Level 4+,
    # Strength or" / "Dexterity 13+)"). A regex requiring the closing paren
    # on the same line fails to match the head at all -- not an anomaly,
    # a silent disappearance. Reproduces Grappler exactly.
    feats, anomalies, conflicts = wrap(page(
        "Grappler\nGeneral Feat (Prerequisite: Level 4+, Strength or\n"
        "Dexterity 13+)\n",
        "You gain the following benefits.\n",
    ))
    assert len(feats) == 1 and not anomalies, (
        "an unclosed prerequisite paren must not make the head invisible: %s / %s"
        % (feats, anomalies)
    )
    assert feats[0]["prerequisite"] == "Prerequisite: Level 4+, Strength or Dexterity 13+", (
        feats[0]["prerequisite"]
    )
    print("  ok  a prerequisite that wraps past the line with no closing paren is not lost")

    # -- category word order differs from a magic item's ("<Category> Feat" -
    # not "Feat, <Category>") and Fighting Style is two words ------------
    feats, anomalies, conflicts = wrap(page(
        "Archery\nFighting Style Feat (Prerequisite: Fighting Style\nFeature)\n",
        "You gain a +2 bonus to attack rolls you make with Ranged weapons.\n",
    ))
    assert len(feats) == 1 and not anomalies
    assert feats[0]["category"] == "fighting-style"
    assert feats[0]["prerequisite"] == "Prerequisite: Fighting Style Feature", feats[0]["prerequisite"]
    print("  ok  the two-word 'Fighting Style' category and its wrap are handled")

    # -- NEGATIVE CONTROL: an ordinary feat is not wrongly excluded --------
    feats, anomalies, conflicts = wrap(page(
        "Skilled\nOrigin Feat\n",
        "You gain proficiency in any combination of three skills or tools.\n",
    ))
    assert len(feats) == 1 and not anomalies and not conflicts, (
        "an ordinary, complete feat must parse cleanly: %s / %s" % (feats, anomalies)
    )
    print("  ok  negative control: an ordinary complete feat is not wrongly excluded")

    print("PASS test_parse_feats_en")


if __name__ == "__main__":
    main()
