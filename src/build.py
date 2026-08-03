"""Build the canonical base: verify -> extract -> parse -> insert -> export.

Run:
    python3 src/build.py                 # every pinned, calibrated source
    python3 src/build.py --source X      # just one, for narrow debugging
    python3 src/build.py --fixture       # from tests/fixtures, no PDF needed

The fixture mode is not a toy. It exercises every stage except the PDF decode,
which means the determinism guarantee, the layer separation, the write guard
and the export manifest are all provable today, before the source is fetched.
When the PDF lands, only the decode stage is new.

ONE BASE, ONE RUN, HOWEVER MANY LANGUAGES. `import_run.sources_lock_sha256` is
already a hash of the WHOLE lock file (every pinned source, not just the one
being read -- see `sources.lock_hash()`), and `run_id` never took a source id
as an input. That was the tell that a "build" was always meant to mean
importing everything currently pinned and fetched into one coherent base, not
one source at a time -- it just had only one source to import when the French
spells were the only thing done. Building FR and EN separately, one overwrite
at a time, would leave `exports/MANIFEST.json` covering whichever language ran
last, silently dropping the other from the ledger that is supposed to prove
what shipped.
"""

import argparse
import json
import os
import sys

import canon
import db
import export_json
import extract
import parse_armor_en
import parse_armor_fr
import parse_backgrounds_en
import parse_backgrounds_fr
import parse_classes_en
import parse_classes_fr
import parse_feats_en
import parse_feats_fr
import parse_gear_en
import parse_gear_fr
import parse_glossary_en
import parse_glossary_fr
import parse_items_en
import parse_items_fr
import parse_monsters_en
import parse_monsters_fr
import parse_species_en
import parse_species_fr
import parse_spells
import parse_spells_en
import parse_tools_en
import parse_tools_fr
import parse_weapons_en
import parse_weapons_fr
import sources

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

FIXTURE_DIR = os.path.join(ROOT, "tests", "fixtures")

# (lang, kind) -> calibrated parser module. Each is calibrated against ONE
# language's real grammar (French puts the school before the level, English
# puts the level first; a magic item's head shape has its own traps
# entirely) -- none of these is a generic "spell parser" or "item parser",
# and picking the wrong one for a language is a parse failure waiting to
# happen, not a language a shared parser could have handled. A source whose
# (lang, kind) has no entry here is simply not built from yet -- the pages
# are extracted once per source and handed to every parser registered for
# that language.
PARSERS = {
    "fr": {
        "spell": parse_spells,
        "item": parse_items_fr,
        "feat": parse_feats_fr,
        "background": parse_backgrounds_fr,
        "species": parse_species_fr,
        "class": parse_classes_fr,
        "glossary": parse_glossary_fr,
        "weapon": parse_weapons_fr,
        "armor": parse_armor_fr,
        "tool": parse_tools_fr,
        "gear": parse_gear_fr,
        "monster": parse_monsters_fr,
    },
    "en": {
        "spell": parse_spells_en,
        "item": parse_items_en,
        "feat": parse_feats_en,
        "background": parse_backgrounds_en,
        "species": parse_species_en,
        "class": parse_classes_en,
        "glossary": parse_glossary_en,
        "weapon": parse_weapons_en,
        "armor": parse_armor_en,
        "tool": parse_tools_en,
        "gear": parse_gear_en,
        "monster": parse_monsters_en,
    },
}

# Every pinned source with a calibrated parser. A source landing in
# sources.lock.json without a parser yet (fetched but not calibrated) must
# not silently join a default build -- it has to be named explicitly with
# --source until someone has read its real pages.
DEFAULT_SOURCES = ["srd-5.2.1-fr", "srd-5.2.1-en"]


def run_id(pipeline_version, lock_sha, extractor):
    """Identity of a run, derived from its inputs only.

    No timestamp: two replays of the same inputs are the same run, and the
    ledger says so. A clock here would make every rebuild look like a change.
    """
    return canon.sha256_text(
        canon.canonical_json(
            {"p": pipeline_version, "l": lock_sha, "x": extractor}
        )
    )[:32]


def load_source_meta(source_id, fixture):
    if fixture:
        with open(os.path.join(FIXTURE_DIR, "source.json"), encoding="utf-8") as fh:
            return json.load(fh)
    src = sources.get(source_id)
    return {
        "id": src["id"],
        "title": src["title"],
        "publisher": src["publisher"],
        "version": src["version"],
        "lang": src["lang"],
        "url": src["url"],
        "sha256": src["sha256"],
        "bytes": src["bytes"],
        "etag": src.get("etag"),
        "last_modified": src.get("last_modified"),
        "license": src["license"],
        "license_url": src["license_url"],
        "attribution": src["attribution"],
    }


def gather(source_id, fixture):
    """Produce (pages, suspect page numbers, extractor ids)."""
    if fixture:
        with open(os.path.join(FIXTURE_DIR, "pages.json"), encoding="utf-8") as fh:
            pages = json.load(fh)
        return pages, [], ("fixture", "fixture")

    pdf_path = sources.verify(source_id)          # refuses on an unpinned or
    result = extract.extract(pdf_path)            # altered source
    suspect = [p["page"] for p in result["suspect_pages"]]
    if suspect:
        print(
            "  %d page(s) disputed between extractors: %s"
            % (len(suspect), suspect[:20]),
            file=sys.stderr,
        )
    return result["pages"], suspect, (result["extractor"], result["cross_checker"])


def build(source_ids=None, fixture=False, db_path=None):
    if fixture:
        source_ids = ["fixture-src"]
    elif source_ids is None:
        source_ids = DEFAULT_SOURCES
    elif isinstance(source_ids, str):
        source_ids = [source_ids]

    conn = db.create(db_path or db.DEFAULT_DB)

    lock_sha = "fixture" if fixture else sources.lock_hash()
    extractor = checker = None
    total_resolved = total_anomalies = total_candidates = total_rejected = 0

    with db.srd_write(conn):
        for source_id in source_ids:
            meta = load_source_meta(source_id, fixture)
            pages, suspect, (extractor, checker) = gather(source_id, fixture)
            kind_parsers = PARSERS.get(meta["lang"], {})
            if not kind_parsers:
                raise SystemExit(
                    "no parser calibrated for lang=%r (have: %s)"
                    % (meta["lang"], ", ".join(sorted(PARSERS)))
                )

            conn.execute(
                """INSERT INTO source
                     (id, title, publisher, version, lang, url, sha256, bytes, etag,
                      last_modified, license, license_url, attribution)
                   VALUES (:id,:title,:publisher,:version,:lang,:url,:sha256,:bytes,
                           :etag,:last_modified,:license,:license_url,:attribution)""",
                meta,
            )

            for kind, parser in sorted(kind_parsers.items()):
                records, anomalies, conflicts = parser.parse(pages, suspect)

                # ---- candidates, then collision resolution, then insertion -
                candidates = []
                for rec in records:
                    data = {k: v for k, v in rec.items() if k != "page"}
                    candidates.append(
                        {
                            "kind": kind,
                            "lang": meta["lang"],
                            "name": rec["name"],
                            "slug": canon.slugify(rec["name"]),
                            "data": data,
                            "content_hash": canon.content_hash(
                                kind, meta["lang"], rec["name"], data
                            ),
                            "page": rec["page"],
                        }
                    )

                resolved, collisions = canon.resolve_slug_collisions(candidates)

                for cand in resolved:
                    db.insert_record(
                        conn,
                        {
                            "id": canon.record_id("srd", kind, cand["lang"], cand["slug"]),
                            "layer": "srd",
                            "kind": kind,
                            "lang": cand["lang"],
                            "slug": cand["slug"],
                            "name": cand["name"],
                            "data": canon.canonical_json(cand["data"]),
                            "content_hash": cand["content_hash"],
                            "source_id": meta["id"],
                            "source_locator": "p.%d" % cand["page"],
                            "srd_version": meta["version"],
                            "license": meta["license"],
                            "attribution": meta["attribution"],
                        },
                    )

                # ---- the exclusion register ---------------------------------
                def exclude(name, reason, detail, locator, decided_by="importer",
                            lang=meta["lang"], kind=kind):
                    db.insert_exclusion(
                        conn,
                        {
                            "id": canon.sha256_text(
                                canon.canonical_json([lang, kind, name, reason, detail, locator])
                            )[:24],
                            "kind": kind,
                            "name": name,
                            "lang": lang,
                            "reason": reason,
                            "detail": detail,
                            "source_locator": locator,
                            "decided_by": decided_by,
                        },
                    )

                for anomaly in anomalies:
                    exclude("(unnamed block)", "unparsed", anomaly["detail"],
                            "p.%d:%d" % (anomaly["page"], anomaly["line"]))
                for conflict in conflicts:
                    exclude(conflict["name"], "extractor-conflict", conflict["detail"],
                            "p.%d" % conflict["page"])
                for cand in collisions:
                    exclude(cand["name"], "slug-collision",
                            "identifier disambiguated to %s; two entries slugify alike"
                            % cand["slug"], "p.%d" % cand["page"])

                total_resolved += len(resolved)
                total_anomalies += len(anomalies) + len(conflicts) + len(collisions)
                total_candidates += len(resolved) + len(anomalies) + len(conflicts)
                total_rejected += len(anomalies) + len(conflicts)

    rid = run_id(canon.PIPELINE_VERSION, lock_sha, extractor)
    conn.execute(
        """INSERT INTO import_run
             (id, pipeline_version, sources_lock_sha256, extractor, cross_checker,
              record_count, exclusion_count, candidates_examined, rejected_count)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            rid,
            canon.PIPELINE_VERSION,
            lock_sha,
            extractor,
            checker,
            total_resolved,
            total_anomalies,
            total_candidates,
            total_rejected,
        ),
    )
    conn.commit()
    return conn


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument(
        "--source", action="append", default=None,
        help="repeatable; defaults to every source in DEFAULT_SOURCES",
    )
    parser.add_argument("--db", default=None)
    parser.add_argument("--no-export", action="store_true")
    args = parser.parse_args(argv)

    try:
        conn = build(args.source, args.fixture, args.db)
    except sources.SourceError as exc:
        print("\nSOURCE REFUSED\n%s" % exc, file=sys.stderr)
        return 2
    except extract.ExtractorError as exc:
        print("\nEXTRACTOR REFUSED\n%s" % exc, file=sys.stderr)
        return 3

    report = db.audit(conn)
    print("records by layer : %s" % report["records_by_layer"])
    print("publishable (SRD): %d" % report["publishable"])
    print("exclusions       : %d" % report["exclusions"])
    print("provenance gaps  : %d" % report["provenance_gaps"])
    print("guard left open  : %s" % report["guard_left_open"])

    if report["provenance_gaps"] or report["guard_left_open"]:
        print("\nFAILED: the base is not in a publishable state.", file=sys.stderr)
        return 1

    if not args.no_export:
        manifest = export_json.export_all(conn)
        print("exports          : %d files" % len(manifest["files"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
