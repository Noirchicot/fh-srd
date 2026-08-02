"""The exports carry their own attribution, and the manifest catches tampering.

The second half is the one that matters operationally. A generated file copied
into `fh-phb/docs/` and then hand-edited there is the failure mode that already
cost this project a deployed bugfix. The `$generated` header asks a human not
to. The manifest is what actually notices.
"""

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import build  # noqa: E402
import export_json  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.path.join(ROOT, "build", "export-test")
OUT = os.path.join(SCRATCH, "exports")


def main():
    shutil.rmtree(SCRATCH, ignore_errors=True)
    conn = build.build(fixture=True, db_path=os.path.join(SCRATCH, "t.sqlite"))
    manifest = export_json.export_all(conn, OUT)

    # -- every export declares itself generated ----------------------------
    spell_file = os.path.join(OUT, "srd", "fr", "spell.json")
    with open(spell_file, encoding="utf-8") as fh:
        payload = json.load(fh)
    assert "DO NOT EDIT" in payload["$generated"], "missing generated notice"
    assert "fh-srd" in payload["$generated"], "notice does not name the source repo"
    print("  ok  generated notice names the source repository")

    # -- attribution is on every record, not only on the file --------------
    assert payload["records"], "no records exported"
    for rec in payload["records"]:
        for field in ("license", "attribution", "source_id", "srd_version", "layer"):
            assert rec.get(field), "record %s has no %s" % (rec["id"], field)
        assert rec["id"].startswith(rec["layer"] + ":"), (
            "record id does not spell out its layer: %s" % rec["id"]
        )
    print("  ok  attribution + layer on each of the %d records" % len(payload["records"]))

    # -- the layer directory split is real ---------------------------------
    assert os.path.isdir(os.path.join(OUT, "srd")), "no srd/ directory"
    assert any(e["path"] == "srd/fr/spell.json" for e in manifest["files"]), (
        "expected a layer/lang/kind path, got %s" % [e["path"] for e in manifest["files"]]
    )
    print("  ok  exports split by layer directory")

    # -- manifest paths are portable ---------------------------------------
    # They must be relative to the export root, not to this repository, or the
    # manifest cannot verify the tree once it has been copied into fh-phb.
    for entry in manifest["files"]:
        p = entry["path"]
        assert not os.path.isabs(p), "absolute path in manifest: %s" % p
        assert ".." not in p.split("/"), "escaping path in manifest: %s" % p
        assert not p.startswith("exports/"), "repo-relative path in manifest: %s" % p
    print("  ok  manifest paths are relative to the export root")

    # -- a clean tree verifies ---------------------------------------------
    problems = export_json.verify_manifest(OUT)
    assert not problems, "a freshly written tree failed its own manifest: %s" % problems
    print("  ok  freshly exported tree verifies")

    # -- and it still verifies somewhere else entirely ----------------------
    # This is the case that matters: the FHPC will hold this tree at a
    # different path, inside a different repository.
    relocated = os.path.join(SCRATCH, "pretend-fh-phb", "docs", "data", "srd")
    shutil.copytree(OUT, relocated)
    problems = export_json.verify_manifest(relocated)
    assert not problems, "the manifest does not verify a relocated copy: %s" % problems
    print("  ok  manifest verifies a copy relocated to another repository")

    # -- tampering is caught (the whole point) ------------------------------
    with open(spell_file, encoding="utf-8") as fh:
        text = fh.read()
    with open(spell_file, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text.replace("Flamme Vagabonde", "Flamme Vagabonde ", 1))
    problems = export_json.verify_manifest(OUT)
    assert problems, "a hand-edited export passed the manifest check"
    assert any(p[1] == "modified" for p in problems), problems
    print("  ok  hand-edited export detected: %s" % problems[0][0])

    # -- a deleted export is caught too -------------------------------------
    os.remove(spell_file)
    problems = export_json.verify_manifest(OUT)
    assert any(p[1] == "missing" for p in problems), problems
    print("  ok  missing export detected")

    conn.close()
    shutil.rmtree(SCRATCH, ignore_errors=True)
    print("PASS test_exports")


if __name__ == "__main__":
    main()
