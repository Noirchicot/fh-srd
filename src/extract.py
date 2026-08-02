"""PDF -> text, with the extractor pinned and a second extractor as a witness.

WotC publishes the SRD as a PDF and nothing else — no DOCX, no JSON, no
markdown, in any of the four localised languages. So the weakest link in this
pipeline is not the database, it is the moment a glyph becomes a character.

Two defences:

1. **The extractor version is pinned and asserted.** PyMuPDF's output is
   deterministic for a given MuPDF build, and non-deterministic across builds
   in ways nobody announces. The importer refuses to run on an unpinned build
   rather than produce records that differ from last month's for no visible
   reason.

2. **A second, independent extractor reads the same pages.** Poppler's
   `pdftotext` shares no code with MuPDF. Where the two agree, the text is
   sound. Where they disagree, the page is reported — and the affected records
   go to the exclusion register as `extractor-conflict` instead of being
   guessed at. "Vérifier plutôt que croire", applied to the layer that most
   invites believing.
"""

import re
import subprocess
import unicodedata
from collections import Counter

# Pinned toolchain. Both are asserted at run time; both are written into the
# import ledger, so a base can always say what read it.
PINNED_PYMUPDF = "1.26.5"
PINNED_MUPDF = "1.26.10"
PINNED_POPPLER = "26.03.0"

_WORD = re.compile(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ]+", re.UNICODE)


class ExtractorError(RuntimeError):
    pass


def _pymupdf():
    try:
        import fitz
    except ImportError as exc:
        raise ExtractorError(
            "PyMuPDF is not importable (%s). Expected %s / MuPDF %s."
            % (exc, PINNED_PYMUPDF, PINNED_MUPDF)
        )
    return fitz


def extractor_id():
    fitz = _pymupdf()
    version = getattr(fitz, "__version__", None) or "?"
    if version != PINNED_PYMUPDF:
        raise ExtractorError(
            "PyMuPDF %s is installed but the pipeline is pinned to %s.\n"
            "  Text extraction is not stable across MuPDF builds, so this is a\n"
            "  refusal, not a warning. Either install the pinned version or bump\n"
            "  PINNED_PYMUPDF *and* re-run the determinism check to see what moved."
            % (version, PINNED_PYMUPDF)
        )
    if PINNED_MUPDF not in (fitz.__doc__ or ""):
        raise ExtractorError(
            "PyMuPDF %s is not built against the pinned MuPDF %s (got: %r)"
            % (version, PINNED_MUPDF, (fitz.__doc__ or "").strip())
        )
    return "pymupdf %s / mupdf %s" % (version, PINNED_MUPDF)


def cross_checker_id():
    try:
        out = subprocess.run(
            ["pdftotext", "-v"], capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        raise ExtractorError(
            "pdftotext (poppler) not found. The cross-check is not optional: it\n"
            "  is the only thing standing between a mis-decoded glyph and a rule\n"
            "  that silently says the wrong number."
        )
    blob = (out.stderr or "") + (out.stdout or "")
    match = re.search(r"pdftotext version ([\d.]+)", blob)
    version = match.group(1) if match else "?"
    if version != PINNED_POPPLER:
        raise ExtractorError(
            "poppler pdftotext %s installed, pipeline pinned to %s"
            % (version, PINNED_POPPLER)
        )
    return "poppler pdftotext %s" % version


def normalise(text):
    """One text normalisation, used everywhere.

    NFC so that composed and decomposed accents cannot produce two different
    hashes for the same French word; a hard space is a space; runs of
    whitespace collapse but paragraph breaks survive.
    """
    text = unicodedata.normalize("NFC", text)
    text = text.replace(" ", " ").replace(" ", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def columns_of(blocks, page_width, span_ratio=0.7):
    """Group text blocks into reading order for a two-column page.

    MEASURED, not assumed: on SRD page 107 the left column starts at x=63 and
    the right at x=313.5, on a 594pt page.

    `get_text("text", sort=True)` is WRONG for this document and wrong in a way
    that looks plausible. It sorts every block by y then x across the FULL page
    width, so it reads one line of the left column, one line of the right, and
    back — interleaving two unrelated spells into a single stream. The damage
    is invisible in a word count and obvious in a spell name: it produced
    entries like "Acid Arrow designate creatures that won't set off the alarm".

    Caught by diffing the recovered spell names against an independent
    conversion of the same document. A page-level word-count check would have
    passed it: the same words are present, in the wrong order.

    Blocks wider than `span_ratio` of the page are treated as spanning both
    columns (section headers, wide tables) and keep their vertical position
    between the column groups they separate.
    """
    left, right, spanning = [], [], []
    mid = page_width / 2.0
    for block in blocks:
        x0, y0, x1, _y1, text = block[0], block[1], block[2], block[3], block[4]
        if not text.strip():
            continue
        if (x1 - x0) > span_ratio * page_width:
            spanning.append((y0, text))
        elif ((x0 + x1) / 2.0) < mid:
            left.append((y0, x0, text))
        else:
            right.append((y0, x0, text))

    ordered = [t for _, t in sorted(spanning, key=lambda b: b[0])]
    ordered += [t for _, _, t in sorted(left, key=lambda b: (b[0], b[1]))]
    ordered += [t for _, _, t in sorted(right, key=lambda b: (b[0], b[1]))]
    return ordered


def pages_pymupdf(pdf_path):
    fitz = _pymupdf()
    doc = fitz.open(pdf_path)
    try:
        pages = []
        for page in doc:
            blocks = page.get_text("blocks")
            ordered = columns_of(blocks, page.rect.width)
            pages.append(normalise("\n".join(ordered)))
        return pages
    finally:
        doc.close()


def pages_pdftotext(pdf_path):
    out = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8", pdf_path, "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    # pdftotext separates pages with a form feed.
    return [normalise(p) for p in out.stdout.split("\f")]


def words(text):
    return _WORD.findall(text.lower())


def compare_pages(a_pages, b_pages):
    """Word-level agreement per page between the two extractors.

    Compared on words, not characters: the two tools legitimately differ on
    line breaks, column order and hyphenation, and none of that changes what a
    rule says. A dropped or mangled *word* does.

    Returns a list of per-page dicts, worst agreement first.
    """
    report = []
    for i in range(max(len(a_pages), len(b_pages))):
        a = words(a_pages[i]) if i < len(a_pages) else []
        b = words(b_pages[i]) if i < len(b_pages) else []
        only_a, only_b = [], []
        if not a and not b:
            # Both extractors agree the page carries no text (a plate, or the
            # blank verso of a section break). Agreement, not absence of data.
            agreement = 1.0
        else:
            ca, cb = Counter(a), Counter(b)
            shared = sum((ca & cb).values())
            agreement = (2.0 * shared) / (len(a) + len(b))
            only_a = sorted((ca - cb).elements())
            only_b = sorted((cb - ca).elements())
        report.append(
            {
                "page": i + 1,
                "agreement": round(agreement, 4),
                "words_pymupdf": len(a),
                "words_pdftotext": len(b),
                "only_pymupdf": only_a[:12],
                "only_pdftotext": only_b[:12],
            }
        )
    return report


def extract(pdf_path, min_agreement=0.98):
    """Extract, cross-check, and hand back both the text and the suspect pages.

    `min_agreement` is a threshold, not a verdict: pages below it are returned
    as `suspect` so the importer can route the records they contain to the
    exclusion register. Nothing is silently dropped and nothing is silently
    kept.
    """
    primary = pages_pymupdf(pdf_path)
    witness = pages_pdftotext(pdf_path)
    report = compare_pages(primary, witness)
    suspect = [r for r in report if r["agreement"] < min_agreement]
    return {
        "extractor": extractor_id(),
        "cross_checker": cross_checker_id(),
        "pages": primary,
        "page_count": len(primary),
        "comparison": report,
        "suspect_pages": sorted(suspect, key=lambda r: r["agreement"]),
        "min_agreement": min_agreement,
    }
