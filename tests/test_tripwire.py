"""The tripwire and the publish gate.

Eric asked for protection against wild importing. The structural guards all
trust a label: a record inserted with layer='srd' and a valid source id passes
every constraint in the schema while containing a page of Forgotten Realms
lore. This is the check that reads what the records actually say.

Tested both ways round, because a tripwire that never fires and a tripwire that
always fires are equally useless.
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import build  # noqa: E402
import canon  # noqa: E402
import check_publishable  # noqa: E402
import db  # noqa: E402
import tripwire  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "build", "tripwire-test.sqlite")


def test_fires_on_each_family():
    cases = {
        "Le royaume de Toril s'est brisé": "product-identity",
        "compatible with Dungeons & Dragons": "trademark",
        "voir le Player's Handbook": "trademark",
        "the Lunar Sorcerer subclass": "not-in-srd",
        "un demi-orc de la Ombreterre": "product-identity",
        "imported from 5etools": "forbidden-source",
        "Zhentarim agents in Waterdeep": "product-identity",
        "an Aasimar paladin": "not-in-srd",
    }
    for text, family in cases.items():
        hits = tripwire.scan_text(text, "t")
        assert hits, "tripwire silent on %r" % text
        found = {h["family"] for h in hits}
        assert family in found, "%r -> %s, expected %s" % (text, found, family)
    print("  ok  fires on %d planted phrases across 4 families" % len(cases))


def test_does_not_fire_on_legitimate_srd_text():
    """A tripwire that flags ordinary SRD prose gets ignored, then stops working."""
    clean = [
        "Une gerbe de feu jaillit d'un point que vous désignez.",
        "Chaque créature dans la zone effectue un jet de sauvegarde de Dextérité.",
        "A shimmering green arrow streaks toward a target within range.",
        "Les orcs et les gobelins attaquent à l'aube.",   # 'orc' IS an SRD species
        "The dwarf cleric casts bless on the halfling.",
        "Sort de 3e niveau d'évocation, portée 45 mètres.",
    ]
    for text in clean:
        hits = tripwire.scan_text(text, "t")
        assert not hits, "false positive on %r: %s" % (text, hits)
    print("  ok  silent on %d lines of legitimate SRD prose" % len(clean))


def test_gate_passes_a_clean_base():
    conn = build.build(fixture=True, db_path=DB)
    failures = check_publishable.check(conn, verbose=False)
    # The fixture's source is marked attribution_verified in the real lock, and
    # the fixture produces exclusions, so a clean fixture base must pass.
    assert not failures, "the gate refused a clean base: %s" % failures
    print("  ok  publish gate passes a clean base")
    return conn


def test_gate_catches_planted_lore(conn):
    """A record smuggled in with a perfectly valid label is still caught."""
    row = conn.execute("SELECT * FROM record WHERE layer='srd' LIMIT 1").fetchone()
    with db.srd_write(conn):
        conn.execute(
            "UPDATE record SET data = ? WHERE id = ?",
            (
                canon.canonical_json(
                    {"text": ["La région s'est détachée de Toril et est tombée."]}
                ),
                row["id"],
            ),
        )
    failures = check_publishable.check(conn, verbose=False)
    assert any("tripwire" in f for f in failures), (
        "the gate passed a record containing Forgotten Realms lore: %s" % failures
    )
    print("  ok  gate catches planted lore in a validly-labelled srd record")


def test_gate_catches_a_stray_layer(conn):
    """This repository imports SRD and nothing else."""
    db.insert_record(
        conn,
        {
            "id": canon.record_id("fates_hand", "spell", "fr", "lame-d-anon"),
            "layer": "fates_hand",
            "kind": "spell",
            "lang": "fr",
            "slug": "lame-d-anon",
            "name": "Lame d'ÂNON",
            "data": canon.canonical_json({"level": 2}),
            "content_hash": "0" * 64,
            "source_id": None,
            "source_locator": "vault",
            "srd_version": None,
            "license": "proprietary",
            "attribution": "Eric — Fate's Hand",
        },
    )
    failures = check_publishable.check(conn, verbose=False)
    assert any("outside the srd layer" in f for f in failures), (
        "the gate passed a non-SRD layer: %s" % failures
    )
    print("  ok  gate refuses any record outside the srd layer")


def test_gate_catches_an_empty_exclusion_register(conn):
    conn.execute("DELETE FROM exclusion")
    failures = check_publishable.check(conn, verbose=False)
    assert any("exclusion register is empty" in f for f in failures), failures
    print("  ok  gate treats an empty exclusion register as a failure")


def main():
    test_fires_on_each_family()
    test_does_not_fire_on_legitimate_srd_text()
    conn = test_gate_passes_a_clean_base()
    test_gate_catches_planted_lore(conn)
    test_gate_catches_a_stray_layer(conn)
    test_gate_catches_an_empty_exclusion_register(conn)
    conn.close()
    os.remove(DB)
    print("PASS test_tripwire")


if __name__ == "__main__":
    main()
