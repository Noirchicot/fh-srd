"""Compare two export trees, record by record, and name every one that moved.

Run:
    python3 src/compare_exports.py BEFORE_DIR [AFTER_DIR]

`BEFORE_DIR` and `AFTER_DIR` are `exports/` directories (the ones holding
`MANIFEST.json` and `srd/<lang>/<kind>.json`). `AFTER_DIR` defaults to this
checkout's own `exports/`.

WHY THIS IS A TOOL AND NOT A ONE-OFF SCRIPT. Every change to the importer is
supposed to be surgical, and "surgical" is a claim about the 2613 records it did
NOT touch. A file-level `diff -rq` cannot make that claim: one export file holds
253 records, so a diff on `srd/en/item.json` says "item changed" whether one
record moved or all of them did. Worse, it says nothing at all when a genre
silently empties and its stale file stays on disk — the failure mode that cost
this repository 102 records on 2026-08-08 and that `build.py`'s own guard now
watches for.

So this compares RECORDS, keyed by their canonical id, and reports:

  * records that appeared or disappeared, by id;
  * records that changed, by id, with the fields that moved and the before/after
    length of each text field;
  * the count that is byte-identical, which is the number the claim rests on.

It exits non-zero when anything moved, so it can be used as a gate. That is not
a verdict that the change is wrong — a repair is supposed to move something —
it is a refusal to let a change go unread.
"""

import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_AFTER = os.path.join(ROOT, "exports")


class ExportTreeError(RuntimeError):
    pass


def load(root):
    """Every record in an export tree, keyed by id."""
    pattern = os.path.join(root, "srd", "*", "*.json")
    files = sorted(glob.glob(pattern))
    if not files:
        raise ExportTreeError(
            "no export files under %r (looked for %s).\n"
            "An empty tree would make every comparison trivially agree, which "
            "is exactly the silence this tool exists to break."
            % (root, pattern))
    records = {}
    for path in files:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
        for record in payload["records"]:
            if record["id"] in records:
                raise ExportTreeError(
                    "id %r appears twice in %r" % (record["id"], root))
            records[record["id"]] = record
    return records


def _shape(value):
    """A short, honest description of a field's value for the report."""
    if isinstance(value, str):
        return "%d chars" % len(value)
    if isinstance(value, (list, tuple)):
        return "%d items" % len(value)
    if value is None:
        return "absent"
    return repr(value)[:40]


def compare(before, after):
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed, identical = [], 0
    for rid in sorted(set(before) & set(after)):
        a = json.dumps(before[rid], sort_keys=True, ensure_ascii=False)
        b = json.dumps(after[rid], sort_keys=True, ensure_ascii=False)
        if a == b:
            identical += 1
            continue
        da, db = before[rid].get("data", {}), after[rid].get("data", {})
        fields = []
        for field in sorted(set(da) | set(db)):
            if da.get(field) != db.get(field):
                fields.append((field, _shape(da.get(field)), _shape(db.get(field))))
        # A record can change outside `data` (its slug, its locator).
        for field in sorted(set(before[rid]) | set(after[rid])):
            if field == "data":
                continue
            if before[rid].get(field) != after[rid].get(field):
                fields.append((field, _shape(before[rid].get(field)),
                               _shape(after[rid].get(field))))
        changed.append((rid, fields))
    return added, removed, changed, identical


def report(added, removed, changed, identical, out=sys.stdout):
    total = identical + len(changed)
    print("byte-identical : %d of %d shared records" % (identical, total), file=out)
    print("changed        : %d" % len(changed), file=out)
    print("added          : %d" % len(added), file=out)
    print("removed        : %d" % len(removed), file=out)
    for rid in added:
        print("  + %s" % rid, file=out)
    for rid in removed:
        print("  - %s" % rid, file=out)
    for rid, fields in changed:
        print("  ~ %s" % rid, file=out)
        for field, was, now in fields:
            print("      %-24s %s -> %s" % (field, was, now), file=out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", help="an exports/ directory")
    parser.add_argument("after", nargs="?", default=DEFAULT_AFTER,
                        help="an exports/ directory (default: this checkout's)")
    args = parser.parse_args(argv)

    try:
        before = load(args.before)
        after = load(args.after)
    except ExportTreeError as exc:
        print("\nEXPORT TREE REFUSED\n%s" % exc, file=sys.stderr)
        return 2

    added, removed, changed, identical = compare(before, after)
    report(added, removed, changed, identical)
    return 0 if not (added or removed or changed) else 1


if __name__ == "__main__":
    sys.exit(main())
