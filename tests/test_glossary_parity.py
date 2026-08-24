"""Les deux glossaires se comparent PAR CONTENU — jamais par compte.

🔴 LE GARDE QUI MANQUAIT, ET LE CAS D'ÉCOLE QUI L'A PAYÉ. Le 2026-08-24, les
deux glossaires portaient 152 entrées chacun. Un garde qui aurait compté était
VERT. Il aurait eu tort de bout en bout :

    absent du français          absent de l'anglais
    Temporary Hit Points        Vitesse d'escalade
    Player Character            Vitesse de nage
    Size                        Vitesse de vol

⭐ TROIS QUI SORTENT, TROIS QUI ENTRENT : le total tombait juste PAR ACCIDENT.
Deux des trois absences étaient de vraies FUITES — le texte était imprimé dans
le livre français et le lecteur le sautait —, et les trois entrées propres au
français comblaient le trou sans rapport aucun avec elles.

⛔ ET LES DEUX FUITES ÉTAIENT PIRES QUE DES ABSENCES : le texte manquant était
collé EN QUEUE de l'entrée précédente. `Points de vie` portait 684 caractères
dont la définition des points de vie temporaires ; `Personnage non-joueur` en
portait 350 dont `Personnage-joueur` en entier. Quatre records faux, pas deux
manquants. C'est la famille du lot 86, à l'identique.

➡️ CE FICHIER NE COMPTE RIEN. Il NOMME les entrées sans vis-à-vis, chacune avec
son motif, et refuse la première qui n'en a pas. Une fuite future arrive donc
sous son nom, pas comme un écart de total.

Run: python3 tests/test_glossary_parity.py
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(HERE, "..", "exports", "srd")


def _records(rel):
    with open(os.path.join(EXPORTS, rel), encoding="utf-8") as fh:
        return json.load(fh)["records"]


def _pairs():
    with open(os.path.join(EXPORTS, "correspondence.json"), encoding="utf-8") as fh:
        return json.load(fh)["pairs"]


# 🔴 LES ORPHELINES, NOMMÉES, CHACUNE AVEC SON MOTIF. Trois motifs existent, et
# ils ne se valent pas :
#   · « édition »  — le livre de cette langue ne l'imprime pas. Rien à réparer.
#   · « arbitrage » — le livre l'imprime, mais lui donner une clef demanderait
#                     d'INVENTER du vocabulaire. Ce n'est pas une mesure, c'est
#                     une décision de produit, et elle appartient à Eric.
# ⛔ Il n'y a PAS de motif « fuite » ici, et c'est délibéré : une fuite se
# répare, elle ne se déclare pas. Une entrée qui en aurait besoin est un lot à
# commander, pas une ligne à ajouter dans cette table.
ORPHELINES_FR = {
    # Le français sort trois vitesses en entrées propres ; l'anglais les replie
    # dans `Climbing`, `Swimming`, `Flying`, qui décrivent le DÉPLACEMENT et pas
    # la vitesse. Vraie divergence entre les deux éditions.
    # ⏳ ARBITRAGE D'ERIC, POSÉ LE 2026-08-24 ET NON RENDU : quelle clef leur
    # donner ? Elles n'ont pas d'anglais à qui l'emprunter, et leur en fabriquer
    # une serait écrire du vocabulaire que le livre ne porte pas.
    "Vitesse d’escalade": "arbitrage",
    "Vitesse de nage": "arbitrage",
    "Vitesse de vol": "arbitrage",
}

ORPHELINES_EN = {
    # ⭐ MESURÉ, PAS SUPPOSÉ (2026-08-24) : le chapitre français a été relu
    # entre ses vraies bornes — de « Définitions des règles » jusqu'à la ligne
    # SEULE « Boîte à outils » suivie de « ludique » (p.203). ⚠️ La borne
    # naïve — chercher la phrase « Boîte à outils ludique » — tombe sur une
    # citation en prose bien avant le chapitre et ferme la fenêtre à la page
    # 193 : le lecteur du glossaire documente lui-même ce piège, et un premier
    # balayage y est tombé.
    # Dans la bonne fenêtre, le cran alphabétique va de `Surprise` directement à
    # `Télépathie`, et l'export reproduit ses treize têtes UNE PAR UNE. Rien
    # n'est perdu : l'entrée n'est pas imprimée. Le français range la matière de
    # `Size` dans `Créature` et dans la table des catégories de taille.
    "Size": "édition",
}

MOTIFS = {"édition", "arbitrage"}


# 🔴 CE QUE LE LECTEUR REFUSE, ET QUI EST MAINTENANT PUBLIÉ. Le filet
# alphabétique écarte des candidates qui ont passé la forme du nom ET le
# plancher de prose — donc des lignes qui ressemblent beaucoup à de vraies
# entrées. Il le faisait EN SILENCE : c'est par cette porte que les deux fuites
# sont sorties. Elles remontent désormais en anomalies, et le build les publie
# dans `exports/exclusions.json`.
#
# ⛔ UN REFUS N'EST PAS UNE ERREUR — celui-ci est CORRECT, c'est une phrase de
# prose qui commence une page et qu'aucun découpage ne peut distinguer d'un nom
# sans la lire. Ce qu'on refuse, c'est le silence. La ligne ci-dessous existe
# pour qu'un refus NEUF casse, et pour que celui-ci cesse de casser le jour où
# il disparaîtrait.
REFUS_DECLARES = {
    "Le point d’origine d’une Ligne n’est pas situé dans la":
        "prose — la phrase ouvre une page (p.195) et porte une majuscule, donc "
        "elle a la forme d'un nom ; sa suite est une vraie phrase, donc elle "
        "passe le plancher de prose. Seul l'ordre alphabétique la démasque.",
}


def unit_aucune_orpheline_sans_motif():
    """Le cœur du garde : il NOMME, il n'additionne pas."""
    for table in (ORPHELINES_FR, ORPHELINES_EN):
        for nom, motif in table.items():
            assert motif in MOTIFS, (
                "« %s » porte le motif %r, qui n'est pas un motif connu (%s). "
                "Une orpheline sans motif est une fuite qu'on a laissée passer."
                % (nom, motif, ", ".join(sorted(MOTIFS))))


def acceptance_les_orphelines_mesurees_sont_celles_declarees():
    """Ce que la donnée dit, confronté à ce que cette table déclare.

    ⛔ AUCUN COMPTE N'EST COMPARÉ ICI. Deux ensembles de NOMS le sont, dans les
    deux sens : une orpheline neuve casse en se nommant, et une orpheline
    déclarée qui a été réparée casse aussi — sans quoi cette table pourrirait,
    et une table qui pourrit est exactement ce qui a laissé filer les fuites.
    """
    fr = _records("fr/glossary.json")
    en = _records("en/glossary.json")
    pairs = _pairs()
    apparies_fr = {p.get("fr") for p in pairs}
    apparies_en = {p.get("en") for p in pairs}

    mesure_fr = {r["name"] for r in fr if r["id"] not in apparies_fr}
    mesure_en = {r["name"] for r in en if r["id"] not in apparies_en}

    for cote, mesure, declare in (("FR", mesure_fr, ORPHELINES_FR),
                                  ("EN", mesure_en, ORPHELINES_EN)):
        neuves = sorted(mesure - set(declare))
        assert not neuves, (
            "%s : entrée(s) de glossaire SANS VIS-À-VIS et non déclarée(s) — %s. "
            "Soit le livre de l'autre langue l'imprime et c'est une FUITE à réparer "
            "(un lot, pas une ligne ici), soit c'est une différence d'édition et il "
            "faut le dire avec son motif." % (cote, ", ".join(neuves)))
        disparues = sorted(set(declare) - mesure)
        assert not disparues, (
            "%s : %s ne sont plus orphelines — la table les déclare encore. "
            "Une déclaration qui survit à ce qu'elle décrivait est une ligne périmée, "
            "et c'est ce qui laisse filer la suivante." % (cote, ", ".join(disparues)))


def acceptance_le_total_ne_prouve_rien():
    """⭐ LA MESURE QUI EXPLIQUE POURQUOI CE FICHIER EXISTE.

    Elle ne vérifie pas que les totaux DIFFÈRENT — ce serait vrai aujourd'hui et
    faux demain, sans que ça dise rien. Elle vérifie que l'écart de total, quel
    qu'il soit, s'explique ENTIÈREMENT par les orphelines déclarées. C'est la
    seule lecture d'un total qui ne mente pas : il n'est pas une preuve, il est
    une CONSÉQUENCE.
    """
    fr = _records("fr/glossary.json")
    en = _records("en/glossary.json")
    ecart = len(fr) - len(en)
    attendu = len(ORPHELINES_FR) - len(ORPHELINES_EN)
    assert ecart == attendu, (
        "l'écart de total est %+d, les orphelines déclarées n'en expliquent que %+d. "
        "⛔ Un total qui ne se déduit pas des noms cache quelque chose — c'est "
        "exactement la situation du 2026-08-24, où 152 == 152 masquait trois fuites."
        % (ecart, attendu))


def acceptance_aucune_definition_n_avale_la_suivante():
    """🔴 LA FAMILLE DU LOT 86, ÉPROUVÉE SUR LE GLOSSAIRE.

    Les deux fuites ne laissaient pas un trou : le texte de l'entrée sautée
    était collé en queue de la précédente. Un compte d'entrées ne peut pas voir
    ça — le record existe, il est simplement FAUX.

    ⚠️ ET LE PREMIER TÉMOIN ESSAYÉ ÉTAIT TROP LARGE — mesuré, pas supposé. Il
    cherchait « un saut de paragraphe suivi du nom d'une autre entrée », et il a
    accusé `Action`, qui se termine légitimement par *« Ces actions sont définies
    ailleurs dans le présent glossaire : »* suivi de la LISTE des noms. Un nom
    cité n'est pas un texte avalé.

    ⭐ LE TÉMOIN QUI DISCRIMINE : une entrée avalée n'apporte pas son nom, elle
    apporte SA DÉFINITION ENTIÈRE — le lecteur découpe le texte entre deux têtes
    acceptées, donc tout ce qui appartenait à la sautée atterrit chez la
    précédente. On teste donc l'INCLUSION DE LA DESCRIPTION, pas la présence du
    nom. ⛔ Et aucun seuil : c'est une inclusion complète, pas une ressemblance.
    """
    for lang in ("fr", "en"):
        records = _records("%s/glossary.json" % lang)
        for porteur in records:
            texte = porteur["data"].get("description") or ""
            if not texte:
                continue
            for autre in records:
                if autre["id"] == porteur["id"]:
                    continue
                avalee = autre["data"].get("description") or ""
                # Une description vide ou minuscule ne prouve rien par inclusion.
                if len(avalee) < 40:
                    continue
                assert avalee not in texte, (
                    "%s : « %s » a AVALÉ « %s » — sa description contient la "
                    "définition ENTIÈRE de l'autre. Le record existe et il est "
                    "faux ; aucun compte d'entrées ne le verrait."
                    % (lang, porteur["name"], autre["name"]))


def acceptance_les_refus_du_lecteur_sont_declares():
    """⭐ LE GARDE QUI AURAIT NOMMÉ LES DEUX FUITES LE JOUR MÊME.

    Le lecteur savait qu'il refusait ; il ne le disait à personne. Maintenant
    qu'il le publie, ce test exige que chaque refus soit DÉCLARÉ avec sa
    raison. Un refus neuf casse ici, sous son nom — et c'est exactement ce qui
    manquait : `Points de vie temporaires` et `Personnage-joueur` sont sortis
    par cette porte, imprimés dans le livre, sans que rien ne bouge.

    ⛔ Il ne compte pas les refus, il les NOMME. Un test qui dirait « au plus
    N refus » laisserait passer le remplacement d'un refus par un autre.
    """
    chemin = os.path.join(EXPORTS, "..", "exclusions.json")
    with open(chemin, encoding="utf-8") as fh:
        publie = json.load(fh)

    refuses = {}
    for r in publie["records"]:
        if r.get("kind") != "glossary" or "alphabetical net refused" not in (r.get("detail") or ""):
            continue
        detail = r["detail"]
        # Le nom de la candidate est entre les premières apostrophes simples.
        debut = detail.index("candidate '") + len("candidate '")
        fin = detail.index("' (key ", debut)
        refuses[detail[debut:fin]] = r.get("source_locator", "")

    neufs = sorted(set(refuses) - set(REFUS_DECLARES))
    assert not neufs, (
        "le filet alphabétique a refusé une candidate NON DÉCLARÉE — %s. "
        "Ouvre le livre à l'endroit que dit `source_locator` : soit c'est une "
        "vraie entrée que le lecteur perd (une FUITE, comme les deux du lot 102), "
        "soit c'est de la prose et il faut le dire ici avec sa raison. "
        "⛔ Ne l'ajoute pas sans avoir regardé." % ", ".join(repr(n) for n in neufs))

    disparus = sorted(set(REFUS_DECLARES) - set(refuses))
    assert not disparus, (
        "%s n'est plus refusé — la déclaration lui survit. Une ligne périmée "
        "dans une table de refus est ce qui masque le refus suivant."
        % ", ".join(repr(d) for d in disparus))


def main():
    unit_aucune_orpheline_sans_motif()
    acceptance_les_refus_du_lecteur_sont_declares()
    acceptance_les_orphelines_mesurees_sont_celles_declarees()
    acceptance_le_total_ne_prouve_rien()
    acceptance_aucune_definition_n_avale_la_suivante()
    print("PASS test_glossary_parity")


if __name__ == "__main__":
    main()
