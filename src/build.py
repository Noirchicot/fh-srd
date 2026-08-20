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
import derive_mechanics
import export_json
import extract
import parse_armor_en
import parse_armor_fr
import parse_backgrounds_en
import parse_backgrounds_fr
import parse_class_progression_en
import parse_class_progression_fr
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
import parse_skills_en
import parse_skills_fr
import parse_species_en
import parse_species_fr
import parse_spells
import parse_spells_en
import parse_tools_en
import parse_tools_fr
import parse_weapon_mastery_en
import parse_weapon_mastery_fr
import parse_weapon_property_en
import parse_weapon_property_fr
import parse_weapons_en
import parse_weapons_fr
import sources
import weapon_sections

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
        "class-progression": parse_class_progression_fr,
        "glossary": parse_glossary_fr,
        "weapon": parse_weapons_fr,
        "armor": parse_armor_fr,
        "tool": parse_tools_fr,
        "gear": parse_gear_fr,
        "monster": parse_monsters_fr,
        "skill": parse_skills_fr,
        "weapon-mastery": parse_weapon_mastery_fr,
        "weapon-property": parse_weapon_property_fr,
    },
    "en": {
        "spell": parse_spells_en,
        "item": parse_items_en,
        "feat": parse_feats_en,
        "background": parse_backgrounds_en,
        "species": parse_species_en,
        "class": parse_classes_en,
        "class-progression": parse_class_progression_en,
        "glossary": parse_glossary_en,
        "weapon": parse_weapons_en,
        "armor": parse_armor_en,
        "tool": parse_tools_en,
        "gear": parse_gear_en,
        "monster": parse_monsters_en,
        "skill": parse_skills_en,
        "weapon-mastery": parse_weapon_mastery_en,
        "weapon-property": parse_weapon_property_en,
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


class EmptyGenreError(RuntimeError):
    """A genre registered in PARSERS produced no records at all."""


def check_every_genre_yielded(parsed, lang, fixture):
    """A registered genre that yields nothing is an ERROR, and it is named.

    WHY THIS EXISTS, and it is not hypothetical: on 2026-08-08 a change to
    `extract.py` made `parse_weapons_fr`, `parse_weapons_en`, `parse_armor_fr`
    and `parse_armor_en` return ZERO records and ZERO anomalies. Every one of
    them hit a line that was not a row, stopped, and returned its empty list
    without complaint. The build printed a record total and **exited 0**. The
    four previous export files were still on disk, so `ls exports/` and even
    `diff -rq` against a reference tree showed a complete, healthy set.

    **102 records had disappeared.** What caught it was a human comparing two
    numbers in the build's own output — 2613 against 2511 records, 29 against
    25 files. Nothing in the pipeline objected. A parser is allowed to find a
    shape it does not understand and say so; it is not allowed to find NOTHING
    and say nothing.

    THE FIXTURE IS EXEMPT, deliberately and narrowly. `tests/fixtures/pages.json`
    is a six-page synthetic stub carrying French spells and nothing else, so
    thirteen of the fourteen registered French genres correctly yield zero
    against it. Exempting it is not a hole in the guard: the fixture is not a
    calibrated source, and the attack in `tests/test_build_guards.py` runs
    against a REAL pinned source precisely so that the exemption cannot be the
    thing that makes the test pass.
    """
    if fixture:
        return
    empty = []
    for kind, (records, anomalies, conflicts) in sorted(parsed.items()):
        if records:
            continue
        empty.append((kind, len(anomalies), len(conflicts)))
    if not empty:
        return

    lines = []
    for kind, n_anomalies, n_conflicts in empty:
        if n_anomalies or n_conflicts:
            why = ("it rejected everything it saw: %d anomal%s, %d extractor conflict(s)"
                   % (n_anomalies, "y" if n_anomalies == 1 else "ies", n_conflicts))
        else:
            why = "it reported nothing at all — no records, no anomalies, no conflicts"
        lines.append("  %s/%s: %s" % (lang, kind, why))
    raise EmptyGenreError(
        "%d genre(s) registered in PARSERS for lang=%r produced no records:\n%s\n\n"
        "A registered genre is a claim that this source contains it. Zero records "
        "is that claim failing, not a quiet result — and the previously exported "
        "file for each of these is still on disk, which is what makes the failure "
        "look like success. Nothing has been exported and the build is stopping "
        "here.\n"
        "If a genre genuinely left the source, remove it from PARSERS and delete "
        "its export; that is a decision, and it should be one someone made."
        % (len(empty), lang, "\n".join(lines))
    )


def gather(source_id, fixture):
    """Produce (pages, suspect page numbers, per-page layout, extractor ids).

    `layout` is the per-page geometry the text stream cannot carry: the
    cell-separated reading of each full-width table, and the page's bold-italic
    phrases in reading order (`extract.layout_pymupdf`). It is handed only to
    parsers that declare `WANTS_LAYOUT`, because exactly one genre needs it —
    see `parse_species_en.py`. The fixture has no PDF and so no geometry: it
    supplies an empty page layout, and a parser that needs it must say so
    rather than quietly produce less.
    """
    if fixture:
        with open(os.path.join(FIXTURE_DIR, "pages.json"), encoding="utf-8") as fh:
            pages = json.load(fh)
        empty = [{"tables": [], "emphasis": []} for _ in pages]
        return pages, [], empty, ("fixture", "fixture")

    pdf_path = sources.verify(source_id)          # refuses on an unpinned or
    result = extract.extract(pdf_path)            # altered source
    suspect = [p["page"] for p in result["suspect_pages"]]
    if suspect:
        print(
            "  %d page(s) disputed between extractors: %s"
            % (len(suspect), suspect[:20]),
            file=sys.stderr,
        )
    return (result["pages"], suspect, result["layout"],
            (result["extractor"], result["cross_checker"]))


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

    # Where the derivation says "the source prints something I will not turn
    # into a field, and here is why". It is REPORTED, never swallowed: an
    # empty list is a claim, not an absence of checking.
    derivation_notes = []

    with db.srd_write(conn):
        for source_id in source_ids:
            meta = load_source_meta(source_id, fixture)
            pages, suspect, layout, (extractor, checker) = gather(source_id, fixture)
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

            # ONE PARSE, THEN THE DERIVATION, THEN THE INSERTION. The kinds
            # used to be parsed and inserted one at a time, in alphabetical
            # order -- which puts `skill`, `feat` and `tool` AFTER the
            # `background` and `class` records that have to resolve names
            # against them. A mechanical field that points at a record id has
            # to be able to check that the record exists, so every kind of one
            # source is parsed before any of them is written.
            parsed = {
                kind: (parser.parse(pages, suspect, layout)
                       if getattr(parser, "WANTS_LAYOUT", False)
                       else parser.parse(pages, suspect))
                for kind, parser in sorted(kind_parsers.items())
            }

            check_every_genre_yielded(parsed, meta["lang"], fixture)

            def candidates_for(kind, records, index):
                out = []
                for rec in records:
                    data = {k: v for k, v in rec.items() if k != "page"}
                    data.update(
                        derive_mechanics.derive(
                            kind, meta["lang"], data, index, rec["name"],
                            derivation_notes,
                        )
                    )
                    out.append(
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
                return out

            # The index the joins resolve against, built in two phases because
            # one of its kinds is itself derived.
            #
            #   1. `feat`, `skill` and `tool` look nothing up to derive their
            #      own fields, so they can be resolved before any join. That
            #      makes their identifiers final here -- including a collision
            #      suffix, which comes from a content hash nothing below will
            #      change.
            #   2. `class` DOES receive derived fields, and a background's feat
            #      names one ("Initié à la magie (Clerc)"). So it is derived and
            #      resolved next, against phase 1, and only then indexed. Its
            #      own derivation needs `skill` alone, which phase 1 provides.
            #
            # Everything else follows, against the complete index. Records are
            # INSERTED in alphabetical order of kind regardless of the order
            # they were resolved in, so the row order in the base is the one it
            # always had.
            index = {}
            resolved_by_kind = {}
            collisions_by_kind = {}

            def resolve_kind(kind):
                resolved, collisions = canon.resolve_slug_collisions(
                    candidates_for(kind, parsed[kind][0], index)
                )
                resolved_by_kind[kind] = resolved
                collisions_by_kind[kind] = collisions
                return resolved

            for phase in (derive_mechanics.INDEX_KINDS,
                          derive_mechanics.INDEX_KINDS_DERIVED):
                for kind in phase:
                    if kind not in parsed:
                        continue
                    index[kind] = derive_mechanics.build_index(
                        kind, meta["lang"], resolve_kind(kind)
                    )
            for kind in sorted(parsed):
                if kind not in resolved_by_kind:
                    resolve_kind(kind)

            # The five classes that get weapon masteries at level 1, RECOUNTED
            # and named -- and the two grammars that state the count made to
            # agree. See `derive_mechanics.check_weapon_mastery_counts`. It is
            # skipped on a source with no class records at all, which only the
            # `--fixture` stub is: `check_every_genre_yielded` above has
            # already refused that on anything real.
            if resolved_by_kind.get("class"):
                derive_mechanics.check_weapon_mastery_counts(
                    resolved_by_kind["class"],
                    parsed.get("class-progression", ([], [], []))[0],
                    meta["lang"],
                )

            for kind, (records, anomalies, conflicts) in sorted(parsed.items()):
                resolved = resolved_by_kind[kind]
                collisions = collisions_by_kind[kind]

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

    if derivation_notes:
        print(
            "  %d mechanical field(s) deliberately not emitted:"
            % len(derivation_notes),
            file=sys.stderr,
        )
        for note in derivation_notes:
            print("    - %s" % note, file=sys.stderr)

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
    except EmptyGenreError as exc:
        # Its own exit code, because the defect this guards against was a build
        # that exited 0. "Non-zero" is the whole point; 4 says which non-zero.
        print("\nGENRE EMPTY\n%s" % exc, file=sys.stderr)
        return 4
    except weapon_sections.SectionCountError as exc:
        # A closed set of eight or eleven that came back short. Same reasoning
        # as 4 and 5: the failure mode being closed here is a build that
        # exports a partial section and exits 0.
        print("\nSECTION INCOMPLETE\n%s" % exc, file=sys.stderr)
        return 6
    except derive_mechanics.WeaponMasteryCountError as exc:
        print("\nWEAPON MASTERY COUNT\n%s" % exc, file=sys.stderr)
        return 7

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
        try:
            manifest = export_json.export_all(conn)
        except export_json.OrphanExportError as exc:
            # Its own exit code, for the same reason EmptyGenreError has one:
            # the defect was a build that finished with status 0.
            print("\nSTALE EXPORT\n%s" % exc, file=sys.stderr)
            return 5
        print("exports          : %d files" % len(manifest["files"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
