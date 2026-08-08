"""The witness for the repaired two-column reading order.

A synthetic fixture proves a function does what its author thought. It cannot
answer "is the reading order RIGHT?", because the author of the fixture and the
author of the rule are the same person. So this suite asks a second, unrelated
renderer — poppler's `pdftotext -layout`, which shares no code with MuPDF and
lays the page out by its own geometry engine — and confronts it.

TWO CONFRONTATIONS, both exact and both over the whole document:

  1. **PLACEMENT.** For every full-width table in both PDFs, every column block
     printed entirely above it must come out before it, and every column block
     printed entirely below it must come out after it — in POPPLER's linear
     rendering as well as in ours. This is the claim the old code got wrong:
     it emitted every wide block at the top of the page whatever its vertical
     position, which is how `srd:species:en:human` acquired the Tiefling's
     table and how each class record acquired the NEXT class's level table.

  2. **CELLS.** For each of the four species lineage tables, every row's Level 3
     and Level 5 spell must appear on one physical poppler line, separated by
     real whitespace and in that left-to-right order. This is what says
     "Longstrider" and "Pass without Trace" are two cells and not one string —
     the defect that made the previous lot refuse the field.

⚠️ THIS SUITE FAILS WHEN IT CANNOT RUN. It does not skip. The previous witness
in this repository exited 0 when the PDFs were absent, so a green run meant
either "confronted and agreed" or "did nothing", and nobody could tell which
without reading the output. Every refusal below is an AssertionError, and the
counts are printed so a run that confronted less than it should is visible.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import extract  # noqa: E402

PDFS = [
    ("en", os.path.join(ROOT, "sources", "pdf", "SRD_CC_v5.2.1.pdf")),
    ("fr", os.path.join(ROOT, "sources", "pdf", "FR_SRD_CC_v5.2.1.pdf")),
]

# The four tables the lineages are read from, by page (1-based) and caption.
LINEAGE_TABLES = [
    ("en", 85, "Elven Lineages"),
    ("en", 86, "Fiendish Legacies"),
    ("fr", 89, "Lignages elfiques"),
    ("fr", 91, "Héritages fiélons"),
]

# Below this the witness has not witnessed anything and says so.
MIN_PLACEMENTS = 200


def require_sources():
    missing = [path for _lang, path in PDFS if not os.path.exists(path)]
    if missing:
        raise AssertionError(
            "the pinned PDFs are not present:\n  %s\n"
            "This suite confronts the extractor against a second renderer of the "
            "SAME bytes. Without them it cannot confront anything, and a witness "
            "that cannot run must FAIL rather than pass quietly."
            % "\n  ".join(missing)
        )


def poppler_page(path, number):
    out = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8",
         "-f", str(number), "-l", str(number), path, "-"],
        capture_output=True, text=True, check=True,
    )
    return [extract.normalise(line) for line in out.stdout.split("\n")]


def index_of(lines, needle):
    """The single line index carrying `needle`, or None if it is not unique."""
    if not needle:
        return None
    hits = [i for i, line in enumerate(lines) if needle in line]
    return hits[0] if len(hits) == 1 else None


def locate(rendered, block_text):
    """Where poppler put this block: the first of its lines that pins uniquely.

    Trying only the block's FIRST line found 79 confrontations across both
    documents, below this suite's own floor — poppler re-wraps, and a block's
    opening line is often a short one that recurs. Trying each line in turn,
    longest first, and taking the first that appears exactly once raises it
    without weakening the claim: a unique line is a unique line whichever one
    of the block's lines it is.
    """
    lines = [l for l in extract.normalise(block_text).split("\n") if len(l) > 12]
    for candidate in sorted(lines, key=len, reverse=True):
        at = index_of(rendered, candidate)
        if at is not None:
            return at, candidate
    return None, None


def placement(fitz):
    """Confrontation 1, over both documents."""
    confronted = agreed = 0
    pages_with_tables = 0
    for lang, path in PDFS:
        doc = fitz.open(path)
        try:
            for number, page in enumerate(doc, start=1):
                blocks = page.get_text("blocks")
                runs, left, right = extract._runs(
                    blocks, page.rect.width, page.rect.height, 0.93,
                    extract.RUN_GAP, extract.GROW_GAP)
                if not runs:
                    continue
                pages_with_tables += 1
                rendered = poppler_page(path, number)
                for run in runs:
                    top = min(b[0] for b in run)
                    bottom = max(b[2] for b in run)
                    anchor, anchor_text = locate(
                        rendered, "\n".join(b[4] for b in run))
                    if anchor is None:
                        continue
                    for block in left + right:
                        at, first = locate(rendered, block[4])
                        if at is None or at == anchor:
                            continue
                        if block[2] <= top:
                            expected = "before"
                        elif block[0] >= bottom:
                            expected = "after"
                        else:
                            continue
                        confronted += 1
                        got = "before" if at < anchor else "after"
                        assert got == expected, (
                            "%s p.%d: %r is printed %s the table starting %r "
                            "(y %.1f vs %.1f-%.1f) but poppler renders it %s"
                            % (lang, number, first[:60], expected, anchor_text[:40],
                               block[0], top, bottom, got))
                        agreed += 1
        finally:
            doc.close()
    return confronted, agreed, pages_with_tables


def cells(fitz):
    """Confrontation 2, over the four lineage tables."""
    checked = 0
    for lang, number, caption in LINEAGE_TABLES:
        path = dict(PDFS)[lang]
        doc = fitz.open(path)
        try:
            page = doc[number - 1]
            tables = [t for t in extract.tables_of(page) if t.get("caption") == caption]
        finally:
            doc.close()
        assert len(tables) == 1, (
            "%s p.%d: expected exactly one table captioned %r, got %d"
            % (lang, number, caption, len(tables)))
        table = tables[0]
        assert "defect" not in table, (
            "%s p.%d: %r came back with a defect: %s" % (lang, number, caption, table["defect"]))

        raw = subprocess.run(
            ["pdftotext", "-layout", "-enc", "UTF-8",
             "-f", str(number), "-l", str(number), path, "-"],
            capture_output=True, text=True, check=True).stdout
        lines = raw.split("\n")

        for row in table["rows"]:
            level3, level5 = row[-2].strip(), row[-1].strip()
            hits = [l for l in lines if level3 in l and level5 in l
                    and l.index(level3) < l.index(level5)]
            assert len(hits) >= 1, (
                "%s p.%d row %r: poppler does not render %r and %r on one line in that "
                "order, so they are not two cells of one row" % (lang, number, row[0], level3, level5))
            line = hits[0]
            between = line[line.index(level3) + len(level3):line.index(level5)]
            assert between.strip() == "" and len(between) >= 2, (
                "%s p.%d row %r: only %r separates %r from %r; a cell boundary needs "
                "real column whitespace, not a single space"
                % (lang, number, row[0], between, level3, level5))
            checked += 1
    return checked


def main():
    require_sources()
    extract.extractor_id()      # refuses on an unpinned MuPDF
    extract.cross_checker_id()  # refuses on an unpinned poppler
    fitz = extract._pymupdf()

    confronted, agreed, pages = placement(fitz)
    assert confronted >= MIN_PLACEMENTS, (
        "only %d placements were confronted (floor is %d). The witness ran and "
        "found almost nothing to check, which is a failure, not a pass."
        % (confronted, MIN_PLACEMENTS))
    assert agreed == confronted
    print("  ok  placement: %d block/table orderings on %d pages with tables, "
          "poppler agrees with every one" % (confronted, pages))

    checked = cells(fitz)
    assert checked == 12, "expected 12 lineage rows, confronted %d" % checked
    print("  ok  cells: %d lineage rows, each with its two spells on one poppler line, "
          "in order, separated by column whitespace" % checked)

    # -- NEGATIVE CONTROL ----------------------------------------------------
    # The placement check compares "before/after"; prove it can say no.
    failed = False
    try:
        rendered = poppler_page(PDFS[0][1], 86)
        a = index_of(rendered, "Fiendish Legacies")
        b = index_of(rendered, "Versatile. You gain an Origin feat of your choice")
        assert a is not None and b is not None
        assert a < b, "poppler puts the table BEFORE the Human's last trait"
    except AssertionError:
        failed = True
    assert failed, (
        "the negative control passed: poppler was asked to confirm the pre-repair "
        "order (the Tiefling's table above the Human's text) and did not refuse it, "
        "so this witness is not measuring what it claims to")
    print("  ok  negative control: poppler refuses the pre-repair order on EN p.86")

    print("PASS test_extract_columns_witness")


if __name__ == "__main__":
    main()
