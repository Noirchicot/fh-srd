"""Tripwire — catches non-SRD content that got into the base by any route.

The other guards are *structural*: they check where a record claims to come
from. This one is *lexical*: it reads what the records actually say, and fires
on names that cannot legitimately appear in a CC-BY SRD import no matter which
layer someone filed them under.

It exists because the structural guards all trust a label. A record inserted
with `layer='srd'` and a valid source id passes every constraint in the schema
while containing a page of Forgotten Realms lore. A human in a hurry — or a
future importer pointed at the wrong file — is exactly the failure this
catches.

Three families, from the vault's compliance audit:

  * **Trademarks.** Never granted by CC-BY, whatever the SRD contains. The SRD's
    own legal page also asks that no attribution to Wizards beyond its exact
    statement be included, which rules out the "not endorsed by" line that
    normally accompanies fan content.
  * **Product identity.** Named settings, deities, factions and places that are
    not in the SRD: Forgotten Realms, Dragonlance, Spelljammer.
  * **Known non-SRD mechanics.** Content present in the 2024 books but outside
    the CC-BY subset.

A hit is not automatically fatal — "orc" is a legitimate SRD species and
"underdark" is not, though both are ordinary words in a French sentence. So the
scan REPORTS with context and the caller decides. What it must never do is stay
quiet.
"""

import re

# (pattern, family, note). Word-bounded and case-insensitive.
TERMS = [
    # --- trademarks: outside the CC-BY grant regardless of the SRD ----------
    (r"dungeons\s*&\s*dragons", "trademark", "WotC trademark; never granted by CC-BY"),
    (r"\bD&D\b", "trademark", "WotC trademark"),
    (r"player'?s\s+handbook", "trademark", "book title used as a mark"),
    (r"dungeon\s+master'?s\s+guide", "trademark", "book title used as a mark"),
    (r"monster\s+manual", "trademark", "book title used as a mark"),
    (r"wizards\s+of\s+the\s+coast", "trademark",
     "permitted ONLY inside the verbatim attribution statement"),

    # --- product identity: Forgotten Realms ---------------------------------
    (r"\bToril\b", "product-identity", "Forgotten Realms setting"),
    (r"\bFaer[uû]n\b", "product-identity", "Forgotten Realms setting"),
    (r"\bMielikki\b", "product-identity", "Forgotten Realms deity"),
    (r"\bZ(?:h|)entharim\b|\bZhentarim\b", "product-identity", "Forgotten Realms faction"),
    (r"\bBaldur'?s\s+Gate\b", "product-identity", "Forgotten Realms city"),
    (r"\bWaterdeep\b", "product-identity", "Forgotten Realms city"),
    (r"\bNeverwinter\b", "product-identity", "Forgotten Realms city"),
    (r"\bElturel\b", "product-identity", "Forgotten Realms city"),
    (r"\bUnderdark\b|\bOmbreterre\b", "product-identity", "product identity, not SRD"),
    (r"\bphlogist(?:on|ique)\b", "product-identity", "Spelljammer"),
    (r"\bDragonlance\b|\bKrynn\b", "product-identity", "Dragonlance setting"),
    (r"\bEberron\b|\bRavenloft\b|\bGreyhawk\b", "product-identity", "WotC setting"),

    # --- known non-SRD mechanics -------------------------------------------
    (r"lunar\s+sorcer", "not-in-srd", "Dragonlance subclass, not CC-licensed"),
    (r"\bartificer\b|\bartificier\b", "not-in-srd", "class excluded from SRD 5.2.1"),
    (r"circle\s+magic|magie\s+de\s+cercle", "not-in-srd", "Heroes of Faerûn, non-SRD"),
    (r"\baasimar\b", "not-in-srd", "species excluded from SRD 5.2.1"),
    (r"\beladrin\b", "not-in-srd", "species never in the SRD"),
    (r"half-?elf|demi-?elfe", "not-in-srd", "species removed in SRD 5.2"),
    (r"half-?orc|demi-?orc", "not-in-srd", "species removed in SRD 5.2"),

    # --- provenance that must never reach a publishable export -------------
    (r"5etools|5e\.tools", "forbidden-source", "no SRD marking; DMCA'd 2024-08"),
]

COMPILED = [(re.compile(p, re.IGNORECASE), fam, note) for p, fam, note in TERMS]


def scan_text(text, where=""):
    hits = []
    for pattern, family, note in COMPILED:
        for match in pattern.finditer(text or ""):
            start = max(match.start() - 45, 0)
            hits.append(
                {
                    "term": match.group(0),
                    "family": family,
                    "note": note,
                    "where": where,
                    "context": " ".join(
                        (text[start : match.end() + 45]).split()
                    ),
                }
            )
    return hits


def scan_base(conn, ignore_attribution=True):
    """Scan every record's name and payload.

    `ignore_attribution` skips the attribution column, where "Wizards of the
    Coast" is not merely allowed but mandatory. Scanning it would produce a hit
    on every single record and train whoever reads the report to ignore it —
    which is how a tripwire stops working.
    """
    hits = []
    for row in conn.execute(
        "SELECT id, layer, name, data FROM record ORDER BY id"
    ):
        hits.extend(scan_text(row["name"], "%s#name" % row["id"]))
        hits.extend(scan_text(row["data"], "%s#data" % row["id"]))
    if not ignore_attribution:
        for row in conn.execute("SELECT id, attribution FROM record ORDER BY id"):
            hits.extend(scan_text(row["attribution"], "%s#attribution" % row["id"]))
    return hits


def summarise(hits):
    by_family = {}
    for hit in hits:
        by_family.setdefault(hit["family"], []).append(hit)
    return by_family
