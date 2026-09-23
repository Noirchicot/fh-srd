"""The eleven key families, and the proof that none of them is a translation.

⭐ THE DISCIPLINE THIS FILE ENFORCES, and it is the whole reason lot 98 could
be trusted: **a table written by hand must be checked by something that never
read it.** Every mapping in `derive_mechanics`, `species_structure` and
`parse_class_progression_en` is re-derived here from the EXPORTS -- by walking
pairs the correspondence layer proved, reading what each side carries, and
keeping a mapping only when no two pairs disagree. If a declared line and the
data disagree, the declared line is the one that is wrong.

🔴 AND IT CAUGHT A REAL ONE. The lineage table was built by pairing lineages by
their POSITION inside each species' list -- which every language sorts in its
own alphabet -- and came out with `elfe-sylvestre` as `high-elf` and
`haut-elfe` as `wood-elf`, exactly swapped. It reported ZERO CONFLICTS, because
each value occurs once and nothing could disagree. ⛔ A clean conflict count
proves nothing about the contents.

Run: python3 tests/test_key_families.py
"""

import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(ROOT, "exports", "srd")

sys.path.insert(0, os.path.join(ROOT, "src"))

import french_layer  # noqa: E402

# ⭐ Le seul endroit du dépôt qui écrive une adresse française — et il dit
# pourquoi : la base de travail est gitignorée, et les routes doivent tourner.
from french_layer import working_base_id as FR  # noqa: E402

import derive_mechanics as dm  # noqa: E402
import parse_class_progression_en as prog  # noqa: E402
import species_structure  # noqa: E402


def load(lang, kind):
    """⭐ UNE SEULE LECTURE POUR TOUT LE DÉPÔT — `src/french_layer.py`.
    
    Depuis la transition à froid, `exports/srd/fr/*.json` ne porte plus de
    records mais des PATCHES posés sur les adresses anglaises. Lire `["records"]`
    ici casserait — et si chaque test reconstituait de son côté, les copies
    divergeraient exactement comme divergent toujours deux écritures d'une
    même liste.
    """
    return french_layer.load(EXPORTS, lang, kind)


def paires_identiques(kind):
    """Les « paires » d'un genre — et depuis le lot 104, c'est L'IDENTITÉ.

    ⭐ Ce fichier appariait par la table de correspondance. Après la transition
    à froid, le record français et l'anglais vivent à la MÊME adresse : leur
    appariement est donc l'identité sur cet identifiant. Ce n'est pas une
    commodité d'écriture, c'est le résultat qu'on garde — et si deux adresses
    redevenaient distinctes, tout ce qui suit s'arrêterait de mesurer.
    """
    en = {r["id"] for r in load("en", kind)}
    fr = {r["id"] for r in load("fr", kind)}
    communes = en & fr
    assert communes, (
        "%s : aucune adresse commune aux deux langues — la couche française "
        "n'est plus posée sur les records anglais." % kind)
    return {rid: rid for rid in sorted(communes)}


def _observe(kind, values):
    """La valeur FRANÇAISE → les valeurs ANGLAISES portées à la même adresse.

    🔴 CE FICHIER A CHANGÉ DE MÉCANIQUE AU LOT 105, ET C'EST UNE MONTÉE D'UN
    CRAN. Il appariait par la table de correspondance (`{en → fr}`) pour
    re-dériver les tables déclarées. Depuis la transition à froid il n'y a plus
    qu'un jeu d'adresses : le record français et l'anglais vivent AU MÊME
    ENDROIT, et la dérivation est devenue triviale.

    ⭐ CETTE TRIVIALITÉ EST LE NOUVEL INVARIANT, PAS LA FIN DU TEST. À la même
    adresse, les deux langues doivent porter LA MÊME clef. Le jour où l'une
    d'elles porterait autre chose, l'embranchement serait revenu — et c'est la
    seule chose qui puisse défaire cette migration EN SILENCE : tous les
    comptes resteraient justes.
    """
    en = {r["id"]: r for r in load("en", kind)}
    fr = {r["id"]: r for r in load("fr", kind)}
    seen = collections.defaultdict(collections.Counter)
    used = 0
    for rid, e in en.items():
        f = fr.get(rid)
        if f is None:
            continue
        used += 1
        for a, b in zip(values(e["data"]), values(f["data"])):
            seen[b][a] += 1
    return seen, used


def check_scalar(kind, field, declared, label):
    """A field carrying ONE value per record: position cannot mislead."""
    seen, used = _observe(kind, lambda d: [d[field]] if d.get(field) else [])
    conflicts = {k: dict(c) for k, c in seen.items() if len(c) > 1}
    assert not conflicts, (label, conflicts)
    for french, counter in seen.items():
        english = next(iter(counter))
        assert declared.get(french) == english, (
            "%s: the data says %r stands for %r; the declared table says %r"
            % (label, french, english, declared.get(french)))
    assert len(seen) >= 1, label
    print("  ok  %-26s %d/%d re-derived from %d pairs, 0 conflicts"
          % (label, len(seen), len(declared), used))


def unit_the_scalar_families():
    # ⭐ `damage_type_key` is the one family whose migration is COMPLETE: it was
    # already named `_key`, so it was fixed in place rather than doubled. Both
    # sides now carry the same three English values, which is why the check is
    # "they agree" rather than "this French word means that English one".
    seen, used = _observe("weapon", lambda d: [d["damage_type_key"]])
    assert set(seen) == {"bludgeoning", "piercing", "slashing"}, sorted(seen)
    for value, counter in seen.items():
        assert list(counter) == [value], (value, dict(counter))
    print("  ok  %-26s 3/3 identical on both sides over %d weapon pairs"
          % ("damage_type_key", used))
    check_scalar("weapon", "mastery", dm.MASTERY_KEYS["fr"], "mastery")
    check_scalar("spell", "school", dm.SCHOOL_KEYS["fr"], "school")
    check_scalar("glossary", "tag", dm.GLOSSARY_TAG_KEYS["fr"], "glossary tag")


def unit_spell_classes_by_occurrence():
    """⛔ NOT BY POSITION. Each language sorts its own class list, so the third
    name on one side is not the third on the other. Which SPELLS carry a class
    is a fact no ordering can touch."""
    en = {r["id"]: r for r in load("en", "spell")}
    fr = {r["id"]: r for r in load("fr", "spell")}
    couples = [(e, f) for e, f in sorted(paires_identiques("spell").items()) if e in en and f in fr]
    pe, pf = collections.defaultdict(set), collections.defaultdict(set)
    for i, (e, f) in enumerate(couples):
        for name in en[e]["data"].get("classes") or []:
            pe[name].add(i)
        for name in fr[f]["data"].get("classes") or []:
            pf[name].add(i)
    checked = 0
    for french, footprint in pf.items():
        matches = [e for e, t in pe.items() if t == footprint]
        assert len(matches) == 1, (french, matches)
        assert dm.SPELL_CLASS_KEYS["fr"][french] == matches[0], (french, matches)
        checked += 1
    assert checked == 8, checked
    print("  ok  %-26s 8/8 by occurrence profile over %d spell pairs"
          % ("spell classes", len(couples)))


def unit_lineages_by_their_spells():
    """The family the position bug swapped. Settled by the spells they grant."""
    spell_en = {r["id"]: r["name"] for r in load("en", "spell")}
    spell_fr = {r["id"]: r["name"] for r in load("fr", "spell")}
    translate = {spell_fr[f].lower(): spell_en[e]
                 for e, f in paires_identiques("spell").items() if e in spell_en and f in spell_fr}
    en = {r["id"]: r for r in load("en", "species")}
    fr = {r["id"]: r for r in load("fr", "species")}

    def spells(lineage, translated):
        levels = lineage.get("levels") or {}
        out = set()
        for key in ("3", "5"):
            value = levels.get(key)
            if value:
                out.add(translate.get(value.lower(), value) if translated else value)
        return frozenset(out)

    checked = 0
    for e, f in sorted(paires_identiques("species").items()):
        if e not in en or f not in fr:
            continue
        english = en[e]["data"].get("lineages") or []
        french = fr[f]["data"].get("lineages") or []
        if not english:
            continue
        for one in french:
            want = spells(one, True)
            matches = [b for b in english if spells(b, False) == want]
            if len(matches) != 1:
                continue          # `chtonien`: one of its spells is unpaired
            assert one["id"] == matches[0]["id"], (
                "the spells say %r is %r, the export says %r"
                % (one["name"], matches[0]["id"], one["id"]))
            checked += 1
    assert checked >= 5, checked
    # ⭐ The swap this test exists for: reading the two elves the wrong way round
    # is the exact failure it must refuse.
    declared = species_structure.FRENCH_LINEAGE_KEYS
    assert declared["elfe-sylvestre"] == "wood-elf"
    assert declared["haut-elfe"] == "high-elf"
    print("  ok  %-26s %d/6 by the spells each one grants, and the two elves "
          "are the right way round" % ("species lineages", checked))


def unit_resource_columns_by_their_series():
    """⚠️ Case-folded: the Bard's die reads `d6` in French and `D6` in English,
    and a case-sensitive comparison leaves that column unmatched for no reason
    that has anything to do with the language."""
    en = {r["id"]: r for r in load("en", "class-progression")}
    fr = {r["id"]: r for r in load("fr", "class-progression")}

    def series(data):
        keys = [c["key"] for c in data["resource_columns"]]
        return {k: [str((lv.get("resources") or {}).get(k)).lower()
                    for lv in data["levels"]] for k in keys}

    checked, seen = 0, set()
    for e, f in sorted(paires_identiques("class-progression").items()):
        if e not in en or f not in fr:
            continue
        se, sf = series(en[e]["data"]), series(fr[f]["data"])
        labels = {c["key"]: c["label"] for c in fr[f]["data"]["resource_columns"]}
        for key, values in sf.items():
            matches = [k for k, v in se.items() if v == values]
            if len(matches) != 1:
                continue
            assert key == matches[0], (labels[key], key, matches[0])
            seen.add(key)
            checked += 1
    assert len(seen) >= 16, sorted(seen)
    # The label stays French; only the key crossed.
    french_labels = {c["label"] for r in load("fr", "class-progression")
                     for c in r["data"]["resource_columns"]}
    assert "Sorts mineurs" in french_labels, sorted(french_labels)[:6]
    print("  ok  %-26s %d columns re-derived from their value series, labels "
          "still French" % ("progression resources", len(seen)))


def unit_monster_abilities_by_value():
    """The six ability keys, read off the SCORES rather than off the names.

    In a paired monster the only French key carrying 21 opposite an English
    `str` of 21 is `for`. No name is compared; nothing is declared that the
    numbers do not already say."""
    en = {r["id"]: r for r in load("en", "monster")}
    fr = {r["id"]: r for r in load("fr", "monster")}
    seen = collections.defaultdict(collections.Counter)
    used = 0
    for e, f in paires_identiques("monster").items():
        if e not in en or f not in fr:
            continue
        used += 1
        a, b = en[e]["data"]["abilities"], fr[f]["data"]["abilities"]
        for key, value in a.items():
            matches = [k for k, v in b.items() if v == value]
            if len(matches) == 1:
                seen[key][matches[0]] += 1
    assert used >= 300, used
    for key, counter in seen.items():
        assert len(counter) == 1, (key, dict(counter))
        assert next(iter(counter)) == key, (key, dict(counter))
    assert set(seen) == {"str", "dex", "con", "int", "wis", "cha"}, sorted(seen)
    print("  ok  %-26s 6/6 keys agree across %d monster pairs, by value alone"
          % ("monster abilities", used))


def acceptance_no_french_key_survives():
    """⛔ NOT ONE of the eleven families still carries a French value.

    The point of the whole lot, checked on the published exports rather than on
    the code that produced them.
    """
    french_leftovers = []
    for record in load("fr", "weapon"):
        data = record["data"]
        if data["damage_type_key"] not in ("bludgeoning", "piercing", "slashing"):
            french_leftovers.append(("weapon.damage_type_key", data["damage_type_key"]))
        if data.get("mastery_key") and data["mastery_key"] not in dm.MASTERY_KEYS["en"]:
            french_leftovers.append(("weapon.mastery_key", data["mastery_key"]))
    for record in load("fr", "spell"):
        data = record["data"]
        if data["school_key"] not in dm.SCHOOL_KEYS["en"]:
            french_leftovers.append(("spell.school_key", data["school_key"]))
        for key in data["class_keys"]:
            if key not in dm.SPELL_CLASS_KEYS["en"]:
                french_leftovers.append(("spell.class_keys", key))
    for record in load("fr", "monster"):
        extra = set(record["data"]["abilities"]) - {"str", "dex", "con", "int",
                                                    "wis", "cha"}
        if extra:
            french_leftovers.append(("monster.abilities", sorted(extra)))
    for record in load("fr", "species"):
        for lineage in record["data"].get("lineages") or []:
            if lineage["id"] not in set(species_structure.FRENCH_LINEAGE_KEYS.values()):
                french_leftovers.append(("species.lineages[].id", lineage["id"]))
    for record in load("fr", "class-progression"):
        for column in record["data"]["resource_columns"]:
            if column["key"] not in set(prog.FRENCH_RESOURCE_KEYS.values()):
                french_leftovers.append(("resource_columns[].key", column["key"]))
    assert not french_leftovers, french_leftovers

    # ⭐ And the words are still French where a reader sees them.
    weapon = next(r for r in load("fr", "weapon") if r["data"].get("mastery"))
    assert weapon["data"]["mastery"] in dm.MASTERY_KEYS["fr"], weapon["data"]["mastery"]
    spell = load("fr", "spell")[0]["data"]
    assert spell["school"] in dm.SCHOOL_KEYS["fr"], spell["school"]
    print("  ok  no French value survives in any of the eleven key families, "
          "and every printed word is still French")


# 🔴 LES CHAMPS QUI SONT DES CLEFS, PAS DES MOTS. Onze familles, plus les
# champs dont le NOM le dit (`*_key`, `*_keys`). ⛔ Aucun d'eux n'a le droit
# d'apparaître dans un patch français.
FAMILLES_DE_CLEFS = (
    "damage_type_key", "mastery_key", "school_key", "class_keys", "tag_key",
    "ability_key", "primary_ability_keys", "primary_ability_mode",
    "strength_min", "abilities",
)


def acceptance_un_patch_francais_ne_porte_que_des_mots():
    """🔴🔴 LE GARDE QUI VERRAIT L'EMBRANCHEMENT REVENIR — et rien d'autre ne
    le verrait.

    Toute cette migration tient sur une phrase : **il n'y a qu'un jeu de
    records, et le français est ce qu'on pose dessus, en MOTS.** Si un patch
    recommençait à porter une CLEF, la couche redeviendrait un embranchement —
    et **tous les comptes resteraient justes**. Les pages se reconstruiraient
    au mot près, la correspondance garderait ses 1 366 paires, les onze
    familles s'accorderaient encore. Rien ne crierait.

    ⭐ On lit donc les patches BRUTS, pas les records reconstitués : c'est le
    fichier commité qui doit être propre, pas la lecture qu'on en fait.

    Deux fautes sont refusées, et elles ne se ressemblent pas :
      · une CLEF dans un patch — le français redécide d'une valeur structurelle ;
      · une ADRESSE dans un patch — une référence croisée qui n'a pas suivi.
    ⚠️ La seconde est celle qui a vraiment failli passer : sans le réadressage
    fait AVANT la comparaison, les 544 références croisées entraient telles
    quelles et personne ne l'aurait vu.
    """
    fautes = []
    adresses = []
    ordres = set()
    directory = os.path.join(EXPORTS, "fr")
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(directory, name), encoding="utf-8") as fh:
            payload = json.load(fh)
        assert "patches" in payload, (
            "%s ne porte pas de `patches` — la couche française n'est plus un "
            "patch, donc plus rien ici ne mesure ce qu'il faut." % name)
        for patch in payload["patches"]:
            for champ, valeur in patch["data"].items():
                if champ.endswith(("_key", "_keys")) or champ in FAMILLES_DE_CLEFS:
                    fautes.append("%s · %s · %s" % (name, patch["id"], champ))
                texte = json.dumps(valeur, ensure_ascii=False)
                if ":fr:" in texte:
                    adresses.append("%s · %s · %s" % (name, patch["id"], champ))
                elif "srd:" in texte:
                    ordres.add("%s.%s" % (name[:-5], champ))

    assert not fautes, (
        "UN PATCH FRANÇAIS PORTE UNE CLEF — l'embranchement est revenu : %s. "
        "Une clef est structurelle : elle appartient au record, pas au mot que "
        "l'interface affiche. Rien d'autre ne verrait ça." % fautes[:6])
    assert not adresses, (
        "UN PATCH FRANÇAIS PORTE UNE ADRESSE FRANÇAISE — une référence croisée "
        "n'a pas suivi la migration : %s. Elles se réadressent AVANT d'être "
        "comparées, et c'est ce « avant » qui les fait sortir du patch toutes "
        "seules." % adresses[:6])

    # ⚠️ ET VOICI OÙ MA MESURE AFFINE LA CONSIGNE. « Un patch ne porte que des
    # mots » est trop absolu : quatre champs y gardent une LISTE D'ADRESSES
    # ANGLAISES, dans l'ordre alphabétique FRANÇAIS. Mesuré : 27 patches, dont
    # 18 où seul l'ordre diffère, et ZÉRO adresse française.
    #
    # ⭐ UN ORDRE N'EST NI UNE CLEF NI UN MOT — c'est l'alphabet du lecteur. Et
    # il compte : trier `skill_choice.from[]` canoniquement mettrait le menu du
    # Roublard français dans l'ordre anglais, exactement comme trier les
    # patches par adresse mettait « Cuirasse » avant « Armure d'écailles ».
    # ⛔ Ils sont DÉCLARÉS pour qu'un cinquième casse ici : un champ qui se met
    # à porter des adresses sans qu'on l'ait décidé est le vrai danger.
    #
    # ⚠️ `gear.contents` (les sept paquetages) est le CINQUIÈME, et il est entré
    # ici en FAISANT CASSER cette ligne — c'est exactement ce qu'elle est là
    # pour faire. Il n'y entre PAS pour son ordre : chaque élément porte les
    # mots du livre français (`text`, `name`, `unit`) À CÔTÉ de l'adresse
    # anglaise (`ref`), donc la liste diffère de l'anglaise par ses mots et
    # emporte ses adresses avec elle. ✅ Mesuré juste au-dessus : `adresses` est
    # vide, donc les `ref` sont bien anglaises — la référence a suivi la
    # migration, elle ne l'a pas manquée. Voir `src/gear_packs.py`.
    ORDRE_DU_LECTEUR = {
        "class.weapon_proficiency_ids", "class.skill_choice",
        "class.weapon_mastery_from", "background.skill_ids",
        "gear.contents",
    }
    neufs = sorted(ordres - ORDRE_DU_LECTEUR)
    assert not neufs, (
        "un champ de patch s'est mis à porter des adresses sans être déclaré — "
        "%s. Soit c'est l'ordre du lecteur français et il se déclare ici, soit "
        "c'est une référence qui n'a pas suivi : REGARDER, pas ajouter." % neufs)
    perimes = sorted(ORDRE_DU_LECTEUR - ordres)
    assert not perimes, (
        "%s ne porte plus d'adresse — la déclaration lui survit, et une ligne "
        "périmée est ce qui masque la suivante." % perimes)

    print("  ok  aucun patch français ne porte de clef ni d'adresse française ; "
          "quatre champs gardent l'ordre du lecteur, déclarés")


def acceptance_le_garde_mord_sur_un_patch_fabrique():
    """⭐ UN GARDE QU'ON N'A PAS VU MORDRE NE MORD PAS.

    ⛔ Éprouvé sur un patch FABRIQUÉ, jamais en salissant les exports : poser
    une fausse clef dans `exports/` pour se prouver qu'on sait la voir serait
    la même faute que poser un faux export chez le voisin.
    """
    def inspecte(patch):
        fautes, adresses = [], []
        for champ, valeur in patch["data"].items():
            if champ.endswith(("_key", "_keys")) or champ in FAMILLES_DE_CLEFS:
                fautes.append(champ)
            if ":fr:" in json.dumps(valeur, ensure_ascii=False):
                adresses.append(champ)
        return fautes, adresses

    propre = {"id": "srd:weapon:en:longsword", "data": {"name": "Épée longue"}}
    assert inspecte(propre) == ([], [])

    avec_clef = {"id": "srd:weapon:en:longsword",
                 "data": {"name": "Épée longue", "damage_type_key": "tranchant"}}
    assert inspecte(avec_clef)[0] == ["damage_type_key"], inspecte(avec_clef)

    # ⭐ ET LE TÉMOIN EST UNE ADRESSE FRANÇAISE, pas n'importe quelle adresse :
    # c'est la seule qui soit une faute. Une adresse anglaise dans une liste
    # ordonnée à la française est légitime, et le test au-dessus la déclare.
    avec_adresse = {"id": "srd:class:en:rogue",
                    "data": {"skill_choice": {"from": [FR("skill", "discretion")]}}}
    assert inspecte(avec_adresse)[1] == ["skill_choice"], inspecte(avec_adresse)
    anglaise = {"id": "srd:class:en:rogue",
                "data": {"skill_choice": {"from": ["srd:skill:en:stealth"]}}}
    assert inspecte(anglaise) == ([], []), inspecte(anglaise)
    print("  ok  le garde mord : une clef et une adresse fabriquées sont vues")


def main():
    unit_the_scalar_families()
    unit_spell_classes_by_occurrence()
    unit_lineages_by_their_spells()
    unit_resource_columns_by_their_series()
    unit_monster_abilities_by_value()
    acceptance_no_french_key_survives()
    acceptance_un_patch_francais_ne_porte_que_des_mots()
    acceptance_le_garde_mord_sur_un_patch_fabrique()
    print("PASS test_key_families")


if __name__ == "__main__":
    main()
