# exports/ — the committed, diffable exports the FHPC consumes

It is **not** where fixture output goes. `python3 src/build.py --fixture`
exercises the whole pipeline, but its records are synthetic test data; writing
them here would put invented spells into the tree the FHPC reads. The fixture
run in the test suite exports to a scratch directory under `build/` instead.

To rebuild from the pinned sources:

    python3 src/build.py            # every pinned, calibrated source, one run
                                     # writes exports/srd/<lang>/<kind>.json + MANIFEST.json

Currently: `srd/fr/spell.json` (339, stat lines only — v1), `srd/en/spell.json`
(339, with description text), `srd/en/item.json` (253 magic items),
`srd/en/feat.json` (17 feats).

Every file here carries a `$generated` header and is hashed in `MANIFEST.json`.
Do not edit them; edit the importer and rebuild.
