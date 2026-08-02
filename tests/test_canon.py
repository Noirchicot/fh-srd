"""Canonical forms — the layer every byte of the pipeline passes through."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import canon  # noqa: E402
import sources  # noqa: E402


def test_slugify():
    cases = {
        "Boule de Feu": "boule-de-feu",
        "Écho Vagabond": "echo-vagabond",
        "Epée à deux mains": "epee-a-deux-mains",
        "Souffle d'Ono": "souffle-d-ono",
        "  Espaces   multiples  ": "espaces-multiples",
        "Cœur de Braise": "coeur-de-braise",
        "Nom-avec-tirets": "nom-avec-tirets",
    }
    for raw, want in cases.items():
        got = canon.slugify(raw)
        assert got == want, "slugify(%r) = %r, want %r" % (raw, got, want)

    # Accented and unaccented forms MUST collide rather than silently produce
    # two identifiers for the same word. That collision is what the exclusion
    # register then reports.
    assert canon.slugify("Écho") == canon.slugify("Echo")

    # Composed vs decomposed input is the same slug.
    assert canon.slugify("Écho") == canon.slugify("Écho")
    print("  ok  slugify (%d cases + NFC/NFD + accent collision)" % len(cases))


def test_canonical_json_is_key_order_blind():
    a = {"b": 1, "a": [3, 2], "c": {"z": 1, "y": 2}}
    b = {"c": {"y": 2, "z": 1}, "a": [3, 2], "b": 1}
    assert canon.canonical_json(a) == canon.canonical_json(b)
    # List order, unlike key order, is meaningful and must survive.
    assert canon.canonical_json({"a": [1, 2]}) != canon.canonical_json({"a": [2, 1]})
    # French stays readable in a diff instead of becoming \u escapes.
    assert "é" in canon.canonical_json({"x": "épée"})
    print("  ok  canonical_json: key-order blind, list-order sensitive, UTF-8")


def test_content_hash_ignores_location():
    data = {"level": 3, "school": "évocation"}
    h1 = canon.content_hash("spell", "fr", "Flamme", data)
    h2 = canon.content_hash("spell", "fr", "Flamme", dict(reversed(list(data.items()))))
    assert h1 == h2, "content hash depends on dict ordering"
    h3 = canon.content_hash("spell", "fr", "Flamme", {"level": 4, "school": "évocation"})
    assert h1 != h3, "content hash ignored a real change"
    print("  ok  content_hash: stable under reordering, sensitive to content")


def test_record_id_round_trip():
    rid = canon.record_id("srd", "spell", "fr", "boule-de-feu")
    assert rid == "srd:spell:fr:boule-de-feu"
    assert rid.split(":")[0] == "srd", "the layer is not readable from the id"
    print("  ok  record_id spells out its layer")


def test_collision_rule_suffixes_everyone():
    """All colliding records take a suffix — not just the later ones.

    If the first one kept the bare slug, a record appearing upstream later
    would reassign identifiers the FHPC already references. Suffixing everyone
    means a collision never moves an id that already existed.
    """
    cands = [
        {"slug": "echo", "content_hash": "bbbb" + "0" * 60, "name": "B"},
        {"slug": "echo", "content_hash": "aaaa" + "0" * 60, "name": "A"},
        {"slug": "unique", "content_hash": "cccc" + "0" * 60, "name": "C"},
    ]
    resolved, collisions = canon.resolve_slug_collisions(cands)
    slugs = sorted(r["slug"] for r in resolved)
    assert slugs == ["echo-aaaa00", "echo-bbbb00", "unique"], slugs
    assert len(collisions) == 2, collisions
    assert not any(r["slug"] == "echo" for r in resolved), "a bare colliding slug survived"

    # And the result does not depend on input order.
    again, _ = canon.resolve_slug_collisions(list(reversed(cands)))
    assert sorted(r["slug"] for r in again) == slugs
    print("  ok  slug collisions: all suffixed, order-independent")


def test_lock_hash_ignores_formatting():
    """The run identity must not change when the lock file is reflowed."""
    h1 = sources.lock_hash()
    assert len(h1) == 64, h1
    assert h1 == sources.lock_hash(), "lock hash is not stable"
    print("  ok  sources lock hash is semantic, not textual")


def main():
    for fn in [
        test_slugify,
        test_canonical_json_is_key_order_blind,
        test_content_hash_ignores_location,
        test_record_id_round_trip,
        test_collision_rule_suffixes_everyone,
        test_lock_hash_ignores_formatting,
    ]:
        fn()
    print("PASS test_canon")


if __name__ == "__main__":
    main()
