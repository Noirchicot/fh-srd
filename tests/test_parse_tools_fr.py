"""Calibration checks for the French tools parser."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_tools_fr  # noqa: E402


def page(*blocks):
    return extract.normalise("\n".join(blocks))


def wrap(*entry_blocks, suspect=()):
    pages = [page("Outils\n\nUn outil vous aide à effectuer certains tests.\n")] \
        + list(entry_blocks) + [page("Matériel d’aventurier\n\nLe tableau.\n")]
    return parse_tools_fr.parse(pages, suspect)


def main():
    # -- ordinary tool, all five fields --------------------------------------
    entries, anomalies, conflicts = wrap(page(
        "Outils de potier (10 po)\nCaractéristique : Intelligence\nPoids : 1,5 kg\n"
        "Utilisation : déterminer ce qu’a contenu un objet en\ncéramique (DD 15)\n"
        "Artisanat : cruche, lampe\n",
    ))
    assert len(entries) == 1 and not anomalies, (entries, anomalies)
    t = entries[0]
    assert t["cost"] == "10 po" and t["ability"] == "Intelligence"
    assert t["craft"] == "cruche, lampe" and t["variants"] is None
    print("  ok  ordinary tool: all fields, no variants")

    # -- optional Variantes field, variable cost -----------------------------
    entries, anomalies, conflicts = wrap(page(
        "Boîte de jeux (variable)\nCaractéristique : Sagesse\nPoids : —\n"
        "Utilisation : déterminer si quelqu’un triche (DD 10)\n"
        "Variantes : cartes à jouer (5 pa), dés (1 pa)\n",
    ))
    assert len(entries) == 1 and not anomalies, (entries, anomalies)
    t = entries[0]
    assert t["cost"] == "variable" and t["craft"] is None
    assert t["variants"] == "cartes à jouer (5 pa), dés (1 pa)"
    print("  ok  variable cost, optional Variantes field present, no Artisanat")

    # -- a 'Nom (Coût)' shaped line NOT followed by Caractéristique is not --
    # -- mistaken for a tool head (the same guard EN's parser relies on) ----
    entries, anomalies, conflicts = wrap(page(
        "Un objet quelconque (10 po)\nCeci n’est pas un outil, juste une "
        "ligne qui ressemble à un en-tête.\n",
        "Outils de voleur (25 po)\nCaractéristique : Dextérité\nPoids : 0,5 kg\n"
        "Utilisation : crocheter une serrure (DD 15)\n",
    ))
    names = [e["name"] for e in entries]
    assert names == ["Outils de voleur"], names
    print("  ok  a 'Name (Cost)' line not followed by 'Caractéristique' is not a false head")

    # -- NEGATIVE CONTROL ------------------------------------------------------
    entries, anomalies, conflicts = wrap(page(
        "Instruments de navigateur (25 po)\nCaractéristique : Sagesse\n"
        "Poids : 1 kg\nUtilisation : tracer un cap (DD 10)\n",
    ))
    assert len(entries) == 1 and not anomalies and not conflicts, (entries, anomalies)
    print("  ok  negative control: an ordinary complete tool is not wrongly excluded")

    print("PASS test_parse_tools_fr")


if __name__ == "__main__":
    main()
