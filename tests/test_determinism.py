"""The determinism claim, checked rather than asserted.

"Rejouer l'import sur la même source produit exactement les mêmes
enregistrements, aux mêmes identifiants."

Two runs, compared three ways:

  1. `sqlite3 .dump` — NOT the .db file. A SQLite file is not byte-stable:
     page allocation, freelists and vacuum state legitimately differ between
     two identical logical databases. Comparing .db bytes would either fail for
     no reason or, worse, pass for the wrong one. The dump is the logical
     content, and that is what must match.
  2. The exported JSON, byte for byte. This is what the FHPC actually consumes.
  3. The identifiers, as a set. The point of determinism here is that a
     re-import does not renumber anything that already has references pointing
     at it.
"""

import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import build  # noqa: E402
import canon  # noqa: E402
import export_json  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.path.join(ROOT, "build", "determinism")


def dump(db_path):
    out = subprocess.run(
        ["sqlite3", db_path, ".dump"], capture_output=True, text=True, check=True
    )
    return out.stdout


def run_once(tag):
    db_path = os.path.join(SCRATCH, "%s.sqlite" % tag)
    out_dir = os.path.join(SCRATCH, tag, "exports")
    conn = build.build(fixture=True, db_path=db_path)
    export_json.export_all(conn, out_dir)
    ids = [r[0] for r in conn.execute("SELECT id FROM record ORDER BY id")]
    conn.close()
    return dump(db_path), out_dir, ids


def read_tree(path):
    files = {}
    for base, _, names in os.walk(path):
        for name in sorted(names):
            full = os.path.join(base, name)
            with open(full, "rb") as fh:
                files[os.path.relpath(full, path)] = fh.read()
    return files


def main():
    shutil.rmtree(SCRATCH, ignore_errors=True)
    os.makedirs(SCRATCH, exist_ok=True)

    dump_a, dir_a, ids_a = run_once("a")
    dump_b, dir_b, ids_b = run_once("b")

    assert dump_a, "run A produced an empty dump"
    assert ids_a, "run A produced no records"

    # 1 — logical database content
    ha, hb = canon.sha256_text(dump_a), canon.sha256_text(dump_b)
    assert ha == hb, "SQL dump differs between replays:\n  A %s\n  B %s" % (ha, hb)

    # 2 — exported bytes
    tree_a, tree_b = read_tree(dir_a), read_tree(dir_b)
    assert set(tree_a) == set(tree_b), "export file sets differ: %s vs %s" % (
        sorted(tree_a),
        sorted(tree_b),
    )
    for name in sorted(tree_a):
        assert tree_a[name] == tree_b[name], "export %s differs between replays" % name

    # 3 — identifiers are stable
    assert ids_a == ids_b, "identifiers moved between replays"

    # 4 — a replay in a SEPARATE PROCESS
    # Runs A and B share an interpreter, so they also share module state, hash
    # seeds and import caches. Agreeing with itself is the weakest form of
    # agreeing. A fresh process is the honest replay, and it is the one that
    # would catch a dict iteration order or a PYTHONHASHSEED leaking into the
    # output.
    db_c = os.path.join(SCRATCH, "c.sqlite")
    out_c = os.path.join(SCRATCH, "c", "exports")
    subprocess.run(
        [sys.executable, os.path.join(ROOT, "src", "build.py"),
         "--fixture", "--db", db_c, "--no-export"],
        check=True, capture_output=True, cwd=ROOT,
        env=dict(os.environ, PYTHONHASHSEED="12345"),
    )
    dump_c = dump(db_c)
    assert canon.sha256_text(dump_c) == ha, (
        "a replay in a separate process produced a different base"
    )

    # 5 — negative control: the check must be capable of failing. If a
    # deliberate mutation still compares equal, the comparison is vacuous.
    mutated = dump_a.replace("Flamme Vagabonde", "Flamme Vagabondes", 1)
    assert mutated != dump_a, "negative control did not mutate anything"
    assert canon.sha256_text(mutated) != ha, "the comparison cannot detect a change"

    print("PASS test_determinism  (%d records, dump sha %s)" % (len(ids_a), ha[:16]))
    print("       exports compared byte-for-byte: %d files" % len(tree_a))
    print("       replayed in a separate process with PYTHONHASHSEED=12345: identical")
    shutil.rmtree(SCRATCH, ignore_errors=True)
    _ = out_c


if __name__ == "__main__":
    main()
