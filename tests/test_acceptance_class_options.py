"""The acceptance test for the genre this lot exists to add.

> Given the Warlock, a consumer can list the **twenty-eight** manifestations it
> chooses ten from; given the Sorcerer, the **ten** metamagic options it
> chooses six from — in either language, from the exports alone.

⭐ AND THE READING IS CHECKED BY SOMETHING THAT NEVER RAN THE PARSER.
`exports/` is produced by PyMuPDF. This file re-reads the same pinned PDFs
with **poppler's `pdftotext`**, which shares no code with MuPDF, and asserts
that every name, every prerequisite, every cost and the opening of every
description is printed on the page the record claims. A table checked against
itself agrees with itself; a hand-written mapping never contradicts a
hand-written mapping. This one is checked by a renderer that has never seen it.

⛔ WHAT THIS FILE DOES NOT DO, deliberately: it does not pair the two
languages. Each side is asserted against its OWN pages. `Décharge déchirante`
is 3rd in the French list where `Agonizing Blast` is 1st in the English one, so
anything comparing the two lists by position would be wrong in both directions
at once and would never contradict itself. That is `correspond.py`'s work, and
a person's signature.

Skips loudly when the PDFs are absent — they are gitignored, so a fresh clone
has not fetched them. A skip is visible in the output and is not a pass.
"""

import json
import os
import re
import subprocess
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(ROOT, "exports", "srd")

sys.path.insert(0, os.path.join(ROOT, "src"))

import french_layer  # noqa: E402
import sources  # noqa: E402

KIND = "class-option"
LANGS = ("en", "fr")

# The SRD's own counts, stated here so the test fails for the right reason
# rather than agreeing with whatever the export happens to hold.
EXPECTED = {"eldritch-invocation": 28, "metamagic": 10}

# How many of each list a character actually takes, from the class features
# ("you gain two Metamagic options … two more at level 10 and two more at 17";
# the Warlock table's Eldritch Invocations column tops out at 10). Not data
# this genre carries — written here so the numbers above have their point.
CHOSEN = {"eldritch-invocation": 10, "metamagic": 6}

# The eleven names the architect measured as absent from EVERY export, in both
# languages, before this lot ran. If any of them goes missing again, this is
# where it is caught.
MEASURED_ABSENT_EN = [
    "Agonizing Blast", "Devil’s Sight", "Eldritch Spear", "Repelling Blast",
    "Mask of Many Faces", "Careful Spell", "Distant Spell", "Empowered Spell",
    "Quickened Spell", "Subtle Spell", "Twinned Spell",
]

# ⛔ The Artificer is not at the SRD and its infusions are not invented here.
FORBIDDEN = ("infusion", "artificer", "artificier")


def flatten(text):
    """Strip ALL whitespace; every other character must still match exactly.

    The same rule `test_attribution_verbatim` uses, and for the same reason:
    line breaks belong to the page layout, not to the statement. Two renderers
    wrap differently and must still be held to the identical wording.
    """
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", text))


def load(lang):
    """⭐ Le PAYLOAD, avec ses `records` reconstitués si c'est un patch.

    Depuis le lot 104, `exports/srd/fr/*.json` porte `patches` et non `records`.
    Ce fichier lit l'en-tête (`count`) ET le contenu : on garde donc le payload
    entier et on lui remet ses records par `src/french_layer.py`.
    """
    with open(os.path.join(EXPORTS, lang, KIND + ".json"), encoding="utf-8") as fh:
        payload = json.load(fh)
    payload["records"] = french_layer.load(EXPORTS, lang, KIND)
    return payload


def witness_pages(path):
    """The pinned PDF, read by poppler. No MuPDF anywhere in this function."""
    out = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", path, "-"],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.split("\f")


def source_for(lang):
    for src in sources.load_lock()["sources"]:
        if src["lang"] == lang:
            return src
    raise AssertionError("no pinned source for lang=%r" % lang)


def main():
    try:
        subprocess.run(["pdftotext", "-v"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        print("SKIP test_acceptance_class_options — poppler's pdftotext is not "
              "on PATH, and the witness is the point of this test")
        return

    for lang in LANGS:
        payload = load(lang)
        records = payload["records"]

        by_category = {}
        for record in records:
            by_category.setdefault(record["data"]["category"], []).append(record)

        assert sorted(by_category) == sorted(EXPECTED), sorted(by_category)
        for category, expected in sorted(EXPECTED.items()):
            found = by_category[category]
            assert len(found) == expected, (lang, category, len(found))

        assert payload["count"] == sum(EXPECTED.values()), payload["count"]

        # ⛔ THE ASYMMETRY. A manifestation is free once taken; a metamagic is
        # paid for at every use. Only the second carries a cost — and the
        # first carries no `cost` key AT ALL, not an empty one, because an
        # empty field reads as "nobody extracted it yet".
        with_cost = [r for r in by_category["metamagic"] if r["data"].get("cost")]
        assert len(with_cost) == EXPECTED["metamagic"], len(with_cost)
        stray = [r["name"] for r in by_category["eldritch-invocation"]
                 if "cost" in r["data"]]
        assert not stray, "manifestations must carry no cost key: %s" % stray

        # A prerequisite is a FIELD, never a sentence left in the prose.
        with_prereq = [r for r in records if r["data"].get("prerequisite")]
        for record in records:
            assert record["data"]["description"], record["name"]
            assert "prerequisite" in record["data"], record["name"]
            assert not record["data"]["description"].lower().startswith(
                ("prerequisite", "prérequis", "cost:", "coût")), record["name"]

        # ⛔ nothing from a book this source does not contain.
        blob = json.dumps(records, ensure_ascii=False).lower()
        for word in FORBIDDEN:
            assert word not in blob, (
                "%s: %r appears in the class-option records. The Artificer is "
                "not in SRD 5.2.1 and its infusions must not be invented here."
                % (lang, word))

        if lang == "en":
            names = set(r["name"] for r in records)
            missing = [n for n in MEASURED_ABSENT_EN if n not in names]
            assert not missing, (
                "these were measured absent from every export before this lot "
                "and must not go missing again: %s" % ", ".join(missing))

        # ---- the independent witness ------------------------------------
        src = source_for(lang)
        pdf = os.path.join(ROOT, src["file"])
        if not os.path.exists(pdf):
            print("SKIP %s — source not fetched (python3 src/fetch_source.py "
                  "--pin %s)" % (src["id"], src["id"]))
            continue

        pages = witness_pages(pdf)
        checked = 0
        for record in records:
            page = int(record["source_locator"].lstrip("p."))
            # Poppler and MuPDF do not always agree on how many pages a PDF
            # has (the French file is 381 to MuPDF's 380), so the window is a
            # window and not a page. It is still narrow enough that a name
            # printed in a different chapter cannot satisfy it.
            window = flatten("\n".join(pages[max(0, page - 3):page + 2]))
            data = record["data"]
            for label, value in (
                ("name", record["name"]),
                ("prerequisite", data.get("prerequisite")),
                ("cost", data.get("cost")),
                ("description", data["description"][:120]),
            ):
                if not value:
                    continue
                assert flatten(value) in window, (
                    "%s: the %s of %r is not printed by poppler within pages "
                    "%d-%d of the pinned PDF — the two renderers disagree "
                    "about what the book says: %r"
                    % (lang, label, record["name"], page - 2, page + 2,
                       value[:80]))
                checked += 1

        print("  ok  %s: %d + %d entries (a class takes %d and %d of them); "
              "%d field(s) across %d records re-read by poppler and identical"
              % (lang, EXPECTED["eldritch-invocation"], EXPECTED["metamagic"],
                 CHOSEN["eldritch-invocation"], CHOSEN["metamagic"],
                 checked, len(records)))
        print("      %d of %d carry a prerequisite; %d carry a cost, and every "
              "one of those is a metamagic"
              % (len(with_prereq), len(records), len(with_cost)))

    print("PASS test_acceptance_class_options")


if __name__ == "__main__":
    main()
