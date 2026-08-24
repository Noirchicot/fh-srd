"""La couche française reconstituée : record anglais + conversion + patch.

🔴 UN SEUL ENDROIT SAIT COMMENT LE FRANÇAIS SE RELIT. Après la transition à
froid, `exports/srd/fr/*.json` ne porte plus de records : il porte des PATCHES,
posés sur les adresses anglaises. Le site, les tests et n'importe quel lecteur
doivent donc reconstituer — et s'ils le faisaient chacun de leur côté, ils
divergeraient exactement comme deux copies d'une même liste divergent toujours.

⭐ Ce module EST cette lecture. `load(exports_dir, lang, kind)` rend des records
complets, quelle que soit la forme du fichier — un catalogue anglais se rend tel
quel, un patch français se reconstitue.
"""

import copy
import json
import os


def _conversions(exports_dir):
    """La table dérivée, lue une fois. ⛔ Jamais recalculée ici : elle est
    produite par l'import, avec sa provenance, et ce fichier ne fait que la
    consulter."""
    path = os.path.join(exports_dir, "conversions.json")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)["fields"]


def _rebuild_french(patches, english, table):
    """Reconstitue les records français depuis l'anglais + le patch + la table.

    🔴 C'EST ICI QUE LA LOI §0.13 DEVIENT VISIBLE. Il n'y a plus qu'un jeu de
    records, adressés en anglais ; le français est ce qu'on pose dessus. Trois
    couches, et l'ordre compte :

      ① le RECORD anglais           — la structure, les clefs, les nombres
      ② la CONVERSION               — un nombre français se RECALCULE
      ③ le PATCH                    — un mot français se PREND dans le livre

    ⭐ ET LE PATCH PASSE EN DERNIER, exprès : si un jour une valeur convertie
    devait aussi être un mot (le livre français écrivant autre chose qu'une
    simple conversion), c'est le livre qui gagnerait, pas la table.

    ⚠️ Une adresse ADOPTÉE n'a pas de record anglais derrière elle — le livre
    anglais imprime le terme mais ne lui donne pas d'entrée. Sa base est donc
    vide et le patch porte tout. C'est prévu, pas un cas dégénéré.
    """
    out = []
    for patch in patches:
        base = english.get(patch["id"])
        data = copy.deepcopy(base["data"]) if base else {}

        # ② les conversions, AVANT le patch
        for champ, valeur in list(data.items()):
            fr = (table.get(champ) or {}).get(valeur) if isinstance(valeur, str) else None
            if fr is not None:
                data[champ] = fr

        # ③ les mots du livre français
        data.update(patch["data"])

        rec = copy.deepcopy(base) if base else {}
        rec.update({
            "id": patch["id"],
            "lang": "fr",
            "name": patch["name"],
            "data": data,
        })
        for champ in ("license", "attribution", "source_id", "source_locator",
                      "srd_version", "content_hash"):
            if champ in patch:
                rec[champ] = patch[champ]
        rec.setdefault("kind", (base or {}).get("kind"))
        rec.setdefault("slug", patch["id"].split(":")[-1])
        out.append(rec)
    return out


def load(exports_dir, lang, kind):
    """Les records d'un (langue, genre), reconstitués si besoin.

    ⛔ Un fichier qui ne porte NI `records` NI `patches` n'est pas un fichier
    vide : c'est une forme qu'on ne connaît pas. On refuse.
    """
    with open(os.path.join(exports_dir, lang, kind + ".json"), "r",
              encoding="utf-8") as fh:
        payload = json.load(fh)
    if "records" in payload:
        return payload["records"]
    if "patches" not in payload:
        raise KeyError(
            "%s/%s.json ne porte ni `records` ni `patches` — forme inconnue, "
            "rien n'est lu." % (lang, kind))
    with open(os.path.join(exports_dir, "en", kind + ".json"), "r",
              encoding="utf-8") as fh:
        english = {r["id"]: r for r in json.load(fh)["records"]}
    return _rebuild_french(payload["patches"], english, _conversions(exports_dir))
