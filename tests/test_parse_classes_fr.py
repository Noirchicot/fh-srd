"""Calibration checks for the French class parser."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402
import parse_classes_fr  # noqa: E402


def page(*blocks):
    raw = "\n".join(blocks)
    return extract.normalise(raw)


def parse_one(*pages, suspect=()):
    classes, anomalies, conflicts = parse_classes_fr.parse(list(pages), suspect)
    # These fixtures deliberately include only one or two of the twelve real
    # SRD classes -- the parser correctly notices the others have no
    # "Traits de base" anchor anywhere in the chapter and reports it (a real
    # safety check, not something any scenario below is testing for), so it
    # is filtered out here rather than asserted on in every scenario -- same
    # discipline as the EN class parser's own test suite.
    real = [a for a in anomalies if "anchor in the Classes chapter" not in a["detail"]]
    return classes, real, conflicts


def _class_block(name, traits_needle, subclass_needle, spell_list=None, tools=False):
    tools_block = "Maîtrises\nd’outils\nOutils de voleur\n\n" if tools else ""
    return page(
        "Classes\n\n%s\n\n%s\n\n"
        "Caractéristique\nprincipale\nDextérité\n\n"
        "Dé de vie\nd8 par niveau de %s\n\n"
        "Maîtrise des jets\nde sauvegarde\nDextérité et Intelligence\n\n"
        "Maîtrises de\ncompétence\n4 au choix\n\n"
        "Maîtrises d’arme\nArmes courantes\n\n"
        "%s"
        "Formation aux\narmures\nAucune\n\n"
        "Équipement\nde départ\nUne dague et 10 po\n\n"
        % (name, traits_needle, name, tools_block),
        "Devenir %s…\n\nEn tant que personnage de niveau 1\n"
        "• Recevez tous les traits de l’encadré.\n\n"
        "Aptitudes de classe du %s\n\n"
        "Niveau 1 : Premier don\nDescription du premier don.\n\n"
        "Niveau 2 : Second don\nDescription du second don.\n\n"
        % (name, name),
        ("%s\n" % spell_list if spell_list else ""),
        "%s\nVoie test\n\n"
        "Une voie de test pour la calibration.\n\n"
        "Niveau 3 : Aptitude de sous-classe\n"
        "Description de l’aptitude de sous-classe.\n\n"
        % subclass_needle,
    )


def main():
    # -- ordinary class, no elision, no tool proficiencies ------------------
    pages = [_class_block("Roublard", "Traits de base du Roublard",
                           "Sous-classe de Roublard :"),
             page("Historiques de personnage\n")]
    classes, anomalies, conflicts = parse_one(*pages)
    assert len(classes) == 1 and not anomalies, (classes, anomalies)
    c = classes[0]
    assert c["hit_point_die"] == "d8 par niveau de Roublard"
    assert c["saving_throw_proficiencies"] == ["Dextérité", "Intelligence"]
    assert c["tool_proficiencies"] is None
    assert len(c["features"]) == 2
    assert c["subclass"]["name"] == "Voie test"
    assert len(c["subclass"]["features"]) == 1
    print("  ok  ordinary class: no elision, saving throws split on 'et'")

    # -- elided class name: "de l'" for Traits, "d'" for Sous-classe --------
    pages = [_class_block("Ensorceleur", "Traits de base de l’Ensorceleur",
                           "Sous-classe d’Ensorceleur :"),
             page("Historiques de personnage\n")]
    classes, anomalies, conflicts = parse_one(*pages)
    assert len(classes) == 1 and not anomalies, (classes, anomalies)
    print("  ok  elided class name: 'de l'' for Traits de base, 'd'' for Sous-classe")

    # -- tool proficiencies (optional field) present -------------------------
    pages = [_class_block("Barde", "Traits de base du Barde",
                           "Sous-classe de Barde :", tools=True),
             page("Historiques de personnage\n")]
    classes, anomalies, conflicts = parse_one(*pages)
    assert len(classes) == 1 and not anomalies, (classes, anomalies)
    assert classes[0]["tool_proficiencies"] == "Outils de voleur"
    print("  ok  optional tool proficiencies field, present")

    # -- a class missing its Traits de base anchor is excluded whole --------
    pages = [page("Classes\n\nAptitudes de classe du Barde\n\nNiveau 1 : Rien\nRien.\n\n"),
             page("Historiques de personnage\n")]
    classes, anomalies, conflicts = parse_classes_fr.parse(pages, ())
    assert not classes
    assert any("anchor in the Classes chapter" in a["detail"] for a in anomalies), anomalies
    print("  ok  a class with no 'Traits de base' anchor is excluded, not guessed")

    # -- NEGATIVE CONTROL -----------------------------------------------------
    pages = [_class_block("Magicien", "Traits de base du Magicien",
                           "Sous-classe de Magicien :"),
             page("Historiques de personnage\n")]
    classes, anomalies, conflicts = parse_one(*pages)
    assert len(classes) == 1 and not anomalies and not conflicts, (classes, anomalies)
    print("  ok  negative control: an ordinary complete class is not wrongly excluded")

    print("PASS test_parse_classes_fr")


if __name__ == "__main__":
    main()
