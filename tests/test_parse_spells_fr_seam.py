"""Page-seam regression for the FRENCH spell parser.

Found 2026-08-03, architect merge review: when a spell's last stat field falls
on a page's last line, the blank line that would close the stat block is lost
(each page is stripped independently) and `duration` silently swallowed the
next page's description prose. 11 of 339 FR records were affected — from v1
onward — and every one still looked complete, so no anomaly count caught it.
The EN parser found and fixed the same trap independently (Charm Monster,
Clone); this suite pins the FR port of that rule.

Runs against the committed export (no PDF needed): the determinism suite ties
the export to the parser, this one ties the content to the fix.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT = os.path.join(HERE, "..", "exports", "srd", "fr", "spell.json")

with open(EXPORT, encoding="utf-8") as f:
    RECORDS = {r["slug"]: r["data"] for r in json.load(f)["records"]}

# The three cases the dehyphenation fix surfaced, pinned exactly.
PINNED = {
    "aura-magique-de-l-arcaniste": "24 heures",
    "divination": "instantanée",
    "rayon-de-soleil": "Concentration, jusqu’à 1 minute",
}
for slug, want in PINNED.items():
    got = RECORDS[slug]["duration"]
    assert got == want, "seam regression: %s duration %r != %r" % (slug, got, want)

# Corpus-wide tripwire: a duration is a clause, never a paragraph. The longest
# legitimate FR duration ("Concentration, jusqu’à ...") stays well under this.
LIMIT = 60
bloated = {s: d["duration"] for s, d in RECORDS.items() if len(d["duration"]) > LIMIT}
assert not bloated, "duration carrying prose (page-seam bleed?): %r" % bloated

# Negative control: the tripwire must be able to fail.
doctored = dict(RECORDS["divination"], duration="instantanée " + "x" * LIMIT)
assert len(doctored["duration"]) > LIMIT, "negative control lost its teeth"

print("FR page-seam regression tests passed.")
