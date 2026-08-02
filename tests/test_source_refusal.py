"""The importer refuses an unpinned or altered source.

Three refusals, each with its own remedy. An import that "worked" against the
wrong bytes is worse than one that failed, because it produces a base that
looks right and cites a document it never read.
"""

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import sources  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write_lock(tmp, sha256, payload=b"hello"):
    """Build a throwaway lock + file pair under a temp root."""
    src_dir = os.path.join(tmp, "sources", "pdf")
    os.makedirs(src_dir, exist_ok=True)
    target = os.path.join(src_dir, "doc.pdf")
    if payload is not None:
        with open(target, "wb") as fh:
            fh.write(payload)
    lock = {
        "schema_version": 1,
        "sources": [
            {
                "id": "t",
                "title": "t",
                "publisher": "t",
                "version": "1",
                "lang": "fr",
                "url": "https://example.invalid/doc.pdf",
                "file": "sources/pdf/doc.pdf",
                "sha256": sha256,
                "bytes": len(payload) if payload is not None else 0,
                "license": "CC-BY-4.0",
                "license_url": "x",
                "attribution": "x",
            }
        ],
    }
    lock_path = os.path.join(tmp, "lock.json")
    with open(lock_path, "w", encoding="utf-8") as fh:
        json.dump(lock, fh)
    return lock_path


def expect_refusal(fn, needle):
    try:
        fn()
    except sources.SourceError as exc:
        assert needle in str(exc), "wrong refusal: %s" % exc
        return str(exc)
    raise AssertionError("expected a refusal containing %r, got none" % needle)


def main():
    tmp = tempfile.mkdtemp(prefix="fh-srd-src-")
    original_root = sources.ROOT
    try:
        sources.ROOT = tmp

        # 1 — not pinned
        lock = write_lock(tmp, None)
        expect_refusal(lambda: sources.verify("t", lock), "is not pinned")
        print("  ok  refuses an unpinned source, and says how to pin it")

        # 2 — pinned but the bytes do not match
        lock = write_lock(tmp, "f" * 64)
        msg = expect_refusal(lambda: sources.verify("t", lock), "does not match its pin")
        assert "licensing change" in msg, "the refusal does not explain the stakes"
        print("  ok  refuses altered bytes, and warns that a reissue is a licence change")

        # 3 — pinned, correct hash: accepted
        import canon

        real = canon.sha256_text("hello")
        lock = write_lock(tmp, real)
        path = sources.verify("t", lock)
        assert os.path.exists(path)
        print("  ok  accepts a source that matches its pin")

        # 4 — pinned and correct, but the file is gone
        os.remove(path)
        expect_refusal(lambda: sources.verify("t", lock), "absent from disk")
        print("  ok  refuses a missing source, and says how to fetch it")

        # 5 — the real lock: both SRD sources are declared, neither yet pinned
        real_lock = sources.load_lock(os.path.join(ROOT, "sources", "sources.lock.json"))
        ids = sorted(s["id"] for s in real_lock["sources"])
        assert ids == ["srd-5.2.1-en", "srd-5.2.1-fr"], ids
        for src in real_lock["sources"]:
            assert src["license"] == "CC-BY-4.0", src["id"]
            assert src["attribution_verified"] is False, (
                "%s claims a verified attribution; nothing has read the PDF yet"
                % src["id"]
            )
        print("  ok  the real lock declares both SRD sources, attribution unverified")
    finally:
        sources.ROOT = original_root
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS test_source_refusal")


if __name__ == "__main__":
    main()
