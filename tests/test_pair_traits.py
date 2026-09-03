"""The cross-language trait key: it exists, it is derived, and it is verified twice.

⛔ WHAT THIS FILE REFUSES TO ACCEPT AS PROOF. A count. On lineages, this repo
once paired by position, produced `elfe-sylvestre` as `high-elf` and
`haut-elfe` as `wood-elf` — exactly swapped — and reported ZERO CONFLICTS,
because an inversion never contradicts itself. So the tests below read VALUES,
and the last one reads the whole pairing a SECOND TIME with the sides swapped:
that is the only reading an inversion cannot survive.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pair_traits  # noqa: E402

EXPORTS = os.path.join(os.path.dirname(__file__), "..", "exports", "srd")


def _rows(lang, kind):
    with open(os.path.join(EXPORTS, lang, kind + ".json"), encoding="utf-8") as handle:
        doc = json.load(handle)
    return next(value for value in doc.values() if isinstance(value, list))


@pytest.fixture(scope="module")
def species():
    english = {row["id"]: row for row in _rows("en", "species")}
    french = {row["id"]: row for row in _rows("fr", "species")}
    return english, french


@pytest.fixture(scope="module")
def names():
    """Names of already-paired records, under the address both languages share."""
    out = {}
    for kind in ("skill", "condition", "glossary", "spell"):
        for lang in ("en", "fr"):
            try:
                rows = _rows(lang, kind)
            except FileNotFoundError:
                continue
            for row in rows:
                out.setdefault(row["id"], {})[lang] = row.get("name")
    return out


def test_every_trait_carries_a_key_in_both_languages(species):
    """The deliverable itself: 33 traits, two languages, one key each."""
    english, french = species
    pairs, without = {}, []
    for address, record_en in english.items():
        record_fr = french.get(address)
        traits_en = (record_en.get("data") or {}).get("traits") or []
        traits_fr = (record_fr.get("data") or {}).get("traits") or [] if record_fr else []
        if not traits_en or not traits_fr:
            continue
        for trait in traits_en + traits_fr:
            if not trait.get("slug"):
                without.append("%s/%s" % (address, trait.get("id")))
        for trait in traits_en:
            pairs.setdefault((address, trait.get("slug")), {})["en"] = trait["id"]
        for trait in traits_fr:
            pairs.setdefault((address, trait.get("slug")), {})["fr"] = trait["id"]

    assert without == [], "traits shipped without a cross-language key: %s" % without[:6]
    lonely = [key for key, sides in pairs.items() if len(sides) != 2]
    assert lonely == [], (
        "a key that exists on one side only is not a key — it is a slug wearing "
        "the name of one: %s" % lonely[:6]
    )
    assert len(pairs) == 33, "the SRD prints 33 species traits per language, found %d" % len(pairs)


def test_the_pairs_are_read_one_by_one(species):
    """⛔ NOT a count. Six pairs whose English and French names have nothing in
    common are stated here in full, so that an inversion changes this file and
    not merely a total. `brave` is deliberately absent: it is the homograph, and
    it would pass under an inversion too."""
    english, french = species
    attendu = {
        "srd:species:en:elf": {"keen-senses": "sens-aiguises", "trance": "transe"},
        "srd:species:en:human": {"resourceful": "ingenieux", "skillful": "competent",
                                 "versatile": "polyvalent"},
        "srd:species:en:orc": {"adrenaline-rush": "poussee-d-adrenaline"},
    }
    for address, couples in attendu.items():
        par_slug = {t["slug"]: t["id"] for t in french[address]["data"]["traits"]}
        for slug, french_id in couples.items():
            assert par_slug.get(slug) == french_id, (
                "%s: the key %r should sit on the French trait %r, it sits on %r"
                % (address, slug, french_id, par_slug.get(slug))
            )


def test_the_pairing_reads_the_same_backwards(species, names):
    """⭐ THE READING AN INVERSION CANNOT SURVIVE. The module is run a second
    time with the two sides swapped — French presented as English. A pairing
    that inverted two traits would contradict itself here; one that is right
    cannot."""
    english, french = species
    reversed_names = {a: {"en": n.get("fr"), "fr": n.get("en")} for a, n in names.items()}
    agreements = 0
    for address, record_en in english.items():
        record_fr = french.get(address)
        traits_en = (record_en.get("data") or {}).get("traits") or []
        traits_fr = (record_fr.get("data") or {}).get("traits") or [] if record_fr else []
        if not traits_en or not traits_fr:
            continue
        forward, _ = pair_traits.pair_species_traits(traits_en, traits_fr, names)
        backward, _ = pair_traits.pair_species_traits(traits_fr, traits_en, reversed_names)
        for french_id, english_id in forward.items():
            assert backward.get(english_id) == french_id, (
                "%s: forward reads %s ⇄ %s, backward reads %s ⇄ %s — one of them is an "
                "inversion, and a count would never have said so"
                % (address, english_id, french_id, english_id, backward.get(english_id))
            )
            agreements += 1
    assert agreements == 33


def test_a_species_that_does_not_close_yields_nothing(names):
    """⛔ Refuse rather than guess. Two traits with no distinguishing signal must
    raise — not come back with one key placed and one missing, which nothing
    downstream could tell apart from a proven pair."""
    muets_en = [{"id": "alpha", "name": "Alpha", "text": "A rule."},
                {"id": "beta", "name": "Beta", "text": "A rule."}]
    muets_fr = [{"id": "un", "name": "Un", "text": "Une règle."},
                {"id": "deux", "name": "Deux", "text": "Une règle."}]
    with pytest.raises(pair_traits.TraitsNotPaired):
        pair_traits.pair_species_traits(muets_en, muets_fr, names)


def test_the_key_is_derived_not_declared():
    """⛔ No hand-written French→English table anywhere in the module. The whole
    point is that the key survives the next refresh of the source: a table
    written once drifts silently, and nobody sees it."""
    import ast
    chemin = os.path.join(os.path.dirname(__file__), "..", "src", "pair_traits.py")
    with open(chemin, encoding="utf-8") as handle:
        brut = handle.read()

    # ⛔ LA PROSE CITE, LE CODE DÉCLARE — et seul le second compte. Une première
    # version de ce garde lisait le fichier entier et accusait la docstring, qui
    # nomme `sens-aiguises` comme EXEMPLE de ce que le module ne fait pas. Un
    # garde qui crie au loup se fait retirer, et on se retrouve sans garde.
    arbre = ast.parse(brut)
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Expr) and isinstance(noeud.value, ast.Constant) \
                and isinstance(noeud.value.value, str):
            noeud.value.value = ""                       # docstrings décapées
    source = ast.unparse(arbre)
    source = "\n".join(l.split("#", 1)[0] for l in source.split("\n"))
    for francais in ("sens-aiguises", "vision-dans-le-noir", "ascendance-draconique",
                     "poussee-d-adrenaline", "ingenieux", "souffle"):
        assert francais not in source, (
            "%r appears in the pairing module: a French trait slug written into the "
            "code is a hand-held table, and it diverges at the next extraction "
            "without anyone noticing" % francais
        )
