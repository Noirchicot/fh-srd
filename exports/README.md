# exports/ — empty on purpose

This directory holds the committed JSON exports the FHPC consumes. It is empty
because the source PDF has not been fetched or pinned yet.

It is **not** where fixture output goes. `python3 src/build.py --fixture`
exercises the whole pipeline, but its records are synthetic test data; writing
them here would put invented spells into the tree the FHPC reads. The fixture
run in the test suite exports to a scratch directory under `build/` instead.

Once the source is pinned:

    python3 src/build.py            # writes exports/srd/fr/*.json + MANIFEST.json

Every file here carries a `$generated` header and is hashed in `MANIFEST.json`.
Do not edit them; edit the importer and rebuild.
