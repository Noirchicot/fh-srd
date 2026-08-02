"""Load and verify the pinned sources.

The rule this module enforces: the importer never reads a file it has not
verified. Not "warns about" — refuses.
"""

import json
import os

import canon

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LOCK = os.path.join(ROOT, "sources", "sources.lock.json")


class SourceError(RuntimeError):
    pass


def load_lock(path=LOCK):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def lock_hash(path=LOCK):
    """Hash of the *semantic* lock, not the file.

    Comments and key order in the JSON must not change the run identity, or a
    reflow of the file would look like a different import.
    """
    lock = load_lock(path)
    material = [
        {
            k: s.get(k)
            for k in ("id", "url", "sha256", "bytes", "version", "lang", "license")
        }
        for s in lock["sources"]
    ]
    material.sort(key=lambda s: s["id"])
    return canon.sha256_text(canon.canonical_json(material))


def get(source_id, path=LOCK):
    for src in load_lock(path)["sources"]:
        if src["id"] == source_id:
            return src
    raise SourceError("no such source in the lock: %s" % source_id)


def verify(source_id, path=LOCK):
    """Return the absolute path of a source file, or refuse.

    Three distinct refusals, each with its own remedy, because "the import
    failed" is not a useful thing to read at 2am:
      - not pinned      -> the lock has no hash yet
      - not present     -> the file was never fetched
      - hash mismatch   -> upstream changed, or the local copy was touched
    """
    src = get(source_id, path)
    abs_path = os.path.join(ROOT, src["file"])

    if not src.get("sha256"):
        raise SourceError(
            "source %s is not pinned: sha256 is null in sources.lock.json.\n"
            "  Fetch and pin it deliberately: python3 src/fetch_source.py --pin %s"
            % (source_id, source_id)
        )
    if not os.path.exists(abs_path):
        raise SourceError(
            "source %s is pinned but absent from disk (%s).\n"
            "  Fetch it: python3 src/fetch_source.py %s" % (source_id, src["file"], source_id)
        )

    actual = canon.sha256_file(abs_path)
    if actual != src["sha256"]:
        raise SourceError(
            "source %s does not match its pin — REFUSING to import.\n"
            "  expected sha256 %s\n"
            "  actual   sha256 %s\n"
            "  Either the local file was modified, or Wizards of the Coast\n"
            "  reissued the PDF. Do not re-pin without reading the diff: a new\n"
            "  upstream file can move content in or out of the SRD subset, which\n"
            "  is a licensing change, not a refresh."
            % (source_id, src["sha256"], actual)
        )

    actual_bytes = os.path.getsize(abs_path)
    if actual_bytes != src["bytes"]:
        raise SourceError(
            "source %s: size %d does not match the pinned %d"
            % (source_id, actual_bytes, src["bytes"])
        )
    return abs_path
