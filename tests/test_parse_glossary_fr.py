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

    # ══ LOT 102 — LES DEUX FUITES, ÉPROUVÉES SUR UN CHAPITRE FABRIQUÉ ══════
    # Toutes deux passaient la forme du nom ET le plancher de prose : seul le
    # filet alphabétique les écartait, et il le faisait sans le dire.

    # -- ① LA CLEF DE TRI EFFAÇAIT UN SÉPARATEUR ----------------------------
    # Le livre imprime `Personnage non-joueur` AVANT `Personnage-joueur` :
    # l'espace passe avant le trait d'union. `canon.slugify` repliait les deux
    # sur `-`, et `j < n` inversait l'ordre du livre — la seconde entrée
    # ressemblait à un pas en arrière. Elle est imprimée p.197 avec sa
    # définition, et elle n'est jamais entrée dans l'export.
    entries, anomalies, conflicts = wrap(page(
        "Personnage non-joueur\nUn personnage non-joueur (PNJ en abrégé) est "
        "un monstre qui possède un nom et une personnalité distincte. Lire "
        "aussi « Monstre ».\n\n"
        "Personnage-joueur\nUn personnage-joueur (PJ en abrégé) est une "
        "personne contrôlée par un joueur. Lire aussi « Création de "
        "personnage ».\n",
    ))
    # ⚠️ On compare des ENSEMBLES : `parse` trie sa sortie par `canon.slugify`,
    # qui n'est PAS la clef du filet — ce tri-là ne range que l'export, il ne
    # décide de rien. Confondre les deux ferait échouer ce test sur une
    # question d'affichage.
    assert sorted(e["name"] for e in entries) == ["Personnage non-joueur", "Personnage-joueur"], entries
    assert not anomalies, anomalies
    # ⛔ ET LE TEXTE DE L'UNE N'EST PAS RESTÉ CHEZ L'AUTRE : une fuite ne
    # laissait pas un trou, elle laissait un record FAUX (famille du lot 86).
    pnj = next(e for e in entries if e["name"] == "Personnage non-joueur")
    assert "PJ en abrégé" not in pnj["description"], pnj["description"]
    print("  ok  lot 102 ① l'espace et le trait d'union sont des séparateurs DISTINCTS")

    # -- ② UNE EXEMPTION REDESCEND LE VERROU, ELLE NE LE FIGE PLUS ----------
    # La lecture en deux colonnes sort `Possession` avant `Pointe`. Le verrou
    # restait à `possession`, donc TOUT ce qui suit et sort avant lui devait
    # être exempté NOMMÉMENT — et la liste s'arrêtait une ligne trop tôt.
    entries, anomalies, conflicts = wrap(page(
        "Possession\nCertains effets font qu’une créature se retrouve possédée "
        "par une autre créature ou entité. Un effet de possession définit le "
        "mode de fonctionnement de la possession.\n\n"
        "Pointe\nLorsque vous entreprenez l’action Pointe, vous recevez du "
        "déplacement supplémentaire pour ce tour. Cette augmentation est égale "
        "à votre Vitesse, après application d’éventuels modificateurs.\n\n"
        "Points de vie\nLes points de vie sont la mesure chiffrée de la "
        "difficulté à tuer une créature ou détruire un objet. Les dégâts les "
        "réduisent, les soins les rétablissent.\n\n"
        "Points de vie temporaires\nLes points de vie temporaires sont "
        "octroyés par certains effets et agissent comme un matelas de sécurité "
        "contre la perte de points de vie réels.\n",
    ))
    assert sorted(e["name"] for e in entries) == [
        "Pointe", "Points de vie", "Points de vie temporaires", "Possession",
    ], [e["name"] for e in entries]
    assert not anomalies, anomalies
    # ⭐ ET `Points de vie temporaires` N'EST PAS DANS `_ORDER_EXEMPT` : il
    # passe parce que le MÉCANISME est réparé, pas parce qu'on l'a nommé.
    assert "Points de vie temporaires" not in parse_glossary_fr._ORDER_EXEMPT
    assert "Points de vie" not in parse_glossary_fr._ORDER_EXEMPT
    print("  ok  lot 102 ② une exemption RE-ANCRE le verrou — la série suivante se répare seule")

    # -- ③ LE FILET REFUSE TOUJOURS, MAIS IL LE DIT ------------------------
    # ⛔ Le refus n'est pas le défaut ; le SILENCE l'était. Une ligne de prose
    # qui ressemble à un nom doit toujours être écartée — et NOMMÉE.
    entries, anomalies, conflicts = wrap(page(
        "Zone d’effet\nUne zone d’effet est un volume défini par un sort ou "
        "une autre capacité, et elle détermine qui se trouve affecté.\n\n"
        "Le point d’origine d’une Ligne n’est pas situé dans la\n"
        "zone qu’elle occupe, et cette précision compte pour savoir qui subit "
        "l’effet lorsqu’on trace le volume depuis son lanceur.\n",
    ))
    assert [e["name"] for e in entries] == ["Zone d’effet"], entries
    assert len(anomalies) == 1, anomalies
    assert "alphabetical net refused" in anomalies[0]["detail"], anomalies[0]
    assert "Le point d’origine" in anomalies[0]["detail"], anomalies[0]
    print("  ok  lot 102 ③ un refus du filet remonte en ANOMALIE, avec le nom de la candidate")

    print("PASS test_parse_glossary_fr")


if __name__ == "__main__":
    main()
