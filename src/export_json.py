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
import correspond
import db

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXPORTS = os.path.join(ROOT, "exports")

GENERATED_NOTICE = (
    "GENERATED FILE — DO NOT EDIT. Produced by the fh-srd importer "
    "(~/tools/fh-srd, branch srd/base-v1). Editing this copy is a silent "
    "no-op: the next sync overwrites it. Fix the importer, rebuild, re-export, "
    "then sync. Integrity: exports/MANIFEST.json."
)


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
    """The correspondence files this run will write, relative to the export root."""
    return {"%s/correspondence.json" % layer for layer in _bilingual_layers(conn)}


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
        path = os.path.join(out_dir, grp["layer"], grp["lang"], grp["kind"] + ".json")
        manifest_files.append(_write(path, payload, out_dir))
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
        result = correspond.correspond_all(seen.get(layer, {}))
        payload = {
            "$generated": GENERATED_NOTICE,
            "$schema_version": 1,
            "layer": layer,
            "license": layer_row["license"],
            "license_url": layer_row["license_url"],
            "import_run": run_id,
            "$note": (
                "COMPUTED, NOT EXTRACTED. Each pair is a fingerprint that was "
                "unique on both sides; `pending` holds every record the data "
                "did not decide, named rather than guessed. Nothing here "
                "modifies the catalogues it points at."
            ),
        }
        payload.update(result)
        manifest_files.append(
            _write(os.path.join(out_dir, layer, "correspondence.json"),
                   payload, out_dir)
        )

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
