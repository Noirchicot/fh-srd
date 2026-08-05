"""The web build claims determinism too: same exports in, same bytes out.

Same three-way check as `test_determinism.py`, adapted to a build step that
reads `exports/srd/*.json` instead of PDFs: two in-process builds, byte for
byte; a third build in a separate process (a different PYTHONHASHSEED would
catch a stray set/dict iteration leaking into the HTML); and a negative
control, so a comparison that cannot fail cannot pass.
"""

import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import build_web  # noqa: E402
import canon  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRATCH = os.path.join(ROOT, "build", "web-determinism")
EXPORTS = os.path.join(ROOT, "exports", "srd")


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

    out_a = os.path.join(SCRATCH, "a")
    out_b = os.path.join(SCRATCH, "b")
    counts_a = build_web.build(out_a, EXPORTS)
    counts_b = build_web.build(out_b, EXPORTS)

    assert counts_a == counts_b, "record counts differ between replays"
    assert sum(sum(k.values()) for k in counts_a.values()) > 0, "build produced no records"

    # 1 — byte-identical output tree
    tree_a, tree_b = read_tree(out_a), read_tree(out_b)
    assert tree_a, "run A produced no files"
    assert set(tree_a) == set(tree_b), "output file sets differ: %s vs %s" % (
        sorted(set(tree_a) ^ set(tree_b)), []
    )
    for name in sorted(tree_a):
        assert tree_a[name] == tree_b[name], "output %s differs between replays" % name
    print("  ok  %d files byte-identical across two in-process builds" % len(tree_a))

    # 2 — a replay in a SEPARATE PROCESS
    out_c = os.path.join(SCRATCH, "c")
    subprocess.run(
        [sys.executable, os.path.join(ROOT, "src", "build_web.py"),
         "--out", out_c, "--exports", EXPORTS],
        check=True, capture_output=True, cwd=ROOT,
        env=dict(os.environ, PYTHONHASHSEED="12345"),
    )
    tree_c = read_tree(out_c)
    assert set(tree_c) == set(tree_a), "separate-process build produced a different file set"
    for name in sorted(tree_a):
        assert tree_a[name] == tree_c[name], "separate-process build differs on %s" % name
    print("  ok  replayed in a separate process with PYTHONHASHSEED=12345: identical")

    # 3 — negative control: the comparison must be capable of failing.
    spell_index = os.path.join("en", "spell", "index.html")
    mutated = tree_a[spell_index].replace(b"Fireball", b"Fireballs", 1)
    assert mutated != tree_a[spell_index], "negative control did not mutate anything"
    assert canon.sha256_text(mutated.decode("utf-8")) != canon.sha256_text(
        tree_a[spell_index].decode("utf-8")
    ), "the comparison cannot detect a change"
    print("  ok  negative control: a mutated file is detected as different")

    shutil.rmtree(SCRATCH, ignore_errors=True)
    print("PASS test_web_determinism  (%d files)" % len(tree_a))


if __name__ == "__main__":
    main()
