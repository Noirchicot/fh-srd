# exports/ — the committed, diffable exports the FHPC consumes

It is **not** where fixture output goes. `python3 src/build.py --fixture`
exercises the whole pipeline, but its records are synthetic test data; writing
them here would put invented spells into the tree the FHPC reads. The fixture
run in the test suite exports to a scratch directory under `build/` instead.

To rebuild from the pinned sources:

    python3 src/build.py            # every pinned, calibrated source, one run
                                     # writes exports/srd/<lang>/<kind>.json + MANIFEST.json

Currently, in **both** `srd/en/` and `srd/fr/`: `spell.json` (339, with
description text), `item.json` (253 EN / 258 FR magic items — a real content
difference between the two printings, see the repository README),
`monster.json` (330 stat blocks), `glossary.json` (152), `feat.json` (17),
`background.json` (4), `species.json` (9), `class.json` (12 classes, each with
its one SRD subclass nested inside), `class-progression.json` (12 level tables,
1..20, one per class), `skill.json` (the 18 SRD skills), `weapon.json` (38),
`armor.json` (13), `tool.json` (25), `gear.json` (82),
`weapon-property.json` (11), `weapon-mastery.json` (8) and
`class-option.json` (38 — the 28 Eldritch Invocations a Warlock chooses ten
from, plus the 10 Metamagic options a Sorcerer chooses six from).
**2734 records in all.**

⚠️ The figure above used to read 2651 and was already wrong before
`class-option` arrived: the base held **2658** the moment before this genre was
added (2734 − 76, and every other export file came back byte-identical from
that build). Whoever left 2651 behind left it seven short; it is recorded here
rather than quietly corrected, because a stale total that nobody notices is the
shape of the 2026-08-08 defect this repository already paid for once.

`class-option.json` is the newest, and its name is **revocable** — the
arbitration on what to call a genre that means *"a list a class chooses from"*
has not been rendered. See `docs/RECORD-SHAPES.md` for the record shape and the
one asymmetry that matters (a manifestation is free once taken and carries no
`cost` key at all; a metamagic is paid for at every use and carries one), and
`QUESTIONS-ARCHITECTE.md` §Q17 for the question itself.

`weapon-property.json` and `weapon-mastery.json` came before it. They carry
the definitions of the eleven weapon properties and the eight mastery
properties, so that a consumer holding a weapon record can look up what its
`mastery` (`"Topple"`, `"Renversement"`) and each of its `properties` actually
do, **by the name the weapon already prints**. They are two genres and not one,
and they are not glossary entries — the reasons are in
`docs/RECORD-SHAPES.md`, together with the `reach` trap they exist to avoid
creating.

Beside the two language trees sits **`srd/correspondence.json`**, and it is a
different kind of file: the others are extracted, this one is **computed**. It says which French record is which English record — 830 pairs,
and **each one carries how it was reached**: 822 from a fingerprint of
language-independent data (a price, a weight, six ability scores) that was
unique on both sides, 8 deduced by following an already-proven pair, and any
signed by hand in `sources/correspondence-signed.json`. The 510 records nobody
has settled are **listed by name**, never guessed at; a record a person examined
and found to have no counterpart at all goes in `no_equivalent`, which is a
closed question and not an open one. The file modifies nothing it points at. `docs/CORRESPONDENCE.md` has the method, the measured `/2` weight
rule it rests on, and the one record where that rule rounds.

Above them sits **`srfh/en/`**, a second layer and not a second copy. It holds
what the book needs to be playable and never printed, derived from the SRD's own
rules, and it never edits an `srd` row: each of its records points down with a
`record_link`. Two files today. `item.json` (294) carries the **price and the
weight** of the magic items. `shelving.json` (416) carries the **shelf** — which
aisle, which shelf — and, for what is worn, the **body slot**; the SRD names
neither. Every value in both files sits beside its own `provenance`, which says
whether it was derived from a field the record already had or read from a table
a person wrote, and on which date. A value nobody can trace is a value nobody
can correct.

⚠️ `srfh` is **not** covered by the upstream CC-BY grant (`cc_by_srd: false`),
and its licence is deliberately `undecided` — that is Eric's question to answer,
not a placeholder to tidy away.

Every file here carries a `$generated` header and is hashed in `MANIFEST.json`.
Do not edit them; edit the importer and rebuild.
