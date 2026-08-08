"""Calibration checks for the French species parser."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_species_fr  # noqa: E402


def page(*blocks):
    raw = "\n".join(blocks)
    return extract.normalise(raw)


def parse_one(*pages, suspect=(), emphasis=(), tables=()):
    """Pages, plus the page geometry the parser now asks `build.py` for.

    REWRITTEN 2026-08-08: the parser takes a third argument. A trait name is
    read from the bold italic the typesetter sets it in, which matters far more
    in French than in English — the French Elf entry arrives as ONE paragraph
    with no break between its five traits, so there is no paragraph shape to
    split on (see `species_structure.py`). Each scenario therefore says which
    phrases its page prints, and each fixture below gained one real trait line
    so that it has something to name.
    """
    pages = list(pages)
    layout = [{"emphasis": [], "tables": []} for _ in pages]
    layout[-1] = {"emphasis": list(emphasis), "tables": list(tables)}
    return parse_species_fr.parse(pages, suspect, layout)


def main():
    intro = page("Description des espèces\n\n")

    # -- ordinary species, wrapped size clause -------------------------------
    pages = [intro, page(
        "Elfe\nType de créature : Humanoïde\nCatégorie de taille : M (moyenne, entre 1,50 m et\n"
        "1,80 m)\nVitesse : 9 m\n",
        "En tant qu’elfe, vous disposez des traits spéciaux suivants. "
        "Transe. Vous vous passez de sommeil.\n",
        "Gnome\nType de créature : Humanoïde\nCatégorie de taille : P (petite)\n"
        "Vitesse : 9 m\n",
        "En tant que gnome, vous disposez des traits spéciaux suivants. "
        "Ruse gnome. Vous avez l’Avantage.\n",
    )]
    sp, anomalies, conflicts = parse_one(*pages, emphasis=["Transe.", "Ruse gnome."])
    assert len(sp) == 2 and not anomalies, (sp, anomalies)
    elfe = sp[0]
    assert elfe["name"] == "Elfe" and elfe["creature_type"] == "Humanoïde"
    assert elfe["size"] == "M (moyenne, entre 1,50 m et 1,80 m)", elfe["size"]
    # THE TRAP: the head IS the name here -- no next-entry-name trim, or the
    # last sentence of Elfe's description would be silently cut.
    assert elfe["description"].endswith("Vous vous passez de sommeil."), elfe["description"]
    # French runs its traits together inside one paragraph, so this is the
    # shape that has no paragraph break to split on and needs the font.
    assert elfe["traits"] == [{
        "id": "transe", "name": "Transe", "text": "Vous vous passez de sommeil."}], elfe["traits"]
    gnome = sp[1]
    assert [t["name"] for t in gnome["traits"]] == ["Ruse gnome"], gnome["traits"]
    print("  ok  ordinary species, wrapped size clause, no next-name trim applied")

    # -- a name mentioned in passing (no 'Type de créature' right after) ---
    # must not be mistaken for a real head.
    pages = [intro, page(
        "...comme détaillé pour l’espèce Orc.\nOrc\nType de créature : Humanoïde\n"
        "Catégorie de taille : M\nVitesse : 9 m\n",
        "En tant qu’orc, vous disposez des traits spéciaux suivants. "
        "Acharnement. Vous tombez à 1 point de vie.\n",
    )]
    sp, anomalies, conflicts = parse_one(*pages, emphasis=["Acharnement."])
    assert len(sp) == 1 and sp[0]["name"] == "Orc", sp
    print("  ok  a bare name mentioned in passing is not mistaken for a head")

    # -- missing field is an exclusion, not borrowed ------------------------
    pages = [intro, page(
        "Nain\nType de créature : Humanoïde\nVitesse : 9 m\n",  # no Catégorie de taille
        "En tant que nain, vous disposez de traits spéciaux. "
        "Résistance naine. Vous avez l’Avantage.\n",
        "Orc\nType de créature : Humanoïde\nCatégorie de taille : M\nVitesse : 9 m\n",
        "En tant qu’orc, vous disposez de traits spéciaux. "
        "Acharnement. Vous tombez à 1 point de vie.\n",
    )]
    sp, anomalies, conflicts = parse_one(*pages, emphasis=["Acharnement."])
    names = [s["name"] for s in sp]
    assert "Orc" in names and "Nain" not in names, names
    print("  ok  a missing field is an exclusion, not borrowed from the next entry")

    # -- NEGATIVE CONTROL ----------------------------------------------------
    pages = [intro, page(
        "Humain\nType de créature : Humanoïde\nCatégorie de taille : M ou P\n"
        "Vitesse : 9 m\n",
        "En tant qu’humain, vous disposez de traits spéciaux. "
        "Polyvalent. Vous recevez un don d’Origine.\n",
    )]
    sp, anomalies, conflicts = parse_one(*pages, emphasis=["Polyvalent."])
    assert len(sp) == 1 and not anomalies and not conflicts, (sp, anomalies)
    print("  ok  negative control: an ordinary complete species is not wrongly excluded")

    print("PASS test_parse_species_fr")


if __name__ == "__main__":
    main()
