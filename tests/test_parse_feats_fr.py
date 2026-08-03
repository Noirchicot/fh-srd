"""Calibration checks for the French feat parser."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_feats_fr  # noqa: E402


def page(*blocks):
    raw = "\n".join(blocks)
    return extract.normalise(raw)


def parse_one(*pages, suspect=()):
    return parse_feats_fr.parse(list(pages), suspect)


def main():
    intro = page("Dons\n\nDescription des dons\nLes dons sont organisés par catégorie.\n")

    # -- origin feat, no prerequisite ---------------------------------------
    pages = [intro, page(
        "Doué\nDon d’origines\n",
        "Vous recevez la maîtrise de trois compétences ou outils au choix.\n",
    )]
    feats, anomalies, conflicts = parse_one(*pages)
    assert len(feats) == 1 and not anomalies, (feats, anomalies)
    assert feats[0]["category"] == "origin" and feats[0]["prerequisite"] is None
    print("  ok  origin feat head, no prerequisite clause")

    # -- general feat with a wrapped prerequisite clause --------------------
    pages = [intro, page(
        "Empoigneur\nDon général (prérequis : niveau 4 ou supérieur, Force\n"
        "ou Dextérité 13 ou plus)\n",
        "Vous recevez les bénéfices suivants.\n",
    )]
    feats, anomalies, conflicts = parse_one(*pages)
    assert len(feats) == 1 and not anomalies, (feats, anomalies)
    f = feats[0]
    assert f["category"] == "general"
    assert f["prerequisite"] == "niveau 4 ou supérieur, Force ou Dextérité 13 ou plus", f["prerequisite"]
    print("  ok  general feat, wrapped prerequisite clause collected across the line break")

    # -- fighting style and epic boon categories -----------------------------
    pages = [intro, page(
        "Archerie\nDon de Style de combat (prérequis : aptitude Style\n"
        "de combat)\n",
        "Vous recevez un bonus de +2 aux jets d’attaque à distance.\n",
        "Faveur du destin\nDon de faveur épique (prérequis : niveau 19 ou\n"
        "supérieur)\n",
        "Vous recevez les bénéfices suivants.\n",
    )]
    feats, anomalies, conflicts = parse_one(*pages)
    names = {f["name"]: f for f in feats}
    assert len(feats) == 2 and not anomalies, (feats, anomalies)
    assert names["Archerie"]["category"] == "fighting-style"
    assert names["Faveur du destin"]["category"] == "epic-boon"
    print("  ok  Style de combat and faveur épique categories")

    # -- a category line with no description text is excluded --------------
    pages = [intro, page(
        "Don cassé\nDon général (prérequis : niveau 4 ou supérieur)\n",
        "Don suivant\nDon d’origines\n",
        "Une description bien réelle.\n",
    )]
    feats, anomalies, conflicts = parse_one(*pages)
    names = [f["name"] for f in feats]
    assert "Don suivant" in names and "Don cassé" not in names, names
    print("  ok  a category line with no description text is excluded, not borrowed")

    # -- NEGATIVE CONTROL ----------------------------------------------------
    pages = [intro, page(
        "Don complet\nDon d’origines\n",
        "Un effet quelconque.\n",
    )]
    feats, anomalies, conflicts = parse_one(*pages)
    assert len(feats) == 1 and not anomalies and not conflicts, (feats, anomalies)
    print("  ok  negative control: an ordinary complete feat is not wrongly excluded")

    print("PASS test_parse_feats_fr")


if __name__ == "__main__":
    main()
