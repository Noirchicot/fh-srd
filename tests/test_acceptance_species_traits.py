"""Acceptance: the species records this lot was commissioned to repair.

READS ONLY `exports/`. Not the database, not the parsers, not the PDF — the
files `fhpc` actually consumes. A repair that works in the parser and does not
reach the export is not a repair.

EVERY EXPECTED VALUE IS WRITTEN OUT IN FULL, and that is the point rather than
a style. A count stays green when the pipeline returns N wrong things: "the Elf
has 5 traits" passes just as happily on five copies of the Tiefling's. So the
trait names are listed, the lineage spells are listed, and the Human's whole
description is pinned character for character.

THE THREE CLAIMS, from the lot's own commission:

  1. `srd:species:en:human` no longer contains a line of the Tiefling.
  2. The French Elf renders its named traits in the order of the book.
  3. The Wood Elf's two spells come back separated.

In French AND English, from the exports alone.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(ROOT, "exports", "srd")


def load(lang, kind):
    path = os.path.join(EXPORTS, lang, "%s.json" % kind)
    if not os.path.exists(path):
        raise AssertionError(
            "%s does not exist. This suite reads the exports and nothing else, so "
            "a missing export is a failure, never a reason to skip." % path
        )
    with open(path, encoding="utf-8") as fh:
        return {r["id"]: r for r in json.load(fh)["records"]}


# The Human's whole description, as the SRD prints it and nothing more. Pinned
# in full because the defect this replaces was an ADDITION: the record used to
# be 541 characters and end on the Tiefling's legacy table.
HUMAN_EN = (
    "As a Human, you have these special traits.\n"
    "\n"
    "Resourceful. You gain Heroic Inspiration whenever you finish a Long Rest.\n"
    "\n"
    "Skillful. You gain proficiency in one skill of your choice.\n"
    "\n"
    "Versatile. You gain an Origin feat of your choice (see “Feats”). Skilled is "
    "recommended."
)

# What the Tiefling's table says, verbatim. None of it may appear in the Human.
TIEFLING_LINES = [
    "Fiendish Legacies",
    "Legacy Level 1 Level 3 Level 5",
    "Abyssal",
    "Chthonic",
    "Infernal",
    "Ray of Sickness",
    "Hold Person",
]

TRAITS = {
    ("en", "elf"): ["Darkvision", "Elven Lineage", "Fey Ancestry", "Keen Senses", "Trance"],
    ("fr", "elfe"): ["Ascendance féerique", "Lignage elfique", "Sens aiguisés",
                     "Transe", "Vision dans le noir"],
    ("en", "human"): ["Resourceful", "Skillful", "Versatile"],
    ("fr", "humain"): ["Compétent", "Ingénieux", "Polyvalent"],
    ("en", "tiefling"): ["Darkvision", "Fiendish Legacy", "Otherworldly Presence"],
    ("fr", "tieffelin"): ["Héritage fiélon", "Présence d’outre-monde", "Vision dans le noir"],
}

LINEAGES = {
    ("en", "elf"): [
        ("drow", "Drow", "Faerie Fire", "Darkness"),
        ("high-elf", "High Elf", "Detect Magic", "Misty Step"),
        ("wood-elf", "Wood Elf", "Longstrider", "Pass without Trace"),
    ],
    ("fr", "elfe"): [
        ("drow", "Drow", "lueurs féeriques", "ténèbres"),
        ("elfe-sylvestre", "Elfe sylvestre", "grande foulée", "passage sans trace"),
        ("haut-elfe", "Haut-elfe", "détection de la magie", "foulée brumeuse"),
    ],
    ("en", "tiefling"): [
        ("abyssal", "Abyssal", "Ray of Sickness", "Hold Person"),
        ("chthonic", "Chthonic", "False Life", "Ray of Enfeeblement"),
        ("infernal", "Infernal", "Hellish Rebuke", "Darkness"),
    ],
    ("fr", "tieffelin"): [
        ("abyssal", "Abyssal", "rayon empoisonné", "immobilisation de personne"),
        ("chtonien", "Chtonien", "simulacre de vie", "rayon affaiblissant"),
        ("infernal", "Infernal", "représailles infernales", "ténèbres"),
    ],
}


def main():
    species = {lang: load(lang, "species") for lang in ("en", "fr")}

    # -- CLAIM 1: the Human is the Human ------------------------------------
    human = species["en"]["srd:species:en:human"]["data"]
    assert human["description"] == HUMAN_EN, (
        "the Human's description is not the SRD's Human paragraph:\n%r" % human["description"]
    )
    for line in TIEFLING_LINES:
        assert line not in human["description"], (
            "the Human's description still carries the Tiefling's %r" % line
        )
    assert len(human["description"]) == 268, len(human["description"])
    print("  ok  claim 1: srd:species:en:human is 268 characters and none of them are the Tiefling's")

    # and the table is where it belongs, not merely gone from the Human
    tiefling = species["en"]["srd:species:en:tiefling"]["data"]
    assert "Fiendish Legacies" in tiefling["description"]
    assert "Chthonic You have Resistance to Necrotic damage." in tiefling["description"]
    print("  ok  claim 1b: the Fiendish Legacies table is inside the Tiefling, not merely deleted")

    # -- CLAIM 2: named traits, in the book's order, both languages ----------
    for (lang, slug), expected in sorted(TRAITS.items()):
        record = species[lang]["srd:species:%s:%s" % (lang, slug)]["data"]
        names = [t["name"] for t in record.get("traits", [])]
        assert names == expected, "%s/%s traits are %r, expected %r" % (lang, slug, names, expected)
        for trait in record["traits"]:
            assert trait["id"] and trait["name"] and trait["text"], trait
            assert not trait["text"].startswith("."), trait
    print("  ok  claim 2: every named trait of six species, in printed order, in both languages")

    # The French Elf is the one the refusal was measured on: its Darkvision used
    # to arrive at character 1781, AFTER a lineage table that began at 305.
    elfe = species["fr"]["srd:species:fr:elfe"]["data"]
    lineage_at = elfe["description"].index("Lignages elfiques\n\nLignage")
    darkvision = [t for t in elfe["traits"] if t["name"] == "Vision dans le noir"][0]
    assert darkvision["text"] == "Vous disposez de la Vision dans le noir sur 18 m.", darkvision
    assert elfe["traits"][-1]["name"] == "Vision dans le noir"
    assert lineage_at > 0
    print("  ok  claim 2b: the French Elf's Darkvision is a named trait with its own text, "
          "not a sentence stranded after a table")

    # -- CLAIM 3: the Wood Elf's two spells are two ---------------------------
    for (lang, slug), expected in sorted(LINEAGES.items()):
        record = species[lang]["srd:species:%s:%s" % (lang, slug)]["data"]
        got = [(l["id"], l["name"], l["levels"]["3"], l["levels"]["5"])
               for l in record.get("lineages", [])]
        assert got == expected, "%s/%s lineages are %r, expected %r" % (lang, slug, got, expected)
    print("  ok  claim 3: twelve lineages, each with its level 3 and level 5 spell SEPARATE, "
          "in both languages")

    for (lang, slug, name), joined in (
        (("en", "elf", "Wood Elf"), "Longstrider Pass without Trace"),
        (("fr", "elfe", "Elfe sylvestre"), "grande foulée passage sans trace"),
    ):
        record = species[lang]["srd:species:%s:%s" % (lang, slug)]["data"]
        row = [l for l in record["lineages"] if l["name"] == name][0]
        assert joined not in row["levels"].values(), (
            "the two spells came back as one string again: %r" % joined
        )
        assert row["levels"]["1"].endswith("cantrip.") or row["levels"]["1"].endswith("druidisme."), \
            row["levels"]["1"]
    print("  ok  claim 3b: %r and %r are not a cell in any lineage"
          % ("Longstrider Pass without Trace", "grande foulée passage sans trace"))

    # -- the fields the previous lot delivered must have survived -------------
    elf = species["en"]["srd:species:en:elf"]["data"]
    assert elf["senses"] == [{"id": "darkvision", "name": "Darkvision", "range_ft": 60}], elf["senses"]
    assert elf["granted_skill_choice"] == {
        "count": 1,
        "from": ["srd:skill:en:insight", "srd:skill:en:perception", "srd:skill:en:survival"],
    }, elf["granted_skill_choice"]
    assert elfe["senses"] == [
        {"id": "darkvision", "name": "Vision dans le noir", "range_m": 18}], elfe["senses"]
    assert elfe["granted_skill_choice"]["count"] == 1
    assert species["fr"]["srd:species:fr:nain"]["data"]["senses"][0]["range_m"] == 36
    print("  ok  senses and granted_skill_choice survived the reshape, values named")

    # -- every species, both languages, has traits ---------------------------
    for lang in ("en", "fr"):
        total = 0
        for record in species[lang].values():
            traits = record["data"].get("traits")
            assert traits, "%s has no traits" % record["id"]
            total += len(traits)
        assert total == 33, "%s has %d traits across nine species, expected 33" % (lang, total)
    print("  ok  33 named traits per language, nine species each, none empty")

    # -- NEGATIVE CONTROL ----------------------------------------------------
    # A suite that cannot fail cannot pass. The Human's description is pinned
    # above; prove that pin is live by checking a value that is deliberately
    # NOT what the record says.
    failed = False
    try:
        assert human["description"] == HUMAN_EN + " Fiendish Legacies"
    except AssertionError:
        failed = True
    assert failed, "the negative control did not fail; these assertions prove nothing"

    failed = False
    try:
        row = [l for l in elf["lineages"] if l["name"] == "Wood Elf"][0]
        assert row["levels"]["3"] == "Longstrider Pass without Trace"
    except AssertionError:
        failed = True
    assert failed, "the negative control did not fail; the cell separation is not being checked"
    print("  ok  negative control: both pins fail when given the pre-repair value")

    print("PASS test_acceptance_species_traits")


if __name__ == "__main__":
    main()
