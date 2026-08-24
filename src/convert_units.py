"""La conversion d'unités : DÉRIVÉE de la donnée, jamais écrite à la main.

🔴 CE MODULE EXISTE PARCE QU'UNE CONVERSION N'EST PAS UNE TRADUCTION. Un mot
français se **prend dans le livre** ; un nombre français se **recalcule**. La
loi §0.13 sépare l'identifiant du mot — et une UNITÉ n'est ni l'un ni l'autre,
c'est un RENDU. Le poids reste `3 lb.` dans la donnée ; afficher `1,5 kg` est le
travail de l'écran.

⭐ ET LA TABLE NE S'ÉCRIT PAS, ELLE SE DÉRIVE. Elle existait déjà : c'était la
donnée française elle-même. Chaque paire prouvée par la correspondance donne
une valeur anglaise et sa valeur française ; il suffit de les lire.

📌 ELLE PORTE LES ARRONDIS DU LIVRE, PAS CEUX DU CALCUL. Le livre écrit `9 m`
là où 30 pieds font 9,144 — et `1,5 km` pour un mille, qui en fait 1,609. ⛔ Un
produit recalculé serait un autre livre. La table ne multiplie rien : elle lit.

## Ce qui entre dans la table, et ce qui n'y entre PAS

⚠️ LA COUPURE EST PAR VALEUR, JAMAIS PAR CHAMP — mesuré le 2026-08-24, et c'est
le piège de ce module. `monster.speed` vaut tantôt `20 ft.` (une conversion
pure, 9 fois) et tantôt `30 ft., Fly 60 ft.` (une PHRASE française, 200 fois).
Décider « le champ speed se convertit » perdrait les 200 phrases ; décider « il
se traduit » gonflerait le patch de 9 conversions. On regarde la VALEUR.

    conversion PURE   la valeur entière est un nombre et son unité
                      → elle sort du patch, elle entre ici
    tout le reste     une phrase, même si elle contient une unité
                      → elle reste dans le patch : c'est un mot du livre

## La preuve que ça tient : la conversion est une FONCTION

⭐ MESURÉ SUR TOUT LE CORPUS, tous champs porteurs d'unité confondus :
**85 entrées, ZÉRO ambiguïté** — aucune valeur anglaise ne rend deux valeurs
françaises. C'est là-dessus que repose le droit de sortir ces valeurs du patch,
et `derive()` le REVÉRIFIE à chaque construction : si une valeur anglaise en
rendait deux, elle jette en les nommant. ⛔ Une table qui cesserait d'être une
fonction rendrait le site français faux sans rien casser d'autre.

⚠️ LA CLEF EST `(champ, valeur anglaise)`, ET C'EST DÉLIBÉRÉMENT LA PLUS
ÉTROITE DES TROIS QUI MARCHENT. Mesurées : `(genre, champ, valeur)` 130 entrées,
`(champ, valeur)` 85, `(valeur)` seule 84 — les trois sans ambiguïté. La valeur
seule serait plus courte et accepterait en silence un `30 feet` qui voudrait
dire autre chose dans un champ futur ; le genre en tête recopierait `1 GP` dans
quatre genres pour ne rien dire de plus. Le champ porte la DIMENSION, et un
champ neuf portant une unité est REFUSÉ par son nom — il mérite qu'on le
regarde.
"""

import re

# Une valeur PUREMENT convertie : rien que des chiffres et leur unité. Les
# formes réelles du corpus, mesurées : `30 feet`, `20 ft.`, `1 mile`,
# `1/2 lb.`, `1,000 GP`, `30/120 feet`.
_UNITE_EN = r"(?:feet|foot|ft\.?|miles?|lb\.?|pounds?|GP|SP|CP|PP|EP)"
_PURE = re.compile(r"^\s*[\d.,/ ]+\s*%s\s*$" % _UNITE_EN, re.I)


class ConversionError(Exception):
    """La conversion a cessé d'être une fonction, ou une valeur manque."""


def is_pure_conversion(value):
    """Vrai si la valeur ANGLAISE est un nombre et son unité, et rien d'autre.

    ⛔ On interroge l'anglais, jamais le français : c'est l'anglais qui reste
    dans la donnée, donc c'est lui qui décide de ce qui se convertit.
    """
    return isinstance(value, str) and bool(_PURE.match(value))


def derive(pairs, records_by_lang):
    """La table, lue dans les paires prouvées. Aucune ligne n'est écrite ici.

    `pairs` : [(id_fr, id_en)] — uniquement des paires PROUVÉES. Une paire
    douteuse fabriquerait une conversion fausse qui aurait l'air d'une mesure.

    Rend `{(champ, valeur_en): valeur_fr}`.
    """
    vues = {}
    conflits = {}
    for fid, eid in pairs:
        fr = records_by_lang["fr"].get(fid)
        en = records_by_lang["en"].get(eid)
        if fr is None or en is None:
            continue
        a, b = fr.get("data") or {}, en.get("data") or {}
        for champ in set(a) | set(b):
            va, vb = a.get(champ), b.get(champ)
            if va == vb or not is_pure_conversion(vb) or not isinstance(va, str):
                continue
            clef = (champ, vb)
            if clef in vues and vues[clef] != va:
                conflits.setdefault(clef, {vues[clef]}).add(va)
            else:
                vues[clef] = va
    if conflits:
        raise ConversionError(
            "la conversion a cessé d'être une FONCTION — %s. Une valeur "
            "anglaise qui rend deux valeurs françaises ne peut pas être "
            "dérivée : le site français serait faux sans que rien d'autre "
            "casse. Refusé, pas arbitré."
            % "; ".join(
                "%s «%s» → %s" % (c, v, sorted(fs))
                for (c, v), fs in sorted(conflits.items())
            )
        )
    return vues


def apply(table, champ, valeur_en):
    """La valeur française d'une conversion, ou une erreur QUI NOMME.

    ⛔ Pas de repli silencieux sur l'anglais : une valeur absente de la table
    afficherait `30 feet` au lecteur français sans que personne le sache. Le
    garde de reconstruction à l'octet près NE VERRAIT PAS un repli, il ne verra
    qu'un mot changé — donc c'est ici que ça doit crier.
    """
    try:
        return table[(champ, valeur_en)]
    except KeyError:
        raise ConversionError(
            "aucune conversion connue pour %s «%s». La table se dérive des "
            "paires prouvées : soit ce record n'a pas de jumeau français, soit "
            "le livre français n'imprime pas cette valeur. Refusé, pas deviné."
            % (champ, valeur_en)
        )


def as_export(table):
    """La table, en JSON stable, groupée par champ — pour être RELUE."""
    par_champ = {}
    for (champ, en), fr in table.items():
        par_champ.setdefault(champ, {})[en] = fr
    return {champ: dict(sorted(v.items())) for champ, v in sorted(par_champ.items())}
