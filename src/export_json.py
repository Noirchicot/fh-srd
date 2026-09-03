"""SQLite -> static JSON exports, plus the manifest that keeps them honest.

The FHPC never talks to a database from a browser. It reads these files.

Which creates a known hazard, and it is worth naming rather than discovering
again: a file published under `fh-phb/docs/` whose source lives in *another*
repository is a generated artefact. Patch the copy and the next sync reverts
your fix, quietly, while the tests still pass because they read the reverted
file. That is exactly how a deployed bugfix was lost on 2026-08-02.

Two mechanisms, because one of them only warns:

  * a `$generated` header in every file, naming this repository — tells a human
    reading the file not to edit it;
  * `exports/MANIFEST.json`, carrying the sha256 of every export — lets the
    consuming side *check*. A hand-edited copy fails the check loudly at sync
    time instead of being silently overwritten six weeks later.

The header is the warning. The manifest is the catch.
"""

import json
import os

import canon
import adopted_addresses
import convert_units
import correspond
import pair_traits
import db
import shelving

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXPORTS = os.path.join(ROOT, "exports")
# The one hand-edited input besides sources.lock.json: the correspondence
# decisions a person signed. Absent is not an error — it means nobody has signed
# anything yet, which is a true state and a common one.
SIGNED = os.path.join(ROOT, "sources", "correspondence-signed.json")
# The second hand-written input: pairings READ in both directions. Kept apart
# from the signed file so a reading is never mistaken for Eric's signature.
READING = os.path.join(ROOT, "sources", "correspondence-read.json")

GENERATED_NOTICE = (
    "GENERATED FILE — DO NOT EDIT. Produced by the fh-srd importer "
    "(~/tools/fh-srd, branch srd/base-v1). Editing this copy is a silent "
    "no-op: the next sync overwrites it. Fix the importer, rebuild, re-export, "
    "then sync. Integrity: exports/MANIFEST.json."
)


# ---------------------------------------------------------------------------
# What a layer publishes BESIDE its records
# ---------------------------------------------------------------------------
# A record answers "where is THIS object". It cannot answer "what are all the
# places an object could be" — group 416 records by shelf and you recover the
# twenty-six shelves that hold something, never the thirty that exist. Four
# shelves and one whole aisle are declared, empty, and waiting; grouping can
# never produce a zero.
#
# So the block is computed by the module that OWNS the classification and
# merged into that file's header. ⛔ Not written per record: the same structure
# copied onto 416 rows is the same value in 416 places, which is how a value
# starts disagreeing with itself. ⛔ Not a new export file and not a new genre
# either — both are refused downstream by name (`gen-srfh-layer.mjs` stops on
# an `srfh/en/*.json` nobody declared, and opening a genre to the `fh-layer/1`
# contract DISARMS one of the four gates of `gen-srd-layer.mjs`). A header key
# on a file that is already declared costs neither.
EXTRA_BLOCKS = {("srfh", "shelving"): shelving.declared_structure}


def _write(path, payload, base):
    """Write canonical JSON and return (path relative to `base`, sha256, bytes).

    Paths are relative to the EXPORT ROOT, never to this repository. That is
    not cosmetic: the manifest has to verify the tree after it has been copied
    into `fh-phb/docs/`, where the repo-relative path is meaningless. A
    manifest that only validates in its birthplace validates nothing.

    LF endings and a trailing newline are explicit rather than inherited from
    the platform: an export produced on another machine must be byte-identical
    or the manifest is worthless.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = canon.canonical_json(payload, indent=2) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return (
        os.path.relpath(path, base).replace(os.sep, "/"),
        canon.sha256_text(text),
        len(text.encode("utf-8")),
    )


def _source_block(conn, source_id):
    if not source_id:
        return None
    row = conn.execute("SELECT * FROM source WHERE id = ?", (source_id,)).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "title": row["title"],
        "publisher": row["publisher"],
        "version": row["version"],
        "lang": row["lang"],
        "url": row["url"],
        "sha256": row["sha256"],
        "license": row["license"],
        "license_url": row["license_url"],
        "attribution": row["attribution"],
    }



_SLUG_FR = __import__("re").compile(r"^([a-z-]+):([a-z0-9-]+)$")


def _readresse_fr(valeur):
    """`gear:acide` → l'adresse du record français dans la base de travail.

    🔴 LES FICHIERS D'ENTRÉE NE PORTENT PLUS D'ADRESSE FRANÇAISE, ET C'EST
    VOULU : après la transition à froid, l'adresse française n'existe plus, et
    écrire une adresse morte comme si elle vivait serait un mensonge tranquille.
    Ils portent le **mot du livre** — `<genre>:<slug>` — et c'est ce qui rend la
    signature d'Eric encore lisible PAR ERIC.

    ⛔ CE N'EST PAS UNE TABLE D'ALIAS. Rien ne résout par elle à l'exécution :
    elle sert UNE fois, ici, à retrouver le record français dans la base de
    travail — qui est un artefact gitignoré, jamais publié. C'est précisément
    ce qui permet aux routes de correspondance de CONTINUER À TOURNER au lieu
    de se figer en table non vérifiable.
    """
    if isinstance(valeur, str):
        m = _SLUG_FR.match(valeur)
        return "srd:%s:fr:%s" % (m.group(1), m.group(2)) if m else valeur
    if isinstance(valeur, list):
        return [_readresse_fr(v) for v in valeur]
    if isinstance(valeur, dict):
        return {k: (_readresse_fr(v) if k in ("fr", "id") else v)
                for k, v in valeur.items()}
    return valeur


def read_signed(path=SIGNED):
    """Load the signed decisions, or an empty set if the file is not there.

    ⚠️ A missing file and an unreadable one are NOT the same thing. Nobody has
    signed anything is a fact; a file that exists and will not parse is a typo
    somebody made, and swallowing it would silently drop every decision they
    thought they had recorded.
    """
    if not os.path.exists(path):
        return dict(correspond.SIGNED_TEMPLATE)
    with open(path, "r", encoding="utf-8") as fh:
        try:
            signed = json.load(fh)
        except ValueError as exc:
            raise correspond.CorrespondenceError(
                "%s exists but is not valid JSON (%s).\n\n"
                "Refusing rather than treating it as empty: an unparseable file "
                "is a mistake in it, not an absence of decisions. Nothing was "
                "written." % (path, exc)
            )
    return {"pairs": _readresse_fr(signed.get("pairs", [])),
            "no_equivalent": _readresse_fr(signed.get("no_equivalent", []))}


def read_reading(path=READING):
    """The two-directional readings, or an empty pair of maps if absent.

    Same rule as `read_signed`: absent is a fact, unparseable is a mistake.
    """
    if not os.path.exists(path):
        return dict(correspond.READING_TEMPLATE)
    with open(path, "r", encoding="utf-8") as fh:
        try:
            reading = json.load(fh)
        except ValueError as exc:
            raise correspond.CorrespondenceError(
                "%s exists but is not valid JSON (%s). Refusing rather than "
                "treating it as empty." % (path, exc))
    # ⚠️ LES DEUX SENS NE SE RÉ-ADRESSENT PAS AU MÊME ENDROIT : le français est
    # la CLEF dans un sens et la VALEUR dans l'autre. Traiter les deux dicts
    # pareil réécrirait des adresses anglaises et laisserait des slugs français
    # — et la lecture aller-retour cesserait de tomber d'accord, ce qui ferait
    # refuser 322 paires justes. C'est le genre d'erreur qui s'annonce comme un
    # défaut de données.
    return {"fr_to_en": {_readresse_fr(k): v
                         for k, v in reading.get("fr_to_en", {}).items()},
            "en_to_fr": {k: _readresse_fr(v)
                         for k, v in reading.get("en_to_fr", {}).items()}}


def _bilingual_layers(conn):
    """Layers holding records in more than one language, and their languages.

    Read from the DATA, never from a constant. The failure this avoids is the
    one `gen-srd-layer.mjs` walked into downstream: it iterates over its own
    hardcoded genre list, so a genre the catalogue gained is not refused, it is
    silently never read. A list of languages frozen in code here would do the
    same thing to a language.
    """
    rows = conn.execute(
        "SELECT DISTINCT layer, lang FROM record ORDER BY layer, lang"
    ).fetchall()
    by_layer = {}
    for row in rows:
        by_layer.setdefault(row["layer"], []).append(row["lang"])
    return {layer: langs for layer, langs in by_layer.items() if len(langs) > 1}


def correspondence_paths(conn):
    """Les fichiers HORS CATALOGUE que cette passe écrira, relatifs à `exports/`.

    🔴 CETTE FONCTION EST LA MÉMOIRE DE `check_no_orphans`, ET ELLE S'OUBLIE
    FACILEMENT. Le lot 104 a ajouté `conversions.json` sans l'inscrire ici :
    la première passe l'a écrit sans broncher (le fichier n'existait pas encore,
    donc aucun orphelin), et **la passe SUIVANTE a refusé tout l'export** en le
    nommant « STALE EXPORT ». ⭐ Le garde a mordu au bon moment et il a refusé
    d'exporter à moitié — mais un artefact commité qu'on ne sait plus produire
    aurait vécu une passe entière.

    ⚠️ Un artefact de plus dans `export_all` DOIT s'inscrire ici dans le même
    geste. Ce n'est pas une liste de commodité : c'est ce qui distingue « ce
    fichier est prévu » de « ce fichier traîne ».
    """
    layers = _bilingual_layers(conn)
    return ({"%s/correspondence.json" % layer for layer in layers}
            | {"%s/conversions.json" % layer for layer in layers})


class OrphanExportError(RuntimeError):
    """`out_dir` holds a .json export this run would not have written."""


def _existing_json(out_dir):
    """Every .json already under `out_dir`, relative and slash-separated."""
    found = set()
    for base, _dirs, names in os.walk(out_dir):
        for name in names:
            if not name.endswith(".json"):
                continue
            full = os.path.join(base, name)
            found.add(os.path.relpath(full, out_dir).replace(os.sep, "/"))
    return found


def check_no_orphans(conn, out_dir):
    """Refuse to export over a tree holding a file this run would not write.

    THE FAILURE THIS CLOSES, which happened here on 2026-08-08: four parsers
    stopped returning records, so `export_all` stopped writing
    `srd/{en,fr}/weapon.json` and `srd/{en,fr}/armor.json` — and the PREVIOUS
    versions of those four files stayed exactly where they were. The export
    directory then described a base that no longer existed. `ls` showed 29
    files. `diff -rq` against a reference tree showed no missing file. The
    manifest was rewritten without them, so nothing cross-checked them either:
    `verify_manifest` only asks "is every file I listed still intact", never
    "is there a file here I did not list".

    A stale export is worse than a missing one. A missing file is an error at
    the consuming end; a stale file is an answer, and a wrong one.

    THIS REFUSES RATHER THAN DELETES, and the choice is deliberate. Deleting
    would make the build green again by removing the evidence, which is the
    same shape of problem one layer down. A genre leaving the catalogue is a
    decision — it means the SRD stopped carrying something, or a parser was
    retired — and a decision should be made by a person and land in a commit,
    not be inferred from an empty query result. Removing the file is one
    `git rm`; the refusal names it and says so.

    ONLY `.json` IS CONSIDERED. `exports/README.md` is written by hand and is
    not a generated artefact; sweeping it in would make this guard a nuisance,
    and a nuisance guard gets switched off.
    """
    groups = conn.execute(
        "SELECT DISTINCT layer, lang, kind FROM record ORDER BY layer, lang, kind"
    ).fetchall()
    expected = {"MANIFEST.json", "exclusions.json"}
    # The correspondence files are written by this run too. Leaving them out
    # would make the guard refuse the very tree it just produced.
    expected |= correspondence_paths(conn)
    for grp in groups:
        expected.add("%s/%s/%s.json" % (grp["layer"], grp["lang"], grp["kind"]))

    orphans = sorted(_existing_json(out_dir) - expected)
    if not orphans:
        return
    raise OrphanExportError(
        "%d export file(s) in %s would be left untouched by this run:\n%s\n\n"
        "This run writes %d file(s); the ones above are not among them, so after "
        "exporting they would still describe a base that no longer exists — and "
        "they would be missing from MANIFEST.json, which only verifies the files "
        "it lists and never notices an extra one. Nothing has been exported.\n"
        "If the genre is genuinely gone, delete the file and commit that; it is a "
        "decision, not a side effect."
        % (len(orphans), out_dir, "\n".join("  " + o for o in orphans),
           len(expected))
    )


#: Ce qu'un patch porte TOUJOURS, même identique à l'anglais : sans eux le
#: record français cesserait de pouvoir citer sa source, et « un record SRD qui
#: ne peut pas citer sa source n'est pas un record SRD ».
_PATCH_ALWAYS = ("license", "attribution", "source_id", "source_locator",
                 "srd_version", "content_hash")


def _sans_adresse_fr(valeur):
    """Remplace toute adresse française par `<genre>:<slug>`, à toute profondeur.

    🔴 POURQUOI LA CORRESPONDANCE NE PEUT PLUS PUBLIER D'ADRESSES FRANÇAISES :
    après la transition à froid, l'adresse française **n'existe plus**. Écrire
    une adresse morte comme si elle vivait serait un mensonge tranquille — et
    la preuve la plus courte du lot (`git grep 'srd:…:fr:'` à zéro) le dirait.

    ⭐ MAIS LA PROVENANCE, ELLE, DOIT SURVIVRE : c'est elle qui dit COMMENT
    chaque paire a été trouvée, et 90 d'entre elles portent la signature
    d'Eric. On garde donc `<genre>:<slug>` — le slug est **un mot du livre**,
    pas une adresse. ⛔ Ce n'est pas une table d'alias : rien ne résout par
    elle à l'exécution, elle ne fait que porter la mémoire du joint.
    """
    if isinstance(valeur, str):
        return _ID_FR.sub(lambda m: ":".join(m.group(0).split(":")[1::2]), valeur)
    if isinstance(valeur, list):
        return [_sans_adresse_fr(v) for v in valeur]
    if isinstance(valeur, dict):
        return {k: _sans_adresse_fr(v) for k, v in valeur.items()}
    return valeur


_ID_FR = __import__("re").compile(r"\bsrd:[a-z-]+:fr:[a-z0-9-]+\b")


def _readdress(valeur, vers):
    """Réécrit toute ADRESSE FRANÇAISE trouvée dans une valeur, à toute profondeur.

    ⭐ CE SONT LES 544 RÉFÉRENCES CROISÉES, et elles « suivent mécaniquement » —
    mais pas toutes seules. `class.weapon_proficiency_ids[]` porte des adresses
    françaises DANS sa valeur ; sans cette réécriture elles entraient telles
    quelles dans le patch, et le grep n'aurait jamais rendu zéro.

    ⭐ ET LA CONSÉQUENCE EST JOLIE : une fois réadressée, la référence devient
    IDENTIQUE à celle du record anglais — donc elle cesse de « différer », donc
    elle sort du patch d'elle-même. Elle ne se décide pas, elle se dérive : c'est
    exactement ce que le §4.2 annonçait, à condition de le faire AVANT de
    comparer.
    """
    if isinstance(valeur, str):
        return _ID_FR.sub(lambda m: vers.get(m.group(0), m.group(0)), valeur)
    if isinstance(valeur, list):
        return [_readdress(v, vers) for v in valeur]
    if isinstance(valeur, dict):
        return {k: _readdress(v, vers) for k, v in valeur.items()}
    return valeur


def _to_patch(payload, joint, english_records):
    """Un catalogue français devient un PATCH sur les adresses anglaises.

    ⛔ RIEN NE SE MIGRE SANS SA PAIRE. Un record français sans vis-à-vis et sans
    adresse adoptée ARRÊTE la construction et se fait NOMMER — il ne se
    rapproche pas « par ressemblance de nom », qui est la pire des preuves.

    ⭐ Le patch ne porte que ce qui DIFFÈRE. Un champ identique des deux côtés
    n'est pas un mot français, c'est le record : le recopier ferait de la couche
    un embranchement, ce qu'on est précisément en train de défaire.
    """
    pairs = joint["pairs"]
    table = joint["table"]
    par_id = {r["id"]: r for r in english_records}
    # La carte complète des réadressages : les paires prouvées, plus les trois
    # adresses adoptées du livre anglais.
    vers = dict(joint["toutes_paires"])
    vers.update(adopted_addresses.ADOPTED)

    patches, orphelins = [], []
    for rec in payload["records"]:
        cible = pairs.get(rec["id"]) or adopted_addresses.ADOPTED.get(rec["id"])
        if cible is None:
            orphelins.append(rec["name"])
            continue
        adopte = rec["id"] in adopted_addresses.ADOPTED
        anglais = par_id.get(cible)
        base = (anglais or {}).get("data") or {}

        # ⛔ RÉADRESSER AVANT DE COMPARER. Une référence croisée encore
        # française « diffère » toujours de l'anglaise, donc elle entrerait dans
        # le patch et le grep ne rendrait jamais zéro. Réadressée, elle devient
        # identique et disparaît d'elle-même.
        data_fr = _readdress(rec["data"], vers)
        mots = {}
        for champ in sorted(set(data_fr) | set(base)):
            va, vb = data_fr.get(champ), base.get(champ)
            if va == vb:
                continue
            # ⛔ Une conversion pure N'ENTRE PAS dans le patch : elle se dérive
            # de `conversions.json` au rendu. ⚠️ Sauf pour une adresse ADOPTÉE,
            # qui n'a pas de record anglais derrière elle — il n'y a rien à
            # convertir depuis, donc la valeur française reste le seul texte.
            if not adopte and convert_units.is_pure_conversion(vb):
                continue
            mots[champ] = va

        patch = {"id": cible, "name": rec["name"], "data": mots}
        if adopte:
            patch["adopted"] = adopted_addresses.PROVENANCE
        for champ in _PATCH_ALWAYS:
            if rec.get(champ) is not None:
                patch[champ] = rec[champ]
        patches.append(patch)

    if orphelins:
        raise correspond.CorrespondenceError(
            "%d record(s) français sans paire NI adresse adoptée — %s. Rien ne "
            "se migre sans sa paire : une adresse devinée par ressemblance de "
            "nom serait fausse sans que rien ne le dise. Refusé, pas rapproché."
            % (len(orphelins), ", ".join(sorted(orphelins)[:8])))

    # ⛔ ON NE RETRIE PAS PAR L'ADRESSE ANGLAISE. Le patch garde l'ordre dans
    # lequel les records français sont arrivés — c'est-à-dire l'ordre du SLUG
    # FRANÇAIS, donc à peu près l'alphabet du lecteur français.
    # 🔴 MESURÉ EN LE CASSANT : trier par `id` mettait « Cuirasse » avant
    # « Armure d'écailles » sur la page française. Le contenu était intact, mais
    # un lecteur francophone ne trouve plus rien. ⭐ Un ORDRE appartient à
    # l'interface, pas au moteur — c'est la même loi §0.13, vue par l'autre bout.
    out = {k: v for k, v in payload.items() if k not in ("records", "count")}
    out["$note"] = (
        "PATCH, NOT RECORDS. The French layer stopped being a BRANCH: there is "
        "one set of records, addressed in English, and this file lays the "
        "French WORDS on top of them. Each entry carries only what DIFFERS from "
        "the English record — a field identical on both sides is not a French "
        "word, it is the record. ⛔ Converted numbers are NOT here: a French "
        "word is taken from the book, a French number is RECOMPUTED, and it is "
        "derived at render time from conversions.json. Law §0.13: the engine "
        "produces identifiers, the interface produces words."
    )
    out["count"] = len(patches)
    out["patches"] = patches
    return out


def export_all(conn, out_dir=EXPORTS):
    """One file per (layer, lang, kind), plus the exclusion register.

    Split by layer first, so shipping only the SRD is a matter of shipping the
    `srd/` directory — not of filtering records at the last minute, which is
    the kind of step that gets skipped once.

    Refuses BEFORE writing anything if the tree holds an export this run would
    not produce (see `check_no_orphans`), so a refusal leaves the directory
    exactly as it found it rather than half-rewritten.
    """
    check_no_orphans(conn, out_dir)

    run = conn.execute("SELECT * FROM import_run LIMIT 1").fetchone()
    run_id = run["id"] if run else None
    manifest_files = []
    # (layer, kind) -> {lang: [records]}, kept for the correspondence pass
    # below. Accumulated here rather than re-queried so the pairing sees
    # exactly the records that were exported, not a second reading of the
    # table that could differ.
    seen = {}
    # Les fichiers de catalogue, préparés mais PAS écrits : voir plus bas.
    # `(path, payload, layer, lang, kind)`.
    differes = []
    # Ce que la passe de correspondance produit, et dont l'écriture dépend :
    # `layer -> {"pairs": ..., "table": ...}`.
    joint = {}

    groups = conn.execute(
        "SELECT DISTINCT layer, lang, kind FROM record ORDER BY layer, lang, kind"
    ).fetchall()

    for grp in groups:
        rows = conn.execute(
            """SELECT * FROM record
               WHERE layer = ? AND lang = ? AND kind = ?
               ORDER BY id""",
            (grp["layer"], grp["lang"], grp["kind"]),
        ).fetchall()

        records = []
        for row in rows:
            records.append(
                {
                    "id": row["id"],
                    "layer": row["layer"],
                    "kind": row["kind"],
                    "lang": row["lang"],
                    "slug": row["slug"],
                    "name": row["name"],
                    "data": json.loads(row["data"]),
                    "content_hash": row["content_hash"],
                    # Attribution rides on the RECORD, not only on the file.
                    # A record pasted into a wiki, a VTT or a chat message still
                    # says who wrote it and under what licence. That redundancy
                    # is the point, not an oversight.
                    "license": row["license"],
                    "attribution": row["attribution"],
                    "source_id": row["source_id"],
                    "source_locator": row["source_locator"],
                    "srd_version": row["srd_version"],
                }
            )

        layer_row = conn.execute(
            "SELECT * FROM layer WHERE id = ?", (grp["layer"],)
        ).fetchone()

        payload = {
            "$generated": GENERATED_NOTICE,
            "$schema_version": 1,
            "layer": grp["layer"],
            "layer_label": layer_row["label"],
            "layer_origin": layer_row["origin"],
            "cc_by_srd": bool(layer_row["cc_by_srd"]),
            "lang": grp["lang"],
            "kind": grp["kind"],
            "license": layer_row["license"],
            "license_url": layer_row["license_url"],
            "import_run": run_id,
            "source": _source_block(conn, rows[0]["source_id"]) if rows else None,
            "count": len(records),
            "records": records,
        }
        extra = EXTRA_BLOCKS.get((grp["layer"], grp["kind"]))
        if extra is not None:
            block = extra(records)
            # A block that lands on a key the header already carries would
            # replace it silently, and the loser would be the one the whole
            # pipeline depends on (`count`, `records`, the licence). Refuse.
            clash = sorted(set(block) & set(payload))
            if clash:
                raise RuntimeError(
                    "the extra block for %s/%s would overwrite header key(s) "
                    "%s. Nothing was exported."
                    % (grp["layer"], grp["kind"], ", ".join(clash)))
            payload.update(block)

        # ⛔ ON N'ÉCRIT PAS ENCORE. La correspondance décide à quelle ADRESSE le
        # français s'écrit, et elle se calcule plus bas, sur `seen`. Écrire ici
        # produirait les fichiers français à leur ancienne adresse, puis il
        # faudrait les réécrire — et un fichier écrit deux fois dans la même
        # passe est exactement ce que `check_no_orphans` ne peut plus garder.
        path = os.path.join(out_dir, grp["layer"], grp["lang"], grp["kind"] + ".json")
        differes.append((path, payload, grp["layer"], grp["lang"], grp["kind"]))
        seen.setdefault(grp["layer"], {}).setdefault(grp["kind"], {})[grp["lang"]] = records

    # The exclusion register ships too. What was left out, and why, is part of
    # the deliverable — not a note in somebody's chat history.
    exclusions = [
        dict(row)
        for row in conn.execute("SELECT * FROM exclusion ORDER BY reason, id")
    ]
    manifest_files.append(
        _write(
            os.path.join(out_dir, "exclusions.json"),
            {
                "$generated": GENERATED_NOTICE,
                "$schema_version": 1,
                "import_run": run_id,
                "count": len(exclusions),
                "records": exclusions,
            },
            out_dir,
        )
    )

    # The correspondence between the languages — a THIRD artefact, written
    # beside the catalogues and never merged into them. What was extracted
    # verbatim under CC-BY has to stay distinguishable from what was computed
    # here, and the pairs a human still has to arbitrate have to stay
    # distinguishable from the ones the data decided on its own.
    for layer, langs in sorted(_bilingual_layers(conn).items()):
        if sorted(langs) != ["en", "fr"]:
            # Two languages this pass was not calibrated for. Refusing beats
            # writing a file that claims to pair them.
            raise correspond.CorrespondenceError(
                "layer %r carries languages %s; the correspondence pass is "
                "calibrated for en/fr only. Nothing was written for it."
                % (layer, ", ".join(sorted(langs)))
            )
        layer_row = conn.execute(
            "SELECT * FROM layer WHERE id = ?", (layer,)
        ).fetchone()
        result = correspond.correspond_all(seen.get(layer, {}),
                                           signed=read_signed(),
                                           reading=read_reading())
        payload = {
            "$generated": GENERATED_NOTICE,
            "$schema_version": 1,
            "layer": layer,
            "license": layer_row["license"],
            "license_url": layer_row["license_url"],
            "import_run": run_id,
            "$note": (
                "COMPUTED, NOT EXTRACTED. Every pair says HOW it was reached "
                "in its `by` field, and the three ways are not equally strong: "
                "`structured-fingerprint/N` is a fingerprint the data made "
                "unique on both sides, `transitive/<genre>.<field>` is deduced "
                "by following an already-proven pair, and `human` is signed in "
                "sources/correspondence-signed.json. `no_equivalent` is a "
                "person's finding that a record has no counterpart at all — a "
                "closed question, not an open one. `pending` is what nobody "
                "has settled, `refusals` what was offered and rejected. "
                "Nothing here modifies the catalogues it points at."
            ),
        }
        payload.update(_sans_adresse_fr(result))
        manifest_files.append(
            _write(os.path.join(out_dir, layer, "correspondence.json"),
                   payload, out_dir)
        )

        # ---- LA CONVERSION D'UNITÉS — un QUATRIÈME artefact ----------------
        # ⭐ Elle se DÉRIVE des paires que la passe ci-dessus vient de prouver,
        # elle ne s'écrit nulle part. C'était déjà la donnée française : chaque
        # paire porte une valeur anglaise et sa valeur française, il suffit de
        # les lire. Elle garde donc LES ARRONDIS DU LIVRE (`9 m` pour 30 pieds,
        # qui en font 9,144) et jamais un produit recalculé.
        #
        # 🔴 POURQUOI ELLE EST À PART DES CATALOGUES, comme la correspondance :
        # une conversion N'EST PAS UNE TRADUCTION. Un mot français se prend
        # dans le livre ; un nombre français se recalcule. La loi §0.13 sépare
        # l'identifiant du mot — une unité n'est ni l'un ni l'autre, c'est un
        # RENDU, et un rendu n'appartient pas à la donnée.
        #
        # ⛔ `derive` REFUSE si une valeur anglaise en rend deux françaises :
        # la conversion cesserait d'être une fonction, et le site français
        # deviendrait faux sans que rien d'autre casse.
        paires_fr = {p["fr"]: p["en"] for p in result["pairs"]}
        # ⚠️ `pairs` sert à trouver l'adresse D'UN record ; `toutes_paires` sert
        # à réadresser les RÉFÉRENCES qu'il porte, qui pointent vers d'autres
        # genres. Ce sont les mêmes données, mais pas le même usage — les
        # confondre ferait qu'un genre ne saurait réadresser que vers lui-même.
        joint[layer] = {"pairs": paires_fr, "toutes_paires": paires_fr}
        table = convert_units.derive(
            [(p["fr"], p["en"]) for p in result["pairs"]],
            {lang: {r["id"]: r for kinds in seen.get(layer, {}).values()
                    for r in kinds.get(lang, [])}
             for lang in ("fr", "en")},
        )
        manifest_files.append(
            _write(
                os.path.join(out_dir, layer, "conversions.json"),
                {
                    "$generated": GENERATED_NOTICE,
                    "$schema_version": 1,
                    "layer": layer,
                    "import_run": run_id,
                    "$note": (
                        "DERIVED, NOT WRITTEN. Every line was read off a pair the "
                        "correspondence proved: the English value as the book prints "
                        "it, and the French value as the French book prints it. "
                        "Nothing is multiplied here — the table carries the BOOK's "
                        "rounding (9 m for 30 feet, which are 9.144), never a "
                        "recomputed product. A conversion is not a translation: a "
                        "French word is taken from the book, a French number is a "
                        "RENDERING. Keyed on (field, English value) — the narrowest "
                        "key that stays a function, so a new unit-bearing field is "
                        "refused by name instead of guessed."
                    ),
                    "count": len(table),
                    "fields": convert_units.as_export(table),
                },
                out_dir,
            )
        )
        joint[layer]["table"] = table

    # ══ LA TRANSITION À FROID — le français cesse d'avoir ses propres adresses
    #
    # 🔴 CE BLOC EST LE T4 ET LE T5 D'UN SEUL GESTE, et il ne peut pas être plus
    # haut : c'est la correspondance, calculée juste au-dessus, qui dit à quelle
    # adresse anglaise chaque record français s'écrit.
    #
    # ⭐ ET LA COUPURE N'EST PAS ENTRE `name`/`description` ET LE RESTE. Mesuré :
    # 6 080 valeurs françaises vivent hors de ces deux champs — toutes les
    # actions et tous les traits des 330 monstres, la rareté des 258 objets, le
    # temps d'incantation des 339 sorts. Un patch à deux champs aurait amputé le
    # livre français des deux tiers de son contenu.
    #
    # La coupure est entre un MOT et un NOMBRE CONVERTI :
    #   · un mot français se PREND dans le livre  → il entre dans le patch
    #   · un nombre français se RECALCULE         → il sort, et se dérive au rendu
    # ⚠️ ET ELLE SE DÉCIDE PAR VALEUR, JAMAIS PAR CHAMP : `monster.speed` vaut
    # `20 ft.` neuf fois et `30 ft., Fly 60 ft.` deux cents fois.
    # ══ LA CLEF DE TRAIT — une identité qui survit au changement de langue
    #
    # 🔴 LE DERNIER OBSTACLE avant « Fate's Hand en français », ratifié par Eric
    # le 2026-09-04 (« id hors langue = clé »). Un trait d'espèce vit DANS
    # `data.traits[]` : c'est un élément de tableau, pas un record, donc rien ne
    # l'apparie. Mesuré : 1 clef sur 33 coïncide entre les deux langues, et
    # c'est `brave` du Halfelin — un homographe, pas une paire.
    #
    # ⭐ CE QU'ON POSE EST UN `slug` NEUTRE, PAS UN `id` DÉPLACÉ. Il AJOUTE une
    # poignée au lieu d'en déplacer une : rien de ce qui cite un id existant ne
    # change de sens. Et il est lu tel quel par le consommateur — la grammaire
    # de chemins de `fhpc` apparie déjà un élément sur `id` OU `slug`.
    #
    # ⛔ ET IL EST DÉRIVÉ, JAMAIS TENU À LA MAIN : une table écrite une fois
    # diverge au premier rafraîchissement de la source sans que personne le
    # voie. Il se calcule ici, sur les records qui viennent d'être exportés.
    # La méthode, ses quatre signaux et ses refus : `src/pair_traits.py`.
    for layer, kinds in seen.items():
        par_langue = kinds.get("species") or {}
        if not par_langue.get("en") or not par_langue.get("fr"):
            continue
        poses = 0
        # Les noms des records DÉJÀ APPARIÉS, sous leur adresse COMMUNE. C'est
        # l'axe qui laisse un trait hériter d'une preuve qu'il n'a pas faite :
        # « Keen Senses » nomme Insight, Perception et Survival, « Sens
        # aiguisés » nomme Intuition, Perception et Survie, et ces trois-là sont
        # appariés depuis longtemps.
        # ⛔ Ici aussi le français porte encore ses adresses : sans la
        # correspondance, les deux langues tomberaient sous des clefs
        # différentes et cet axe ne rapprocherait jamais rien.
        vers_commun = dict((joint.get(layer) or {}).get("toutes_paires") or {})
        noms = {}
        for autre_kind, langues in kinds.items():
            for lang_nom, records_nom in langues.items():
                for r in records_nom:
                    adresse = vers_commun.get(r["id"], r["id"])
                    noms.setdefault(adresse, {})[lang_nom] = r.get("name")
        # ⚠️ À CE MOMENT DE LA PASSE, LE FRANÇAIS PORTE ENCORE SES PROPRES
        # ADRESSES : la transition à froid n'a lieu qu'à l'écriture, plus bas.
        # C'est donc la CORRESPONDANCE qui dit quel record français est lequel —
        # la même qui réadressera le catalogue quelques lignes plus loin.
        # ⛔ Une première version appariait sur `record_en["id"]` directement :
        # elle ne trouvait rien, ne levait rien, et posait ZÉRO clef en silence.
        vers_anglais = dict((joint.get(layer) or {}).get("toutes_paires") or {})
        par_id_fr = {}
        for r in par_langue["fr"]:
            par_id_fr[vers_anglais.get(r["id"], r["id"])] = r
        for record_en in par_langue["en"]:
            record_fr = par_id_fr.get(record_en["id"])
            traits_en = (record_en.get("data") or {}).get("traits") or []
            traits_fr = (record_fr.get("data") or {}).get("traits") or [] if record_fr else []
            if not traits_en or not traits_fr:
                continue
            try:
                clefs, _ = pair_traits.pair_species_traits(traits_en, traits_fr, noms)
            except pair_traits.TraitsNotPaired as refus:
                # ⛔ ON REFUSE L'EXPORT ENTIER, on ne note pas un regret. Une
                # clef posée sans preuve est indiscernable d'une clef prouvée :
                # personne, en aval, ne pourrait faire le tri. Et un export qui
                # sort avec une espèce muette laisserait la couche FH viser un
                # trait qu'elle ne trouvera pas — le refus tombe donc ici, où il
                # nomme encore l'espèce, plutôt qu'au montage de la pile.
                # Même geste que `UnknownLineage` dans `species_structure.py`.
                raise pair_traits.TraitsNotPaired(
                    "%s: %s. The export is refused rather than shipped with a "
                    "species whose traits carry no cross-language key."
                    % (record_en["id"], refus)
                )
            for trait in traits_en:
                trait["slug"] = trait["id"]        # l'anglais EST la clef neutre
            for trait in traits_fr:
                if trait["id"] in clefs:
                    trait["slug"] = clefs[trait["id"]]
            poses += len(traits_en) + len(clefs)

        # ⛔ UN BLOC QUI NE POSE RIEN NE SE TAIT PAS. La première version de
        # celui-ci n'a posé aucune clef sur 66 traits, sans lever, sans se
        # plaindre — l'export est sorti vert et muet. Un compte à zéro est donc
        # un échec, pas un cas limite.
        if poses == 0:
            raise pair_traits.TraitsNotPaired(
                "the trait-key pass matched %d species but stamped NOTHING; "
                "an export that carries no cross-language trait key is the very "
                "thing this pass exists to prevent" % len(par_langue["en"])
            )

    for path, payload, layer, lang, kind in differes:
        if lang == "fr" and layer in joint:
            payload = _to_patch(payload, joint[layer], seen[layer][kind].get("en", []))
        manifest_files.append(_write(path, payload, out_dir))

    manifest = {
        "$generated": GENERATED_NOTICE,
        "$schema_version": 1,
        "import_run": run_id,
        "pipeline_version": run["pipeline_version"] if run else None,
        "extractor": run["extractor"] if run else None,
        "cross_checker": run["cross_checker"] if run else None,
        "sources_lock_sha256": run["sources_lock_sha256"] if run else None,
        "files": [
            {"path": p, "sha256": h, "bytes": n}
            for (p, h, n) in sorted(manifest_files)
        ],
    }
    mpath = os.path.join(out_dir, "MANIFEST.json")
    os.makedirs(out_dir, exist_ok=True)
    mtext = canon.canonical_json(manifest, indent=2) + "\n"
    with open(mpath, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(mtext)
    return manifest


def verify_manifest(out_dir=EXPORTS):
    """Re-hash every export and compare against the manifest.

    This is what the FHPC sync should run on the copy it holds. It answers one
    question: is this file still the file the importer produced?
    """
    mpath = os.path.join(out_dir, "MANIFEST.json")
    with open(mpath, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    problems = []
    for entry in manifest["files"]:
        path = os.path.join(out_dir, entry["path"])
        if not os.path.exists(path):
            problems.append((entry["path"], "missing"))
            continue
        with open(path, "r", encoding="utf-8") as fh:
            actual = canon.sha256_text(fh.read())
        if actual != entry["sha256"]:
            problems.append((entry["path"], "modified"))
    return problems


if __name__ == "__main__":
    import sys

    conn = db.connect()
    try:
        manifest = export_all(conn)
    except OrphanExportError as exc:
        print("\nSTALE EXPORT\n%s" % exc, file=sys.stderr)
        sys.exit(5)
    print("exported %d files" % len(manifest["files"]))
    problems = verify_manifest()
    if problems:
        for path, why in problems:
            print("  %-50s %s" % (path, why))
        sys.exit(1)
    print("manifest verified")
