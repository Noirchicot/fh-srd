"""The attribution in the lock is the one printed in the PDF. Checked, not trusted.

A transcription is a manual step, and manual steps drift. This test re-reads
page 1 of the pinned PDF and asserts that the statement recorded in the lock
appears there word for word.

It is the difference between "somebody typed an attribution" and "the
attribution is the one Wizards requires". For a project that intends to sell,
that difference is the whole point.

Skips loudly when the PDFs are absent — they are gitignored, so a fresh clone
has not fetched them yet. A skip is visible in the output and is not a pass.
"""

import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import sources  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def flatten(text):
    """Strip ALL whitespace. Every other character must still match exactly.

    Collapsing runs of whitespace to a single space is not enough, and the way
    it fails is instructive: the PDF wraps the licence URL mid-token, printing
    `.../by/4.0/` at the end of one line and `legalcode` at the start of the
    next. Turn that break into a space and you get `.../by/4.0/ legalcode`,
    which is not a URL and does not match the correctly-recorded statement.

    Removing whitespace entirely keeps the check strict where it matters --
    wording, accents, the guillemets around "SRD 5.2.1", the version number --
    while ignoring line breaks, which belong to the page layout and not to the
    statement.
    """
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", "", text)


def main():
    try:
        import fitz
    except ImportError:
        print("SKIP test_attribution_verbatim — PyMuPDF not importable")
        return

    checked = 0
    for src in sources.load_lock()["sources"]:
        path = os.path.join(ROOT, src["file"])
        if not os.path.exists(path):
            print("SKIP %s — source not fetched (python3 src/fetch_source.py --pin %s)"
                  % (src["id"], src["id"]))
            continue

        doc = fitz.open(path)
        legal = flatten(doc[0].get_text("text"))
        doc.close()

        recorded = flatten(src["attribution"])
        assert recorded in legal, (
            "the attribution recorded for %s does not appear on page 1 of its own PDF.\n"
            "  recorded: %s\n"
            "  This means the statement was reconstructed rather than transcribed."
            % (src["id"], recorded[:160])
        )
        print("  ok  %s — statement found verbatim on page 1" % src["id"])

        # The SRD's legal page asks that no OTHER attribution to Wizards be
        # included. The vault audit's proposed block adds "neither approved nor
        # endorsed by Wizards of the Coast", which is such an other attribution.
        # Assert the restriction is really printed there, so the finding rests
        # on the document and not on a recollection of it.
        marker = ("n’inclure aucune autre attribution" if src["lang"] == "fr"
                  else "do not include any other attribution")
        assert flatten(marker) in legal, (
            "%s: could not find the 'no other attribution' restriction on page 1"
            % src["id"]
        )
        print("      and the 'no other attribution to Wizards' restriction with it")
        checked += 1

    if checked == 0:
        print("SKIP test_attribution_verbatim — no source fetched")
        return
    print("PASS test_attribution_verbatim  (%d source(s) verified against their PDF)"
          % checked)


if __name__ == "__main__":
    main()
