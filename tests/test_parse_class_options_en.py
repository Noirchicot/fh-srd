"""Calibration checks for the English class-option parser.

Both lists come out of ONE module (`class_options.py`), so one fixture
exercises both, and the traps are checked where they actually live:

  * a head is a bare NAME — no label, no punctuation, nothing in the text
    stream separates it from the first line of a paragraph. Five of the
    twenty-eight invocations have no prerequisite line either, so the shape is
    literally "short line, then prose";
  * a body line that looks exactly like a head (`Repeatable.`, `Quick Attack.`,
    `Cantrips and Rituals.`) must NOT become an entry — and the only thing that
    says so is the face the source sets it in;
  * a head that opens a PAGE, with the previous page's last body line
    immediately before it in the stream and no blank line between;
  * `Metamagic Options` is not a unique line: the class feature twenty lines
    above names the section in running prose;
  * ⛔ an invocation carries NO `cost` key and a metamagic carries one — the
    asymmetry is the rule, not an oversight;
  * a list that comes back short REFUSES, and so does one out of order.

The twenty-eight and ten names below are the real ones, read off the pinned
PDF; the bodies are stubs. That makes this fixture a second, independent
statement of what the source contains — if the parser ever comes back with a
different set, this file disagrees with it rather than agreeing by
construction.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import class_options  # noqa: E402
import extract  # noqa: E402
import parse_class_options_en as parser  # noqa: E402

# (name, prerequisite or None). Alphabetical, as the source states it is.
INVOCATIONS = [
    ("Agonizing Blast", "Level 2+ Warlock, a Warlock Cantrip\nThat Deals Damage"),
    ("Armor of Shadows", None),
    ("Ascendant Step", "Level 5+ Warlock"),
    ("Devil’s Sight", "Level 2+ Warlock"),
    ("Devouring Blade", "Level 12+ Warlock, Thirsting Blade\nInvocation"),
    ("Eldritch Mind", None),
    ("Eldritch Smite", "Level 5+ Warlock, Pact of the Blade\nInvocation"),
    ("Eldritch Spear", "Level 2+ Warlock, a Warlock Cantrip\nThat Deals Damage"),
    ("Fiendish Vigor", "Level 2+ Warlock"),
    ("Gaze of Two Minds", "Level 5+ Warlock"),
    ("Gift of the Depths", "Level 5+ Warlock"),
    ("Gift of the Protectors", "Level 9+ Warlock, Pact of the Tome\nInvocation"),
    ("Investment of the Chain Master", "Level 5+ Warlock, Pact of the Chain\nInvocation"),
    ("Lessons of the First Ones", "Level 2+ Warlock"),
    ("Lifedrinker", "Level 9+ Warlock, Pact of the Blade\nInvocation"),
    ("Mask of Many Faces", "Level 2+ Warlock"),
    ("Master of Myriad Forms", "Level 5+ Warlock"),
    ("Misty Visions", "Level 2+ Warlock"),
    ("One with Shadows", "Level 5+ Warlock"),
    ("Otherworldly Leap", "Level 2+ Warlock"),
    ("Pact of the Blade", None),
    ("Pact of the Chain", None),
    ("Pact of the Tome", None),
    ("Repelling Blast", "Level 2+ Warlock, a Warlock Cantrip\nThat Deals Damage via an Attack Roll"),
    ("Thirsting Blade", "Level 5+ Warlock, Pact of the Blade\nInvocation"),
    ("Visions of Distant Realms", "Level 9+ Warlock"),
    ("Whispers of the Grave", "Level 7+ Warlock"),
    ("Witch Sight", "Level 15+ Warlock"),
]

# (name, cost). Every one of the ten carries one.
METAMAGIC = [
    ("Careful Spell", "1 Sorcery Point"),
    ("Distant Spell", "1 Sorcery Point"),
    ("Empowered Spell", "1 Sorcery Point"),
    ("Extended Spell", "1 Sorcery Point"),
    ("Heightened Spell", "2 Sorcery Points"),
    ("Quickened Spell", "2 Sorcery Points"),
    ("Seeking Spell", "1 Sorcery Point"),
    ("Subtle Spell", "1 Sorcery Point"),
    ("Transmuted Spell", "1 Sorcery Point"),
    ("Twinned Spell", "1 Sorcery Point"),
]

# The four body lines that would pass any "short line, title case, no full
# stop needed" rule and are not heads. Hung on one entry so the whole fixture
# carries the trap.
DECOY_BODY = (
    "Repeatable. You can gain this invocation more\n"
    "than once. Each time you do so, choose a different\n"
    "eligible cantrip."
)


def entry(name, clause_label, clause, body):
    out = [name]
    if clause:
        out.append("%s %s" % (clause_label, clause.split("\n")[0]))
        out.extend(clause.split("\n")[1:])
    out.append("")
    out.append(body)
    return "\n".join(out)


def sections(invocations=INVOCATIONS, metamagic=METAMAGIC):
    """The two sections as they are printed, plus the decoy above each."""
    inv = [
        "Level 20: Eldritch Master",
        "When you use your Magical Cunning feature, you",
        "regain all expended Pact Magic spell slots.",
        "Eldritch Invocation Options",
        "",
        "Eldritch Invocation options appear in alphabetical",
        "order.",
        "",
    ]
    for i, (name, prereq) in enumerate(invocations):
        body = DECOY_BODY if name == "Agonizing Blast" else \
            "Body of %s, which is prose and not a head." % name
        inv.append(entry(name, "Prerequisite:", prereq, body))
        inv.append("")
    inv.append("Warlock Spell List")

    meta = [
        "Level 2: Metamagic",
        "you gain two Metamagic options of your choice from",
        "“Metamagic Options” later in this class’s description.",
        "Metamagic Options",
        "",
        "The following options are available to your Metamagic",
        "feature. The options are presented in alphabetical order.",
        "",
    ]
    for name, cost in metamagic:
        meta.append(entry(name, "Cost:", cost,
                          "Body of %s, which is prose and not a head." % name))
        meta.append("")
    meta.append("Sorcerer Spell List")
    return "\n".join(meta), "\n".join(inv)


def pages_and_layout(invocations=INVOCATIONS, metamagic=METAMAGIC, split=True):
    """Two or three pages, with the head channel `extract.heads_of` produces.

    `split` cuts the invocation section mid-entry so that a head opens a page
    with no blank line before it — the shape that costs exactly one entry per
    language if the group rule is "preceded by a blank line" alone.
    """
    meta, inv = sections(invocations, metamagic)
    names = [n for n, _ in invocations] + [n for n, _ in metamagic]

    if split:
        lines = inv.split("\n")
        cut = lines.index("Pact of the Blade")
        pages = [meta, "\n".join(lines[:cut]), "\n".join(lines[cut:])]
    else:
        pages = [meta, inv]

    pages = [extract.normalise(p) for p in pages]
    layout = [{"tables": [], "emphasis": [],
               "heads": [n for n in names if n in page.split("\n")]}
              for page in pages]
    return pages, layout


def by_name(records):
    return {r["name"]: r for r in records}


def main():
    pages, layout = pages_and_layout()
    records, anomalies, conflicts = parser.parse(pages, (), layout)
    assert not anomalies, anomalies
    assert not conflicts, conflicts
    assert len(records) == 38, len(records)

    inv = [r for r in records if r["category"] == "eldritch-invocation"]
    meta = [r for r in records if r["category"] == "metamagic"]
    assert len(inv) == 28, len(inv)
    assert len(meta) == 10, len(meta)
    print("  ok  28 Eldritch Invocations and 10 Metamagic options, "
          "from two sections read in one pass")

    got = by_name(records)
    assert set(got) == set(n for n, _ in INVOCATIONS) | set(n for n, _ in METAMAGIC)
    print("  ok  every one of the 38 names comes back, and nothing else")

    # -- the five with no prerequisite line at all -------------------------
    bare = sorted(r["name"] for r in inv if r["prerequisite"] is None)
    assert bare == ["Armor of Shadows", "Eldritch Mind", "Pact of the Blade",
                    "Pact of the Chain", "Pact of the Tome"], bare
    print("  ok  the 5 invocations printed as name-then-prose are read: %s"
          % ", ".join(bare))

    # -- a wrapped prerequisite comes back whole ---------------------------
    assert got["Agonizing Blast"]["prerequisite"] == (
        "Level 2+ Warlock, a Warlock Cantrip That Deals Damage"
    ), got["Agonizing Blast"]["prerequisite"]
    print("  ok  a prerequisite that wraps across two lines is rejoined")

    # -- ⛔ THE ASYMMETRY --------------------------------------------------
    assert all("cost" not in r for r in inv), [r["name"] for r in inv if "cost" in r]
    assert all(r.get("cost") for r in meta), meta
    assert got["Heightened Spell"]["cost"] == "2 Sorcery Points"
    assert all(r["prerequisite"] is None for r in meta), meta
    print("  ok  a manifestation carries NO cost key (free once taken); "
          "all 10 metamagic options carry one (paid at every use)")

    # -- the decoy body lines are not entries ------------------------------
    assert "Repeatable." not in got
    assert "Repeatable. You can gain this invocation more" in \
        got["Agonizing Blast"]["description"], got["Agonizing Blast"]["description"]
    print("  ok  'Repeatable.' stays inside the body it belongs to")

    # -- a head that opens a page ------------------------------------------
    assert got["Pact of the Blade"]["page"] == 3, got["Pact of the Blade"]
    assert got["Otherworldly Leap"]["page"] == 2, got["Otherworldly Leap"]
    print("  ok  an entry whose head is the first line of a page is read")

    # -- the section heading is not the first line that says so ------------
    assert got["Careful Spell"]["page"] == 1
    assert "Metamagic Options" not in got
    assert "Level 2: Metamagic" not in got
    print("  ok  the class feature that NAMES the section in prose does not "
          "open it")

    # -- the head channel is not optional ----------------------------------
    blind = [{"tables": [], "emphasis": [], "heads": []} for _ in pages]
    try:
        parser.parse(pages, (), blind)
    except class_options.ListCountError as exc:
        assert "entry heads" in str(exc), exc
        print("  ok  without the source's own typography the parser REFUSES "
              "rather than guessing at line shapes")
    else:
        raise AssertionError("a missing head channel must stop the build")

    # -- a document that prints neither section is not a failure -----------
    empty = parser.parse([extract.normalise("Fireball\nA bright streak.")], (),
                         [{"tables": [], "emphasis": [], "heads": []}])
    assert empty == ([], [], []), empty
    print("  ok  a source without either section yields nothing and says so "
          "by yielding nothing (this is --fixture)")

    # -- a list short of one entry REFUSES ---------------------------------
    short = [e for e in INVOCATIONS if e[0] != "Witch Sight"]
    try:
        parser.parse(*_call(pages_and_layout(invocations=short)))
    except class_options.ListCountError as exc:
        assert "27 entries, expected 28" in str(exc), exc
        print("  ok  a list short of one entry REFUSES, naming the count")
    else:
        raise AssertionError("27 invocations must stop the build, not export 27")

    # -- a list out of order REFUSES ---------------------------------------
    swapped = list(INVOCATIONS)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    try:
        parser.parse(*_call(pages_and_layout(invocations=swapped)))
    except class_options.ListCountError as exc:
        assert "alphabetical" in str(exc), exc
        print("  ok  a list whose names stop increasing REFUSES: the source "
              "states the order, so a break in it is a misread region")
    else:
        raise AssertionError("an out-of-order list must stop the build")

    # -- a disputed page sends its records to the exclusion register --------
    records, anomalies, conflicts = parser.parse(pages, [1], layout)
    assert len(conflicts) == 10 and not any(
        r["category"] == "metamagic" for r in records), (len(conflicts), records)
    print("  ok  an extractor-disputed page yields conflicts, not records")

    # -- a head-face line inside a BODY is named ---------------------------
    pages2, layout2 = pages_and_layout(split=False)
    pages2 = [p.replace("Body of Eldritch Mind, which is prose and not a head.",
                        "Body of Eldritch Mind.\nWitch Sight\nand more prose.")
              for p in pages2]
    records, anomalies, conflicts = parser.parse(pages2, (), layout2)
    assert len(records) == 38, len(records)
    assert len(anomalies) == 1, anomalies
    assert "Witch Sight" in anomalies[0]["detail"], anomalies[0]
    assert "inside the body" in anomalies[0]["detail"], anomalies[0]
    print("  ok  a head-face line printed inside a body is named, not swallowed")

    print("PASS test_parse_class_options_en")


def _call(pages_and_layout_result):
    pages, layout = pages_and_layout_result
    return pages, (), layout


if __name__ == "__main__":
    main()
