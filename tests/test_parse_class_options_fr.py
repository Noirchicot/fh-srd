"""Calibration checks for the French class-option parser.

🔴 THE TRAP THIS FILE EXISTS FOR, and it is measured on FR p.71, not imagined:

    Lame dévorante
    Prérequis : Niveau d’Occultiste 12+, manifestation
    Lame assoiffée                       <- character-for-character the head
                                            of the entry seven lines above

The prerequisite WRAPS, and its second line is exactly the name of another
entry printed on the same page. A parser that took "this line is set in the
entry-head face" as sufficient would read a twenty-ninth invocation there,
overshoot the count, and — if the count guard were absent — cut `Lame
dévorante`'s body in half. The group rule is what refuses it.

🔴 AND THE OTHER ONE: **French does not say "invocation".** It says
*Manifestation occulte*. Every anchor in this test is the French word, and the
last assertion checks that the string "invocation" appears nowhere in the
French records — because a search for it is exactly how one concludes, wrongly,
that this data is not in the book.

The bodies below are stubs; the twenty-eight and ten names, and their
prerequisites and costs, are the real ones read off the pinned PDF.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import class_options  # noqa: E402
import extract  # noqa: E402
import parse_class_options_fr as parser  # noqa: E402

# (name, prerequisite or None), alphabetical in FRENCH — which is not the
# English order: Décharge déchirante is 3rd here, Agonizing Blast is 1st there.
MANIFESTATIONS = [
    ("Armure d’ombres", None),
    ("Buveuse de vie", "Niveau d’Occultiste 9+, manifestation Pacte\nde la lame"),
    ("Décharge déchirante", "Niveau d’Occultiste 2+, un sort mineur\nd’Occultiste infligeant des dégâts"),
    ("Décharge répulsive", "Niveau d’Occultiste 2+, un sort mineur\nd’Occultiste infligeant des dégâts via un jet d’attaque"),
    ("Engagement du maître des chaînes", "Niveau d’Occultiste 5+, manifestation Pacte\nde la chaîne"),
    ("Enseignement des Premiers-Nés", "Niveau d’Occultiste 2+"),
    ("Esprit occulte", None),
    ("Frappe occulte", "Niveau d’Occultiste 5+, manifestation Pacte\nde la lame"),
    ("Lame assoiffée", "Niveau d’Occultiste 5+, manifestation Pacte\nde la lame"),
    # ⬇ THE TRAP: the wrap lands on a line that IS another entry's head.
    ("Lame dévorante", "Niveau d’Occultiste 12+, manifestation\nLame assoiffée"),
    ("Lance occulte", "Niveau d’Occultiste 2+, un sort mineur\nd’Occultiste infligeant des dégâts"),
    ("Maître des formes", "Niveau d’Occultiste 5+"),
    ("Maître des ombres", "Niveau d’Occultiste 5+"),
    ("Mille visages", "Niveau d’Occultiste 2+"),
    ("Murmures de la tombe", "Niveau d’Occultiste 7+"),
    ("Pacte de la chaîne", None),
    ("Pacte de la lame", None),
    ("Pacte du grimoire", None),
    ("Pas aérien", "Niveau d’Occultiste 5+"),
    ("Perception transférée", "Niveau d’Occultiste 5+"),
    ("Présent des profondeurs", "Niveau d’Occultiste 5+"),
    ("Présent des sauveurs", "Niveau d’Occultiste 9+, manifestation Pacte\ndu grimoire"),
    ("Royaumes lointains", "Niveau d’Occultiste 9+"),
    ("Saut d’outre-monde", "Niveau d’Occultiste 2+"),
    ("Vigueur fiélonne", "Niveau d’Occultiste 2+"),
    ("Vision du diable", "Niveau d’Occultiste 2+"),
    ("Vision sorcière", "Niveau d’Occultiste 15+"),
    ("Visions embrumées", "Niveau d’Occultiste 2+"),
]

METAMAGIE = [
    ("Sort accéléré", "2 points de Sorcellerie"),
    ("Sort ample", "1 point de Sorcellerie"),
    ("Sort chercheur", "1 point de Sorcellerie"),
    ("Sort étendu", "1 point de Sorcellerie"),
    ("Sort intensifié", "2 points de Sorcellerie"),
    ("Sort jumeau", "1 point de Sorcellerie"),
    ("Sort prévenant", "1 point de Sorcellerie"),
    ("Sort renforcé", "1 point de Sorcellerie"),
    ("Sort subtil", "1 point de Sorcellerie"),
    ("Sort transmuté", "1 point de Sorcellerie"),
]


def entry(name, label, clause, body):
    out = [name]
    if clause:
        parts = clause.split("\n")
        out.append("%s %s" % (label, parts[0]))
        out.extend(parts[1:])
    out.append("")
    out.append(body)
    return "\n".join(out)


def pages_and_layout(manifestations=MANIFESTATIONS, metamagie=METAMAGIE):
    meta = [
        "Niveau 20 : Apothéose arcanique",
        "Tant que votre aptitude Sorcellerie innée est active,",
        "vous pouvez recourir à une option de Métamagie.",
        "Options de Métamagie",
        "",
        "Les options ci-après sont disponibles pour votre",
        "aptitude Métamagie. Elles sont présentées par ordre",
        "alphabétique.",
        "",
    ]
    for name, cost in metamagie:
        meta.append(entry(name, "Coût :", cost,
                          "Corps de %s, qui est de la prose." % name))
        meta.append("")
    meta.append("Liste des sorts d’Ensorceleur")

    inv = [
        "Niveau 20 : Maître de l’occulte",
        "Lorsque vous utilisez votre aptitude Rouerie magique,",
        "vous récupérez tous les emplacements de sort dépensés.",
        "Options de Manifestation occulte",
        "",
        "Les options de Manifestation occulte sont listées par",
        "ordre alphabétique.",
        "",
    ]
    for name, prereq in manifestations:
        inv.append(entry(name, "Prérequis :", prereq,
                         "Corps de %s, qui est de la prose." % name))
        inv.append("")
    inv.append("Liste des sorts d’Occultiste")

    names = [n for n, _ in manifestations] + [n for n, _ in metamagie]
    # Cut mid-section so a head opens a page with no blank line before it.
    lines = "\n".join(inv).split("\n")
    cut = lines.index("Pacte de la chaîne")
    raw = ["\n".join(meta), "\n".join(lines[:cut]), "\n".join(lines[cut:])]

    pages = [extract.normalise(p) for p in raw]
    layout = [{"tables": [], "emphasis": [],
               "heads": [n for n in names if n in page.split("\n")]}
              for page in pages]
    return pages, layout


def main():
    pages, layout = pages_and_layout()
    records, anomalies, conflicts = parser.parse(pages, (), layout)
    assert not anomalies, anomalies
    assert not conflicts, conflicts

    inv = [r for r in records if r["category"] == "eldritch-invocation"]
    meta = [r for r in records if r["category"] == "metamagic"]
    assert len(inv) == 28, len(inv)
    assert len(meta) == 10, len(meta)
    print("  ok  28 Manifestations occultes and 10 Métamagies — the same two "
          "lists as English, read from French anchors")

    got = {r["name"]: r for r in records}
    assert set(got) == set(n for n, _ in MANIFESTATIONS) | set(n for n, _ in METAMAGIE)
    print("  ok  every one of the 38 French names comes back, and nothing else")

    # -- 🔴 THE WRAP THAT LOOKS LIKE A HEAD --------------------------------
    assert got["Lame dévorante"]["prerequisite"] == (
        "Niveau d’Occultiste 12+, manifestation Lame assoiffée"
    ), got["Lame dévorante"]["prerequisite"]
    assert got["Lame assoiffée"]["prerequisite"] == (
        "Niveau d’Occultiste 5+, manifestation Pacte de la lame"
    ), got["Lame assoiffée"]["prerequisite"]
    assert got["Lame dévorante"]["description"] == \
        "Corps de Lame dévorante, qui est de la prose."
    print("  ok  a prerequisite wrapping onto a line that IS another entry's "
          "head is read as the clause it is — 28, not 29")

    # -- the five printed as name-then-prose -------------------------------
    bare = sorted(r["name"] for r in inv if r["prerequisite"] is None)
    assert bare == ["Armure d’ombres", "Esprit occulte", "Pacte de la chaîne",
                    "Pacte de la lame", "Pacte du grimoire"], bare
    print("  ok  the 5 manifestations with no prerequisite line are read: %s"
          % ", ".join(bare))

    # -- ⛔ the asymmetry --------------------------------------------------
    assert all("cost" not in r for r in inv)
    assert all(r.get("cost") for r in meta)
    assert got["Sort accéléré"]["cost"] == "2 points de Sorcellerie"
    print("  ok  « Coût : » is read for the 10 Métamagies and no manifestation "
          "carries the key at all")

    # -- a head opening a page ---------------------------------------------
    assert got["Pacte de la chaîne"]["page"] == 3, got["Pacte de la chaîne"]
    print("  ok  an entry whose head is the first line of a page is read")

    # -- 🔴 the word that is NOT in the French book -------------------------
    haystack = " ".join(
        "%s %s %s" % (r["name"], r.get("prerequisite") or "", r["description"])
        for r in records
    ).lower()
    assert "invocation" not in haystack, "the French SRD does not say it"
    assert "manifestation" in haystack
    print("  ok  not one French record says « invocation » — which is why "
          "searching for that word finds nothing and proves nothing")

    # -- a list short of one entry REFUSES ---------------------------------
    short = [e for e in METAMAGIE if e[0] != "Sort transmuté"]
    pages2, layout2 = pages_and_layout(metamagie=short)
    try:
        parser.parse(pages2, (), layout2)
    except class_options.ListCountError as exc:
        assert "9 entries, expected 10" in str(exc), exc
        print("  ok  a list short of one entry REFUSES, naming the count")
    else:
        raise AssertionError("9 métamagies must stop the build, not export 9")

    print("PASS test_parse_class_options_fr")


if __name__ == "__main__":
    main()
