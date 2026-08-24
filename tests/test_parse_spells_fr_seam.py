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
EXPORTS = os.path.join(HERE, "..", "exports", "srd")
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import french_layer  # noqa: E402

# ⭐ `src/french_layer.py` : le français est un PATCH posé sur les adresses
# anglaises. Les slugs sont donc anglais — ce que ce fichier éprouve, ce sont
# les MOTS du livre français, et ils n'ont pas bougé.
RECORDS = {r["slug"]: r["data"]
           for r in french_layer.load(EXPORTS, "fr", "spell")}

# The three cases the dehyphenation fix surfaced, pinned exactly.
PINNED = {
    "arcanist-s-magic-aura": "24 heures",
    "divination": "instantanée",
    "sunbeam": "Concentration, jusqu’à 1 minute",
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
