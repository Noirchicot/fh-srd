"""The four layers stay separated, and the database enforces it.

This is the legal condition of the project, so it is tested like one: every
rule is checked by making the database REFUSE the thing that would break it,
not by checking that the importer happens not to try.
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import build  # noqa: E402
import canon  # noqa: E402
import db  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "build", "layers-test.sqlite")

CASES = []


def case(fn):
    CASES.append(fn)
    return fn


def fh_record(slug="lame-d-anon", **over):
    rec = {
        "id": canon.record_id("fates_hand", "spell", "fr", slug),
        "layer": "fates_hand",
        "kind": "spell",
        "lang": "fr",
        "slug": slug,
        "name": "Lame d'ÂNON",
        "data": canon.canonical_json({"level": 2}),
        "content_hash": "0" * 64,
        "source_id": None,
        "source_locator": "vault",
        "srd_version": None,
        "license": "proprietary",
        "attribution": "Eric — Fate's Hand",
    }
    rec.update(over)
    return rec


@case
def srd_layer_is_importer_owned(conn):
    """A record cannot be added to the SRD layer with the guard shut."""
    try:
        db.insert_record(
            conn,
            fh_record(
                slug="contrebande",
                layer="srd",
                id=canon.record_id("srd", "spell", "fr", "contrebande"),
                source_id="fixture-src",
                srd_version="0.0.0-fixture",
                license="CC-BY-4.0",
                attribution="x",
                source_locator="p.1",
            ),
        )
    except sqlite3.IntegrityError as exc:
        assert "importer-owned" in str(exc), exc
        return
    raise AssertionError("the SRD write guard did not fire")


@case
def srd_record_must_carry_provenance(conn):
    """Even with the guard open, an SRD row without provenance is refused."""
    with db.srd_write(conn):
        try:
            db.insert_record(
                conn,
                fh_record(
                    slug="sans-source",
                    layer="srd",
                    id=canon.record_id("srd", "spell", "fr", "sans-source"),
                    source_id=None,
                    license="CC-BY-4.0",
                ),
            )
        except sqlite3.IntegrityError:
            return
    raise AssertionError("an SRD record without a source was accepted")


@case
def id_must_spell_out_its_layer(conn):
    """An id that disagrees with its layer column cannot exist."""
    try:
        db.insert_record(conn, fh_record(id="srd:spell:fr:menteur"))
    except sqlite3.IntegrityError:
        return
    raise AssertionError("a record whose id contradicts its layer was accepted")


@case
def overriding_never_mutates_the_srd_row(conn):
    """A Fate's Hand override leaves the SRD record byte-identical."""
    srd_id = conn.execute(
        "SELECT id FROM record WHERE layer='srd' ORDER BY id LIMIT 1"
    ).fetchone()[0]
    before = dict(
        conn.execute("SELECT * FROM record WHERE id=?", (srd_id,)).fetchone()
    )

    db.insert_record(conn, fh_record())
    conn.execute(
        "INSERT INTO record_link (src_id, dst_id, rel, note) VALUES (?,?,?,?)",
        (fh_record()["id"], srd_id, "overrides", "FH raises the damage die"),
    )
    conn.commit()

    after = dict(
        conn.execute("SELECT * FROM record WHERE id=?", (srd_id,)).fetchone()
    )
    assert before == after, "the SRD row changed when a layer above it overrode it"


@case
def srd_cannot_override_anything(conn):
    """The base never amends the layers above it; the edge is refused."""
    srd_id = conn.execute(
        "SELECT id FROM record WHERE layer='srd' ORDER BY id LIMIT 1"
    ).fetchone()[0]
    try:
        conn.execute(
            "INSERT INTO record_link (src_id, dst_id, rel) VALUES (?,?,?)",
            (srd_id, fh_record()["id"], "overrides"),
        )
    except sqlite3.IntegrityError as exc:
        assert "never overrides" in str(exc), exc
        return
    raise AssertionError("an srd->higher override edge was accepted")


@case
def publishing_the_srd_alone_is_one_query(conn):
    """`publishable_srd` returns the SRD layer and nothing else."""
    layers = {
        row[0] for row in conn.execute("SELECT DISTINCT layer FROM publishable_srd")
    }
    assert layers == {"srd"}, "publishable view leaked other layers: %s" % layers

    total = conn.execute("SELECT count(*) FROM record").fetchone()[0]
    pub = conn.execute("SELECT count(*) FROM publishable_srd").fetchone()[0]
    assert pub < total, "the fixture has no non-SRD record; the test proves nothing"


@case
def no_record_anywhere_lacks_attribution(conn):
    gaps = conn.execute("SELECT count(*) FROM provenance_gaps").fetchone()[0]
    assert gaps == 0, "%d record(s) without attribution or licence" % gaps


def main():
    conn = build.build(fixture=True, db_path=DB)
    for fn in CASES:
        fn(conn)
        print("  ok  %s" % fn.__name__)
    conn.close()
    os.remove(DB)
    print("PASS test_layers  (%d checks)" % len(CASES))


if __name__ == "__main__":
    main()
