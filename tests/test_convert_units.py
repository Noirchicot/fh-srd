"""La conversion est une FONCTION, et c'est ce qui autorise l'option 4.

🔴 TOUTE LA DÉCISION D'ERIC REPOSE SUR CE FICHIER. Il a tranché que les nombres
convertis sortent de la donnée et se dérivent au rendu — ce qui n'est possible
QUE si une valeur anglaise rend toujours la même valeur française. Si une seule
en rendait deux, le site français deviendrait faux **sans que rien d'autre
casse** : les records seraient intacts, les paires justes, les comptes verts, et
une valeur sur deux serait tirée au sort.

⭐ MESURÉ SUR TOUT LE CORPUS le 2026-08-24 : 85 entrées, ZÉRO ambiguïté. Et la
mesure du siège portait sur 58 sorts — forte, pas exhaustive. Celle-ci porte sur
les 1 366 paires et sur TOUS les champs porteurs d'unité.

⛔ CE FICHIER NE COMPTE PAS LES ENTRÉES. Un compte figé se périmerait au premier
objet ajouté au livre ; ce qu'on garde, c'est la PROPRIÉTÉ.

Run: python3 tests/test_convert_units.py
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import convert_units  # noqa: E402

EXPORTS = os.path.join(HERE, "..", "exports", "srd")


def _table():
    """La table PUBLIÉE, telle que le rendu la consulte."""
    with open(os.path.join(EXPORTS, "conversions.json"), encoding="utf-8") as fh:
        return json.load(fh)


def unit_la_coupure_est_par_valeur_jamais_par_champ():
    """⚠️ LE PIÈGE DE CE MODULE, et il est réel dans la donnée.

    `monster.speed` vaut TANTÔT `20 ft.` — une conversion pure — TANTÔT
    `30 ft., Fly 60 ft.`, qui est une PHRASE. Décider « le champ speed se
    convertit » perdrait les phrases françaises ; décider « il se traduit »
    ferait entrer des conversions dans le patch. On regarde la valeur.
    """
    assert convert_units.is_pure_conversion("30 feet")
    assert convert_units.is_pure_conversion("20 ft.")
    assert convert_units.is_pure_conversion("1/2 lb.")
    assert convert_units.is_pure_conversion("1,000 GP")
    assert convert_units.is_pure_conversion("30/120 feet")
    # ⛔ Une phrase qui CONTIENT une unité n'est pas une conversion.
    assert not convert_units.is_pure_conversion("30 ft., Fly 60 ft.")
    assert not convert_units.is_pure_conversion("Darkvision 60 ft.; Passive Perception 9")
    assert not convert_units.is_pure_conversion("Self")
    assert not convert_units.is_pure_conversion(None)


def unit_la_table_refuse_de_cesser_d_etre_une_fonction():
    """⭐ LE GARDE, ÉPROUVÉ EN LE FAISANT MORDRE — un garde qu'on n'a pas vu
    mordre ne mord pas. Deux paires fabriquées donnent à la même valeur
    anglaise deux valeurs françaises : `derive` doit REFUSER, pas arbitrer.
    """
    faux = {
        "fr": {"f1": {"data": {"weight": "1,5 kg"}},
               "f2": {"data": {"weight": "1,4 kg"}}},
        "en": {"e1": {"data": {"weight": "3 lb."}},
               "e2": {"data": {"weight": "3 lb."}}},
    }
    try:
        convert_units.derive([("f1", "e1"), ("f2", "e2")], faux)
    except convert_units.ConversionError as err:
        assert "FONCTION" in str(err), err
        assert "1,4 kg" in str(err) and "1,5 kg" in str(err), (
            "le refus doit NOMMER les deux valeurs : « une valeur anglaise en "
            "rend deux » sans dire lesquelles n'aide personne")
        return
    raise AssertionError("la table a accepté deux françaises pour une anglaise")


def unit_une_valeur_absente_crie_au_lieu_de_se_replier():
    """⛔ PAS DE REPLI SILENCIEUX SUR L'ANGLAIS. Une valeur manquante afficherait
    `30 feet` au lecteur français ; le garde de reconstruction verrait bien un
    mot changé, mais il ne dirait pas POURQUOI. C'est ici que ça doit crier.
    """
    try:
        convert_units.apply({}, "weight", "3 lb.")
    except convert_units.ConversionError as err:
        assert "3 lb." in str(err) and "weight" in str(err), err
        return
    raise AssertionError("une conversion inconnue a été rendue en silence")


def acceptance_la_table_publiee_est_une_fonction():
    """🔴 CE FICHIER NE PROUVE PLUS LA COMPLÉTUDE — ET C'EST UN GAIN, PAS UNE
    PERTE. Il la prouvait en re-dérivant la table depuis les DEUX catalogues.
    Depuis la transition à froid il n'y en a plus qu'un : les records sont
    adressés en anglais et le français est un patch qui, précisément, ne porte
    plus les valeurs converties. La dérivation n'a plus d'entrées à lire.

    ⭐ SA COMPLÉTUDE EST PROUVÉE AILLEURS, ET MIEUX : les 18 pages françaises se
    reconstruisent au mot près. Une conversion manquante ferait bouger un mot,
    et le garde dirait LEQUEL. Aucun re-calcul ne peut en dire autant.

    ⭐ CE QUI RESTE À PROUVER ICI EST CE QUE LES PAGES NE VOIENT PAS : la FORME.
    Une table complète peut n'être pas une fonction — deux entrées pour la même
    valeur anglaise passeraient inaperçues sur des pages qui n'en emploient
    qu'une.
    """
    publie = _table()
    vus = {}
    for champ, entrees in publie["fields"].items():
        for en, fr in entrees.items():
            assert (champ, en) not in vus, (champ, en)
            vus[(champ, en)] = fr
    assert publie["count"] == len(vus), (publie["count"], len(vus))
    assert sorted(publie["fields"]) == ["cost", "range", "speed", "weight"], (
        sorted(publie["fields"]))


def acceptance_la_clef_porte_la_dimension():
    """⭐ LA CLEF EST `(champ, valeur)`, ET C'EST LA PLUS ÉTROITE DES TROIS QUI
    MARCHENT. Mesuré : `(genre, champ, valeur)` 130 entrées, `(champ, valeur)`
    85, la valeur seule 84 — les trois sans ambiguïté.

    ⛔ La valeur seule serait plus courte et accepterait EN SILENCE un `30 feet`
    qui voudrait dire autre chose dans un champ futur. Ce test garde donc la
    preuve que la dimension est portée : la MÊME valeur anglaise vit sous deux
    champs différents, et c'est ce qui rend la clef à un terme insuffisante.
    """
    champs = _table()["fields"]
    assert champs["range"]["30 feet"] == "9 m", champs["range"]["30 feet"]
    assert champs["speed"]["30 feet"] == "9 m", champs["speed"]["30 feet"]
    # ⭐ Ici les deux tombent d'accord — mais rien ne l'impose, et c'est
    # exactement pourquoi le champ reste dans la clef.
    partages = [v for v in champs["range"] if v in champs["speed"]]
    assert partages, (
        "aucune valeur n'est portée par deux champs : la clef à deux termes "
        "n'a plus de témoin, remesurer avant de la simplifier")


def acceptance_les_arrondis_sont_ceux_du_livre():
    """📌 LA TABLE NE MULTIPLIE RIEN, ELLE LIT.

    30 pieds font 9,144 m et le livre écrit `9 m` ; un mille fait 1,609 km et
    le livre écrit `1,5 km`. ⭐ Une table recalculée serait un AUTRE livre — et
    elle aurait l'air juste, ce qui est pire.
    """
    with open(os.path.join(EXPORTS, "conversions.json"), encoding="utf-8") as fh:
        champs = json.load(fh)["fields"]
    assert champs["range"]["30 feet"] == "9 m", champs["range"]["30 feet"]
    assert champs["range"]["1 mile"] == "1,5 km", champs["range"]["1 mile"]
    # ⭐ Et le livre change d'unité quand ça l'arrange : une demi-livre passe en
    # GRAMMES, pas en kilos. Un convertisseur générique aurait écrit `0,25 kg`.
    assert champs["weight"]["1/2 lb."] == "250 g", champs["weight"]["1/2 lb."]
    assert champs["weight"]["3 lb."] == "1,5 kg", champs["weight"]["3 lb."]

    # ⭐⭐ ET VOICI LE TEST QU'UN CALCUL ÉCHOUE ET QUE LE LIVRE PASSE. On écrit
    # le convertisseur générique — celui que n'importe qui écrirait — et on
    # montre qu'il donne une AUTRE réponse. Sans ça, « la table porte les
    # arrondis du livre » resterait une phrase.
    def convertisseur_generique(valeur_en):
        """Ce qu'une bibliothèque d'unités rendrait, honnêtement et faux."""
        nombre, unite = valeur_en.rsplit(" ", 1)
        if "/" in nombre:
            a, b = nombre.split("/")
            nombre = float(a) / float(b)
        else:
            nombre = float(nombre.replace(",", ""))
        if unite.startswith("lb"):
            return "%g kg" % round(nombre * 0.4536, 3)
        if unite.startswith(("feet", "foot", "ft")):
            return "%g m" % round(nombre * 0.3048, 3)
        raise AssertionError(unite)

    for valeur_en, du_livre in (("1/2 lb.", "250 g"), ("3 lb.", "1,5 kg")):
        calcule = convertisseur_generique(valeur_en)
        assert calcule != du_livre, (
            "le convertisseur générique rend %r pour %r, la même chose que le "
            "livre — ce témoin ne prouve plus rien, en trouver un autre"
            % (calcule, valeur_en))
    # ⭐ La demi-livre est le cas qui tranche : le livre CHANGE D'UNITÉ (des
    # grammes), là où le calcul reste en kilos. Aucune arithmétique ne fait ça.
    assert convertisseur_generique("1/2 lb.").endswith("kg")
    assert champs["weight"]["1/2 lb."].endswith(" g")

    # ⛔ Et un mille ne fait pas 1,5 km — le livre arrondit, la table le suit.
    assert champs["range"]["1 mile"] == "1,5 km"
    assert round(1 * 1.609, 3) != 1.5


def acceptance_aucune_page_francaise_ne_porte_une_unite_anglaise():
    """⭐⭐ LA COMPLÉTUDE DE LA TABLE, SOUS SA FORME PERMANENTE.

    Le lot 104 l'a prouvée UNE FOIS, et de la meilleure façon : les 18 pages
    françaises se reconstruisent au mot près après la migration. ⛔ Mais cette
    preuve-là ne se garde pas — elle compare à un commit, donc elle se périme
    au suivant.

    ⭐ L'INVARIANT EN DESSOUS, LUI, EST PERMANENT : une conversion manquante ne
    disparaît pas en silence, elle imprime `30 feet` sur une page française.
    Ce test lit donc les pages RENDUES et refuse toute unité anglaise. Il
    couvre ce que la table ne peut pas dire d'elle-même : elle peut être une
    fonction, avoir la bonne clef, porter les arrondis du livre — et être
    INCOMPLÈTE. Seule la page le dit.

    ⚠️ On cherche l'unité COLLÉE À UN NOMBRE, jamais le mot seul : le glossaire
    français cite légitimement des termes anglais dans ses renvois, et refuser
    « feet » partout accuserait des pages saines.
    """
    racine = os.path.join(HERE, "..", "web", "fr")
    if not os.path.isdir(racine):
        print("SKIP pages — le site n'est pas construit")
        return
    motif = re.compile(r"\d+(?:[.,]\d+)?\s*(?:feet|foot|ft\.|lb\.|pounds?|GP|SP|CP|EP)\b")
    fautes = []
    pages = 0
    for genre in sorted(os.listdir(racine)):
        chemin = os.path.join(racine, genre, "index.html")
        if not os.path.exists(chemin):
            continue
        pages += 1
        with open(chemin, encoding="utf-8") as fh:
            for trouve in set(motif.findall(fh.read())):
                fautes.append("%s : %r" % (genre, trouve))
    assert pages >= 15, "seulement %d pages françaises lues" % pages
    assert not fautes, (
        "UNE PAGE FRANÇAISE IMPRIME UNE UNITÉ ANGLAISE — la table de "
        "conversion est incomplète, et voici ce qui manque : %s. ⛔ Le rendu ne "
        "se replie jamais sur l'anglais en silence ; si ceci apparaît, c'est "
        "qu'une valeur a échappé à la coupure « conversion pure »." % fautes[:8])
    # ⭐ LE CONTRÔLE, ET IL NE COÛTE RIEN : le MÊME motif sur les pages
    # ANGLAISES doit trouver, et abondamment. Sans lui, un motif qui ne
    # matcherait jamais rien passerait pour un garde vert.
    anglaises = os.path.join(HERE, "..", "web", "en")
    trouve_en = 0
    for genre in sorted(os.listdir(anglaises)):
        chemin = os.path.join(anglaises, genre, "index.html")
        if os.path.exists(chemin):
            with open(chemin, encoding="utf-8") as fh:
                trouve_en += len(motif.findall(fh.read()))
    assert trouve_en > 100, (
        "le motif ne trouve que %d unités anglaises sur les pages ANGLAISES — "
        "il ne détecte donc pas ce qu'il prétend, et son zéro côté français ne "
        "prouve rien" % trouve_en)
    print("  ok  %d pages françaises, aucune unité anglaise (le même motif en "
          "trouve %d côté anglais) — la table est complète"
          % (pages, trouve_en))


def main():
    unit_la_coupure_est_par_valeur_jamais_par_champ()
    unit_la_table_refuse_de_cesser_d_etre_une_fonction()
    unit_une_valeur_absente_crie_au_lieu_de_se_replier()
    acceptance_la_table_publiee_est_une_fonction()
    acceptance_la_clef_porte_la_dimension()
    acceptance_les_arrondis_sont_ceux_du_livre()
    acceptance_aucune_page_francaise_ne_porte_une_unite_anglaise()
    print("PASS test_convert_units")


if __name__ == "__main__":
    main()
