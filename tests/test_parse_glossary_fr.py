"""Calibration checks for the French Rules Glossary parser.

Each scenario reproduces a shape actually found in the pinned FR PDF while
calibrating parse_glossary_fr.py, plus one negative control proving the
suite can fail.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_glossary_fr  # noqa: E402


def page(*blocks):
    return extract.normalise("\n".join(blocks))


def wrap(*entry_blocks, suspect=()):
    pages = [page(
        "Glossaire de règles\n\nConventions relatives\nau glossaire\n\n"
        "Sous-types entre crochets.\n\nBM\nbonus de maîtrise\n\n"
        "Définitions des règles\n\nCi-après, les définitions des diverses règles.\n\n"
    )] + list(entry_blocks) + [page("Boîte à outils\nludique\n\n")]
    return parse_glossary_fr.parse(pages, suspect)


def main():
    # -- ordinary entry, no tag -----------------------------------------
    entries, anomalies, conflicts = wrap(page(
        "Abris\nL’abri fournit un degré de protection à la cible située "
        "derrière. Il existe trois niveaux d’abri qui octroient chacun "
        "un bénéfice distinct aux cibles abritées.\n",
    ))
    assert len(entries) == 1 and not anomalies, (entries, anomalies)
    assert entries[0]["name"] == "Abris" and entries[0]["tag"] is None
    print("  ok  ordinary untagged entry")

    # -- French sentence-case name (NOT English title case) --------------
    entries, anomalies, conflicts = wrap(page(
        "Jet de sauvegarde\nUn jet de sauvegarde, ou JS en abrégé, représente "
        "une tentative d’échapper à une menace ou d’y résister. Vous "
        "n’effectuez en temps normal un jet de sauvegarde que lorsqu’une "
        "règle vous y contraint.\n",
    ))
    assert len(entries) == 1 and not anomalies, (entries, anomalies)
    assert entries[0]["name"] == "Jet de sauvegarde", entries[0]["name"]
    print("  ok  sentence-case French name (only first word capitalised) is accepted")

    # -- accented bracketed tag: "État", not EN's plain-ASCII charset ----
    entries, anomalies, conflicts = wrap(page(
        "Agrippé [État]\nTant que vous avez l’état Agrippé, vous subissez "
        "les effets suivants. Votre Vitesse est de 0 et ne peut pas "
        "augmenter du tout tant que cet état perdure.\n",
    ))
    assert len(entries) == 1 and not anomalies, (entries, anomalies)
    e = entries[0]
    assert e["name"] == "Agrippé" and e["tag"] == "etat", e
    print("  ok  accented bracketed tag ([État]) is read")

    # -- accent-aware alphabetical order: 'À terre' must not poison it ---
    # against every later unaccented entry (raw code-point order puts 'À'
    # after 'z', which is not French dictionary order).
    entries, anomalies, conflicts = wrap(
        page(
            "À terre\nTant que vous avez l’état À terre, vous subissez les "
            "effets suivants pendant toute la durée de cet état précis.\n",
        ),
        page(
            "Abris\nL’abri fournit un degré de protection à la cible "
            "située derrière lui pendant tout le temps où elle y reste.\n",
        ),
    )
    names = [e["name"] for e in entries]
    assert names == ["À terre", "Abris"], names
    print("  ok  accent-insensitive sort key: 'À terre' does not block 'Abris'")

    # -- a mid-paragraph sentence fragment is not mistaken for a head ----
    entries, anomalies, conflicts = wrap(page(
        "Repos long\nLes personnages profitent des bienfaits d’un Repos "
        "long en dormant, se relaxant ou pratiquant une activité légère "
        "pendant au moins 8 heures d’affilée.\n"
        "\t Si vous vous êtes reposé au moins 1 heure avant l’interruption, "
        "vous recevez les bénéfices d’un Repos court.\n",
        "Reptation\nLorsque vous rampez, toute distance parcourue vous "
        "coûte le double de déplacement pendant tout le mouvement "
        "considéré.\n",
    ))
    names = [e["name"] for e in entries]
    assert "Reptation" in names, names
    assert not any(n.startswith("Si vous") for n in names), names
    print("  ok  a 'Si'/'Vous'-led sentence fragment is not mistaken for an entry name")

    # -- an entry name with no body text is excluded, not borrowed -------
    entries, anomalies, conflicts = wrap(
        page("Entrée cassée\n"),
        page(
            "Entrée suivante\nUne description bien réelle et suffisamment "
            "longue pour franchir le seuil de mots exigé par ce test.\n",
        ),
    )
    names = [e["name"] for e in entries]
    assert "Entrée suivante" in names, names
    assert "Entrée cassée" not in names, names
    print("  ok  a name line with no real body text is excluded")

    # -- NEGATIVE CONTROL --------------------------------------------------
    entries, anomalies, conflicts = wrap(page(
        "Alignement\nL’alignement d’une créature illustre globalement ses "
        "valeurs éthiques et ses idéaux personnels envers le monde entier.\n",
    ))
    assert len(entries) == 1 and not anomalies and not conflicts, (entries, anomalies)
    print("  ok  negative control: an ordinary complete entry is not wrongly excluded")

    print("PASS test_parse_glossary_fr")


if __name__ == "__main__":
    main()
