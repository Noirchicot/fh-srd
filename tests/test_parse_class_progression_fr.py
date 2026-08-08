"""Calibration checks for the French class level-progression parser.

The row mechanics are the English module's and are tested there. What is
tested here is everything that decides WHICH table belongs to WHICH class --
because French orders its class chapters by its own alphabet, and pairing a
table with a class by position alone would hand the Ensorceleur's spell slots
to the Guerrier in a file that looks complete. Plus the two French cell
shapes English gives no reason to expect: metres with a decimal comma, and
header labels the source hyphenates mid-word.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_class_progression_fr as prog  # noqa: E402
from parse_class_progression_en import needles as en_needles, split_row  # noqa: E402


def rows_for(cls):
    """Twenty rows matching the declared column count for `cls`."""
    resources, slots = prog.TABLES[cls]
    out = []
    for level in range(1, 21):
        cells = ["%d" % level, "+%d" % (2 + (level - 1) // 4), "Aptitude"]
        cells += ["1"] * len(resources)
        cells += ["2" if n == 1 else "—" for n in range(1, slots + 1)]
        out.append("\n".join(cells))
    return "\n\n".join(out)


def class_page(cls, anchor=True, labels=True):
    parts = []
    if anchor:
        parts.append(prog.needles(cls)[0])
    if labels:
        resources, slots = prog.TABLES[cls]
        parts.append("\n".join(resources))
        if slots:
            parts.append(prog.SLOT_BAND_LABEL)
    parts.append(rows_for(cls))
    return extract.normalise("\n\n".join(parts))


def document(classes=None, **kwargs):
    classes = classes or prog.CLASSES
    return [class_page(cls, **kwargs) for cls in classes]


def main():
    # -- the whole document, in French chapter order ------------------------
    found, anomalies, conflicts = prog.parse(document())
    assert not anomalies and not conflicts, (anomalies, conflicts)
    assert len(found) == 12, len(found)
    assert {r["name"] for r in found} == set(prog.CLASSES)
    print("  ok  les douze tables françaises sont lues et attribuées")

    # -- the class order is French's own, not English's ---------------------
    assert prog.CLASSES.index("Ensorceleur") == 4, prog.CLASSES
    assert prog.CLASSES.index("Roublard") == 11
    ensorceleur = [r for r in found if r["name"] == "Ensorceleur"][0]
    assert ensorceleur["spell_slot_levels"] == 9
    assert ensorceleur["class"] == "srd:class:fr:ensorceleur"
    guerrier = [r for r in found if r["name"] == "Guerrier"][0]
    assert guerrier["spell_slot_levels"] == 0
    print("  ok  Ensorceleur est cinquième et reste un lanceur complet, Guerrier non")

    # -- THE REFUSAL THAT MATTERS: a page with no class anchor is NOT -------
    # attributed by position. Drop the Ensorceleur's anchor and the parser
    # must refuse that one table and say so, not shift every later table by
    # one class.
    pages = document()
    pages[4] = class_page("Ensorceleur", anchor=False)
    found, anomalies, _ = prog.parse(pages)
    assert len(found) == 11, [r["name"] for r in found]
    assert any("Ensorceleur" in a["detail"] and "refusing to attribute" in a["detail"]
               for a in anomalies), anomalies
    assert "Ensorceleur" not in {r["name"] for r in found}
    assert {r["name"] for r in found} == set(prog.CLASSES) - {"Ensorceleur"}
    print("  ok  une table sans ancre de classe est refusée, pas attribuée de proche en proche")

    # -- a declared column that is not on the page is a refusal too ---------
    pages = document()
    pages[7] = class_page("Moine", labels=False)
    found, anomalies, _ = prog.parse(pages)
    assert any("Moine" in a["detail"] and "do not appear" in a["detail"]
               for a in anomalies), anomalies
    assert "Moine" not in {r["name"] for r in found}
    print("  ok  une colonne déclarée absente de la page fait refuser la table")

    # -- FRENCH CELL SHAPE 1: metres with a decimal comma -------------------
    assert prog.CELL_RE.match("+4,50 m") and prog.CELL_RE.match("+3 m")
    assert not prog.CELL_RE.match("+10 ft.")
    split, why = split_row(
        ["6", "+3", "Aptitude de sous-classe, Frappes renforcées", "1d8", "6",
         "+4,50 m"], 6, prog.CELL_RE)
    assert why is None, why
    assert split[3] == ["1d8", "6", "+4,50 m"], split[3]
    print("  ok  « +4,50 m » est une cellule valide ; « +10 ft. » ne l'est pas ici")

    # -- FRENCH CELL SHAPE 2: header labels hyphenated mid-word -------------
    # The Occultiste prints its own columns as "Manifes-/tations/occultes" and
    # "Niveau des/emplace-/ments". The label check runs on the DEHYPHENATED
    # text, so they are found; on the raw page they are not.
    hyphenated = extract.normalise(
        prog.needles("Occultiste")[0] + "\n\nManifes-\ntations\noccultes\n"
        "Sorts\nmineurs\nSorts\npréparés\nEmpla-\ncements\nde sort\n"
        "Niveau des\nemplace-\nments\n\n" + rows_for("Occultiste")
    )
    assert "Niveau des emplacements" not in " ".join(hyphenated.split())
    pages = document()
    pages[8] = hyphenated
    found, anomalies, _ = prog.parse(pages)
    assert not anomalies, anomalies
    occultiste = [r for r in found if r["name"] == "Occultiste"][0]
    assert [c["key"] for c in occultiste["resource_columns"]][-1] == (
        "niveau_des_emplacements")
    print("  ok  un intitulé de colonne coupé par un tiret est reconnu après recollage")

    # -- NEGATIVE CONTROL 1: eleven tables is not twelve --------------------
    found, anomalies, _ = prog.parse(document(prog.CLASSES[:-1]))
    assert not found and anomalies
    assert "found 11 level-progression tables, expected 12" in anomalies[0]["detail"]
    print("  ok  contrôle négatif : onze tables au lieu de douze arrête tout, bruyamment")

    # -- NEGATIVE CONTROL 2: the English anchors must not match French pages
    for cls in prog.CLASSES:
        page = class_page(cls)
        assert not any(n in page for n in en_needles("Wizard")), cls
    print("  ok  contrôle négatif : les ancres anglaises ne mordent sur aucune page française")

    print("PASS test_parse_class_progression_fr")


if __name__ == "__main__":
    main()
