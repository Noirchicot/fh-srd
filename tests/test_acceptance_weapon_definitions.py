"""The acceptance test for the two genres this lot exists to add.

> Given a weapon record, a consumer can look up **what its mastery does** and
> **what each of its properties does** — from the exports alone, by the name
> the weapon already prints, with no table of correspondences anywhere.

So this file reads `exports/` and nothing else: no parser, no PDF, no rule.
Both languages, because a builder Eric's table can use has to work in French.

⚠️ IT ALSO GUARDS THE `reach` TRAP, which is the reason these eleven records
are their own genre and not glossary entries. The Rules Glossary carries ONE
`reach` — the combat one, "your reach is 5 feet" — and does NOT carry the
weapon property `Reach`. Pouring the properties into the glossary would have
CREATED a duplicate that does not exist in the source. The test below asserts
the two texts are different and that they live in different genres, so a
later "tidy-up" that merges them fails here.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(ROOT, "exports", "srd")

sys.path.insert(0, os.path.join(ROOT, "src"))
import canon  # noqa: E402

LANGS = ("en", "fr")

# The SRD's own counts, stated so the test fails for the right reason rather
# than agreeing with whatever the file says.
EXPECTED_COUNTS = {"weapon-property": 11, "weapon-mastery": 8}
EXPECTED_WEAPONS = 38

# The properties cell is a comma-separated list whose members may carry a
# parenthetical that is NOT part of the name: "Versatile (1d8)",
# "Ammunition (Range 80/320; Arrow)", and — the one that looks like a bug and
# is not — "Deux mains (sauf à cheval)", a caveat rather than a value. The
# semicolon inside those parentheses is why the split has to respect them.
CELL_SPLIT = re.compile(r",\s*(?![^(]*\))")
TRAILING_PAREN = re.compile(r"\s*\([^()]*\)\s*$")

# The em dash the tables print for "this weapon has none".
EMPTY = {"—", "-", ""}

# The properties that are defined but never appear as a value in the Weapons
# table's Properties column. See the comment at the assertion below: one is a
# sidebar, the other is only ever printed inside another property's
# parentheses.
UNUSED_PROPERTIES = {
    "en": ["improvised-weapons", "range"],
    "fr": ["armes-improvisees", "portee"],
}


def load(lang, kind):
    with open(os.path.join(EXPORTS, lang, kind + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def main():
    for lang in LANGS:
        for kind in ("weapon-property", "weapon-mastery", "weapon", "glossary"):
            path = os.path.join(EXPORTS, lang, kind + ".json")
            if not os.path.exists(path):
                print("SKIP acceptance — exports not built: %s" % path)
                return

    for lang in LANGS:
        properties = load(lang, "weapon-property")
        masteries = load(lang, "weapon-mastery")
        weapons = load(lang, "weapon")
        glossary = load(lang, "glossary")

        # -- 1. the closed counts, in the shipped files ---------------------
        assert properties["count"] == EXPECTED_COUNTS["weapon-property"], properties["count"]
        assert masteries["count"] == EXPECTED_COUNTS["weapon-mastery"], masteries["count"]
        assert weapons["count"] == EXPECTED_WEAPONS, weapons["count"]

        # -- 2. every record carries its definition and its attribution -----
        for payload in (properties, masteries):
            for rec in payload["records"]:
                assert rec["data"]["description"].strip(), rec["id"]
                assert rec["license"] == "CC-BY-4.0", rec["id"]
                assert "SRD 5.2.1" in rec["attribution"], rec["id"]
                assert rec["srd_version"] == "5.2.1", rec["id"]
                assert rec["source_locator"].startswith("p."), rec["id"]

        # -- 3. the join the mandate asked for: BY NAME ---------------------
        mastery_by_slug = {r["slug"]: r for r in masteries["records"]}
        property_by_slug = {r["slug"]: r for r in properties["records"]}

        used_masteries = set()
        for weapon in weapons["records"]:
            printed = weapon["data"]["mastery"]
            slug = canon.slugify(printed)
            assert slug in mastery_by_slug, (
                "%s: weapon %r prints mastery %r, which resolves to no "
                "weapon-mastery record (slug %r)"
                % (lang, weapon["name"], printed, slug))
            used_masteries.add(slug)

        assert used_masteries == set(mastery_by_slug), (
            "%s: masteries defined but used by no weapon: %s"
            % (lang, sorted(set(mastery_by_slug) - used_masteries)))

        used_properties = set()
        for weapon in weapons["records"]:
            cell = (weapon["data"].get("properties") or "").strip()
            if cell in EMPTY:
                continue
            for piece in CELL_SPLIT.split(cell):
                name = TRAILING_PAREN.sub("", piece).strip()
                if not name:
                    continue
                slug = canon.slugify(name)
                assert slug in property_by_slug, (
                    "%s: weapon %r prints property %r, which resolves to no "
                    "weapon-property record (slug %r)"
                    % (lang, weapon["name"], name, slug))
                used_properties.add(slug)

        # TWO of the eleven are defined and never printed as a column value,
        # and both are facts of the source rather than gaps in the join:
        #
        #   * `Improvised Weapons` / `Armes improvisées` is a sidebar about
        #     weapons you do not own. No weapon row could carry it.
        #   * `Range` / `Portée` is only ever printed INSIDE another
        #     property's parentheses — "Ammunition (Range 80/320; Arrow)",
        #     "Munitions (portée 30/120 ; carreaux)" — never on its own. Its
        #     definition is what tells a reader how to read those two numbers.
        #
        # Named, so that a third one appearing here is a defect and not a
        # shrug.
        unused = sorted(set(property_by_slug) - used_properties)
        assert unused == UNUSED_PROPERTIES[lang], (lang, unused)

        # -- 4. ⚠️ THE `reach` TRAP ----------------------------------------
        glossary_by_slug = {r["slug"]: r for r in glossary["records"]}
        reach_slug = "reach" if lang == "en" else "allonge"
        assert reach_slug in property_by_slug, reach_slug
        if reach_slug in glossary_by_slug:
            here = property_by_slug[reach_slug]["data"]["description"]
            there = (glossary_by_slug[reach_slug]["data"].get("description")
                     or "")
            assert here != there, (
                "%s: the %r glossary entry and the %r weapon property now "
                "carry the SAME text. The SRD prints two different rules "
                "under that word; if they have become one, a merge happened "
                "that the source does not authorise."
                % (lang, reach_slug, reach_slug))
            assert (property_by_slug[reach_slug]["id"]
                    != glossary_by_slug[reach_slug]["id"])

        print("  ok  %s: %d properties + %d masteries; all %d weapons resolve "
              "their mastery and every printed property by name; %r is two "
              "records in two genres"
              % (lang, properties["count"], masteries["count"],
                 weapons["count"], reach_slug))

    print("PASS test_acceptance_weapon_definitions")


if __name__ == "__main__":
    main()
