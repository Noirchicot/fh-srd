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

        # 5 — the real lock: both SRD sources declared, pinned, and attributed
        #
        # REWRITTEN 2026-08-03. This assertion previously required
        # `attribution_verified is False`, which was correct while nothing had
        # read the PDF: it was there to fail the day someone flipped the flag
        # without doing the work. The work has now been done — both statements
        # were transcribed from page 1 of their own PDF — so the assertion is
        # rewritten to the new truth rather than loosened or deleted. What it
        # now guards is the opposite direction: the flag may not be set without
        # a recorded transcription source, and the statement may not drift.
        # REWRITTEN 2026-08-03 (second time, same day): the lock gained a third
        # entry, the community Markdown conversion of the English SRD. It is a
        # SECONDARY source and is pinned by VCS commit rather than by a single
        # file hash, so the pin assertion below is split by source kind rather
        # than relaxed to accommodate it.
        real_lock = sources.load_lock(os.path.join(ROOT, "sources", "sources.lock.json"))
        ids = sorted(s["id"] for s in real_lock["sources"])
        assert ids == ["srd-5.2.1-en", "srd-5.2.1-en-markdown", "srd-5.2.1-fr"], ids

        pdfs = [s for s in real_lock["sources"] if s["file"].endswith(".pdf")]
        assert len(pdfs) == 2, [s["id"] for s in pdfs]
        for src in pdfs:
            assert src["license"] == "CC-BY-4.0", src["id"]
            assert src["sha256"] and len(src["sha256"]) == 64, (
                "%s is not pinned" % src["id"]
            )
            assert src["attribution_verified"] is True, src["id"]
            assert "transcribed verbatim" in src.get("attribution_source", ""), (
                "%s claims a verified attribution with no transcription source"
                % src["id"]
            )
            # The statement must name 5.2.1 -- not 5.2. The version number is
            # inside the required wording, and the vault audit quotes a 5.2
            # form that predates the document actually imported here.
            assert "5.2.1" in src["attribution"], src["id"]
            assert "https://www.dndbeyond.com/srd" in src["attribution"], src["id"]
            assert "creativecommons.org/licenses/by/4.0/legalcode" in src["attribution"]

        # The secondary source must declare itself secondary, credit the
        # converter, and must NOT inherit the converter's own paraphrased
        # licence text -- "material taken from", missing the dndbeyond.com URL.
        md = [s for s in real_lock["sources"] if s["id"].endswith("-markdown")][0]
        assert md["authority"].startswith("SECONDARY"), md["authority"]
        assert "downfallx" in md["converter_credit"], md["converter_credit"]
        assert "must NOT be used" in md["attribution_source"], md["attribution_source"]
        assert md["attribution"] == [
            s for s in pdfs if s["lang"] == "en"
        ][0]["attribution"], "markdown source does not carry Wizards' own wording"
        assert md["verification_2026_08_03"]["spells"].startswith("VERIFIED")
        assert md["verification_2026_08_03"]["monsters"].startswith("NOT VERIFIED")

        by_lang = {s["lang"]: s for s in pdfs}
        # The French PDF carries its OWN French statement. Attributing French
        # records with a statement transcribed from a different file is exactly
        # the kind of detail that makes an attribution defective.
        assert by_lang["fr"]["attribution"].startswith("Cette œuvre inclut"), (
            "the French source does not carry the French statement"
        )
        assert by_lang["en"]["attribution"].startswith("This work includes"), (
            "the English source does not carry the English statement"
        )
        assert by_lang["fr"]["attribution"] != by_lang["en"]["attribution"]
        print("  ok  both sources pinned; FR and EN attributions transcribed, distinct")
    finally:
        sources.ROOT = original_root
        shutil.rmtree(tmp, ignore_errors=True)
    print("PASS test_source_refusal")


if __name__ == "__main__":
    main()
