"""The two guards that close the silent-genre-loss hole, attacked deliberately.

On 2026-08-08 a change to `extract.py` made four parsers — `parse_weapons_en`,
`parse_weapons_fr`, `parse_armor_en`, `parse_armor_fr` — return ZERO records and
ZERO anomalies. Each met a line that was not a row, stopped, and returned its
empty list. The build printed a record total and **exited 0**. The four previous
export files stayed on disk, so `ls exports/` showed 29 files and `diff -rq`
against a reference tree showed nothing missing. 102 records had vanished and
the only thing that noticed was a human comparing two totals.

This suite makes that impossible to live through in silence again, and it does
it by **causing** both halves rather than asserting around them:

  1. a registered genre is made to return nothing, against a REAL pinned
     source, and the build must fail with a non-zero status that names it;
  2. a stale export is left on disk and the exporter must refuse, naming it.

⚠️ IT FAILS WHEN IT CANNOT RUN. Attack 1 needs a real PDF. A guard test that
skips when its subject is unavailable is the same trap the class-progression
witness fell into: green meant either "attacked and held" or "did nothing".
"""

import contextlib
import io
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import build  # noqa: E402
import export_json  # noqa: E402

SCRATCH = os.path.join(ROOT, "build", "guard-test")
EN_PDF = os.path.join(ROOT, "sources", "pdf", "SRD_CC_v5.2.1.pdf")

# The genre that actually broke. Attacking the one that bit is not sentiment:
# it is a real parser, registered for a real source, that really does yield 38
# records — so "0" can only come from the attack.
VICTIM = ("en", "weapon")


class SilentParser(object):
    """A parser that finds nothing and says nothing. Exactly the 2026-08-08 shape."""

    @staticmethod
    def parse(pages, suspect_pages=(), layout=()):
        return [], [], []


class ComplainingParser(object):
    """A parser that finds nothing but does report anomalies."""

    @staticmethod
    def parse(pages, suspect_pages=(), layout=()):
        return [], [{"page": 91, "line": 0, "detail": "every row refused"}], []


def require_sources():
    if not os.path.exists(EN_PDF):
        raise AssertionError(
            "%s is not present. Attack 1 makes a REAL parser return nothing "
            "against a REAL pinned source; without the PDF it cannot attack "
            "anything, and a guard test that cannot run must FAIL rather than "
            "pass quietly." % EN_PDF
        )


def run_build(argv):
    """`build.main(argv)`, returning (exit code, stderr)."""
    err = io.StringIO()
    out = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
        code = build.main(argv)
    return code, err.getvalue()


def attack_empty_genre():
    lang, kind = VICTIM
    db_path = os.path.join(SCRATCH, "empty.sqlite")
    argv = ["--source", "srd-5.2.1-%s" % lang, "--db", db_path, "--no-export"]

    # -- the control FIRST: unattacked, this build succeeds ------------------
    code, _err = run_build(argv)
    assert code == 0, "the unattacked build did not succeed (%s); the attack " \
                      "below would prove nothing" % code
    print("  ok  control: the same build with every parser intact exits 0")

    original = build.PARSERS[lang][kind]
    try:
        # -- ATTACK: the silent shape -------------------------------------
        build.PARSERS[lang][kind] = SilentParser
        code, err = run_build(argv)
        assert code != 0, (
            "THE BUILD EXITED 0 WITH A GENRE RETURNING NOTHING. This is the exact "
            "2026-08-08 defect and the guard did not fire.")
        assert code == 4, "expected exit code 4 (GENRE EMPTY), got %d" % code
        assert "GENRE EMPTY" in err, err
        assert "%s/%s" % (lang, kind) in err, (
            "the failure does not NAME the genre that vanished:\n%s" % err)
        assert "no records, no anomalies, no conflicts" in err, err
        print("  ok  attack 1a: a genre returning nothing silently fails the build, "
              "exit 4, and the message names %s/%s" % (lang, kind))

        # -- ATTACK: zero records but anomalies raised ---------------------
        build.PARSERS[lang][kind] = ComplainingParser
        code, err = run_build(argv)
        assert code == 4, "expected exit code 4, got %d" % code
        assert "%s/%s" % (lang, kind) in err, err
        assert "rejected everything it saw: 1 anomaly" in err, err
        print("  ok  attack 1b: zero records WITH anomalies also fails, and the "
              "message distinguishes the two cases")
    finally:
        build.PARSERS[lang][kind] = original

    # -- the control AGAIN: the patch is undone, not merely hoped ----------
    code, _err = run_build(argv)
    assert code == 0, "the parser was not restored; later assertions are unsafe"
    print("  ok  control: the victim parser is restored and the build exits 0 again")


def attack_stale_export():
    out_dir = os.path.join(SCRATCH, "exports")
    shutil.rmtree(out_dir, ignore_errors=True)
    conn = build.build(fixture=True, db_path=os.path.join(SCRATCH, "fx.sqlite"))

    manifest = export_json.export_all(conn, out_dir)
    written = sorted(f["path"] for f in manifest["files"])
    assert written, "the control export wrote nothing"
    assert not export_json.verify_manifest(out_dir)
    print("  ok  control: a clean tree exports %d file(s) and verifies" % len(written))

    # -- ATTACK: leave behind exactly what 2026-08-08 left behind ----------
    stale = os.path.join(out_dir, "srd", "fr", "weapon.json")
    os.makedirs(os.path.dirname(stale), exist_ok=True)
    with open(stale, "w", encoding="utf-8", newline="\n") as fh:
        fh.write('{"kind": "weapon", "count": 38, "records": []}\n')

    # THE HOLE, DEMONSTRATED BEFORE IT IS CLOSED: the mechanism that already
    # existed does not see this file at all. verify_manifest asks "is every
    # file I listed still intact"; it never asks "is there a file here I did
    # not list". Without this assertion the new guard could be mistaken for a
    # duplicate of the old one.
    assert export_json.verify_manifest(out_dir) == [], (
        "verify_manifest now reports the stale file; if that is true this test's "
        "premise has changed and the reasoning below needs rewriting")
    print("  ok  the pre-existing manifest check does NOT see a stale export — "
          "which is why this guard is not a duplicate of it")

    before = _snapshot(out_dir)
    raised = None
    try:
        export_json.export_all(conn, out_dir)
    except export_json.OrphanExportError as exc:
        raised = exc
    assert raised is not None, (
        "THE EXPORTER OVERWROTE A TREE HOLDING A STALE EXPORT. This is the second "
        "half of the 2026-08-08 defect and the guard did not fire.")
    assert "srd/fr/weapon.json" in str(raised), (
        "the refusal does not NAME the stale file:\n%s" % raised)
    print("  ok  attack 2: the exporter refuses and names srd/fr/weapon.json")

    assert _snapshot(out_dir) == before, (
        "the refusal wrote to the tree; a refused export must leave the directory "
        "exactly as it found it")
    print("  ok  attack 2b: the refusal left every byte of the tree untouched")

    # -- the whole 2026-08-08 scenario, end to end -------------------------
    os.remove(stale)
    export_json.export_all(conn, out_dir)
    print("  ok  removing the stale file lets the export through again")

    conn.close()


# A driver that patches the victim parser and then runs the REAL entry point in
# a REAL process. `main()` returning 4 is a strong claim; `$?` being 4 is the
# claim that actually failed on 2026-08-08, when the build "exited 0".
DRIVER = """
import sys
sys.path.insert(0, %r)
import build
class Silent(object):
    @staticmethod
    def parse(pages, suspect_pages=(), layout=()):
        return [], [], []
build.PARSERS[%r][%r] = Silent
sys.exit(build.main(sys.argv[1:]))
"""


def attack_process_exit_status():
    lang, kind = VICTIM
    path = os.path.join(SCRATCH, "driver.py")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(DRIVER % (os.path.join(ROOT, "src"), lang, kind))
    proc = subprocess.run(
        [sys.executable, path, "--source", "srd-5.2.1-%s" % lang,
         "--db", os.path.join(SCRATCH, "proc.sqlite"), "--no-export"],
        capture_output=True, text=True,
    )
    assert proc.returncode != 0, (
        "THE PROCESS EXITED 0. Every in-process assertion above can hold while "
        "this one fails, and this is the one that matters to a shell, a CI step "
        "or a person reading a terminal.")
    assert proc.returncode == 4, "expected $? == 4, got %d" % proc.returncode
    assert "%s/%s" % (lang, kind) in proc.stderr, proc.stderr
    print("  ok  attack 1c: the real entry point in a real process exits 4, "
          "not 0, and names %s/%s on stderr" % (lang, kind))


def attack_both_together():
    """The real incident: a genre goes silent AND its export is still on disk."""
    lang, kind = VICTIM
    out_dir = os.path.join(SCRATCH, "incident")
    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(os.path.join(out_dir, "srd", lang), exist_ok=True)
    with open(os.path.join(out_dir, "srd", lang, "%s.json" % kind), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write('{"kind": "%s", "count": 38, "records": []}\n' % kind)

    original = build.PARSERS[lang][kind]
    build.PARSERS[lang][kind] = SilentParser
    try:
        code, err = run_build(["--source", "srd-5.2.1-%s" % lang,
                               "--db", os.path.join(SCRATCH, "incident.sqlite")])
    finally:
        build.PARSERS[lang][kind] = original

    assert code == 4, (
        "the full incident — a genre returning nothing while its stale export sits "
        "on disk — did not stop the build (exit %d)" % code)
    assert "%s/%s" % (lang, kind) in err
    print("  ok  the incident in full: the build stops at the empty genre, before "
          "the export step can be reached, and names %s/%s" % (lang, kind))


def _snapshot(path):
    files = {}
    for base, _dirs, names in os.walk(path):
        for name in sorted(names):
            full = os.path.join(base, name)
            with open(full, "rb") as fh:
                files[os.path.relpath(full, path)] = fh.read()
    return files


def main():
    require_sources()
    shutil.rmtree(SCRATCH, ignore_errors=True)
    os.makedirs(SCRATCH, exist_ok=True)

    attack_empty_genre()
    attack_process_exit_status()
    attack_stale_export()
    attack_both_together()

    # -- NEGATIVE CONTROL ---------------------------------------------------
    # Both guards must be capable of staying quiet. A guard that fires on
    # everything is not a guard, and a suite that only ever sees it fire cannot
    # tell the difference.
    conn = build.build(fixture=True, db_path=os.path.join(SCRATCH, "nc.sqlite"))
    quiet = os.path.join(SCRATCH, "quiet")
    shutil.rmtree(quiet, ignore_errors=True)
    export_json.export_all(conn, quiet)
    export_json.export_all(conn, quiet)   # twice: a rewrite is not an orphan
    with open(os.path.join(quiet, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("hand-written, not generated\n")
    export_json.export_all(conn, quiet)   # a non-.json file is not an orphan
    conn.close()
    print("  ok  negative control: re-exporting over its own output, and a "
          "hand-written README.md beside it, are not orphans")

    shutil.rmtree(SCRATCH, ignore_errors=True)
    print("PASS test_build_guards")


if __name__ == "__main__":
    main()
