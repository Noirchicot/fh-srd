"""Database access, with the SRD write guard as an explicit, scoped latch."""

import contextlib
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCHEMA = os.path.join(ROOT, "schema", "001_canonical.sql")
DEFAULT_DB = os.path.join(ROOT, "build", "srd.sqlite")


def create(path=DEFAULT_DB, overwrite=True):
    """Build a fresh database from the schema.

    The base is a build artefact: it is rebuilt from the pinned source, never
    migrated in place and never committed. That is what lets the determinism
    check compare two full runs instead of two diffs.
    """
    if overwrite and os.path.exists(path):
        os.remove(path)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = connect(path)
    with open(SCHEMA, "r", encoding="utf-8") as fh:
        conn.executescript(fh.read())
    conn.commit()
    return conn


def connect(path=DEFAULT_DB):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextlib.contextmanager
def srd_write(conn):
    """Open the SRD write latch for the duration of the block, then close it.

    Closing happens in a `finally`, so a crash mid-import leaves the guard
    shut rather than leaving the base quietly writable.
    """
    conn.execute("UPDATE guard SET v = 1 WHERE k = 'srd_import_open'")
    try:
        yield conn
    finally:
        conn.execute("UPDATE guard SET v = 0 WHERE k = 'srd_import_open'")
        conn.commit()


def insert_record(conn, rec):
    conn.execute(
        """INSERT INTO record
             (id, layer, kind, lang, slug, name, data, content_hash,
              source_id, source_locator, srd_version, license, attribution)
           VALUES
             (:id, :layer, :kind, :lang, :slug, :name, :data, :content_hash,
              :source_id, :source_locator, :srd_version, :license, :attribution)""",
        rec,
    )


def insert_exclusion(conn, exc):
    conn.execute(
        """INSERT OR REPLACE INTO exclusion
             (id, kind, name, lang, reason, detail, source_locator, decided_by)
           VALUES
             (:id, :kind, :name, :lang, :reason, :detail, :source_locator, :decided_by)""",
        exc,
    )


def audit(conn):
    """The three questions worth asking of any built base."""
    gaps = conn.execute("SELECT count(*) FROM provenance_gaps").fetchone()[0]
    guard_open = conn.execute(
        "SELECT v FROM guard WHERE k = 'srd_import_open'"
    ).fetchone()[0]
    by_layer = {
        row["layer"]: row["n"]
        for row in conn.execute(
            "SELECT layer, count(*) AS n FROM record GROUP BY layer ORDER BY layer"
        )
    }
    return {
        "provenance_gaps": gaps,
        "guard_left_open": bool(guard_open),
        "records_by_layer": by_layer,
        "publishable": conn.execute(
            "SELECT count(*) FROM publishable_srd"
        ).fetchone()[0],
        "exclusions": conn.execute("SELECT count(*) FROM exclusion").fetchone()[0],
    }
