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
`weapon-property.json` (11) and `weapon-mastery.json` (8). 2651 records in all.

`weapon-property.json` and `weapon-mastery.json` are the newest two. They carry
the definitions of the eleven weapon properties and the eight mastery
properties, so that a consumer holding a weapon record can look up what its
`mastery` (`"Topple"`, `"Renversement"`) and each of its `properties` actually
do, **by the name the weapon already prints**. They are two genres and not one,
and they are not glossary entries — the reasons are in
`docs/RECORD-SHAPES.md`, together with the `reach` trap they exist to avoid
creating.

Every file here carries a `$generated` header and is hashed in `MANIFEST.json`.
Do not edit them; edit the importer and rebuild.
