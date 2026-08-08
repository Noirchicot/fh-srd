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

    PyMuPDF merges a whole multi-paragraph passage (a spell's description, an
    item's, a feat's) into ONE block, and marks where the second and later
    paragraphs start with a literal tab -- the printed first-line indent --
    right after the newline: "...one.\n\t Flammable objects...". A table
    row's tab is never in that position; it sits mid-line ("Str\t18 +4"), so
    it is untouched by this. Left alone, the plain `[ \t]+` collapse below
    would eat that tab and turn a paragraph break into a same-paragraph line
    wrap -- invisible, and indistinguishable from real wrapping once done. So
    a line-initial tab is promoted to a blank line BEFORE the general
    whitespace collapse would erase the only signal that one was there.

    FOUND CALIBRATING THE CLASS PARSER, not something the spell/item/feat
    passes had a reason to trip over: WotC's own layout engine hyphenates a
    handful of words with a SOFT hyphen (U+00AD) rather than a plain "-" --
    "Meta\xadmagic", "Short\xadsword", "spell\xadcasters" -- mid-word, not at a
    line break, so the existing line-by-line dehyphenator (which only acts on
    a plain "-" at a line's END) never sees it. Left alone it survives into
    the exported text as an invisible character sitting inside an otherwise
    ordinary word. A soft hyphen is a print-time hint for where a word MAY
    break, never a character that should render; the correct reading is
    "Metamagic", not "Meta\xadmagic". Stripped outright, unconditionally --
    unlike a real hyphen it carries no information this pipeline should keep.
    """
    text = text.replace("­", "")
    text = unicodedata.normalize("NFC", text)
    text = text.replace(" ", " ").replace(" ", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n\t[ \t]*", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# A page is two-column in some vertical bands and full-width in others. These
# three numbers say where one regime ends and the other begins. Every one of
# them was measured on the two pinned PDFs; the measurements are in
# `columns_of`'s docstring and re-asserted by tests/test_extract_columns.py.
RUN_GAP = 12.0    # vertical gap that still counts as "the same full-width table"
GROW_GAP = 10.0   # vertical gap across which a caption still belongs to its table

# An entry's head line, in the source's own typography. MEASURED on both pinned
# PDFs: 1373 lines in EN and 1377 in FR are set wholly in GillSans-SemiBold at
# 12pt, and every one of them is the title of an entry -- a spell, a magic item,
# a class feature, a tool, a glossary term. A table CAPTION is the same face at
# 10.5pt and a table's column header at 9.25pt, so the size separates them
# cleanly; chapter and section heads are 26pt and 18pt.
HEAD_FONT = "GillSans-SemiBold"
HEAD_SIZE = 12.0

# A block's own bbox, compared between `get_text("blocks")` and
# `get_text("dict")`. They agree to well under a point; half a point is slack.
ANCHOR_TOL = 0.5

# Below this, a caption is too short to identify anything.
MIN_CAPTION = 4


def _classify(blocks, page_width, page_height, margin_ratio):
    """Split blocks into (spanning, left, right), dropping the running footer."""
    mid = page_width / 2.0
    spanning, left, right = [], [], []
    for block in blocks:
        x0, y0, x1, y1, text = block[0], block[1], block[2], block[3], block[4]
        # `text` is a string from `get_text("blocks")` and a list of lines from
        # `tables_of`. Both classify the same way; only emptiness differs.
        if not (text.strip() if isinstance(text, str) else text):
            continue
        if page_height and y0 > page_height * margin_ratio:
            # Running footer ("Document de Référence du Système 5.2.1 118").
            # It has to go, and not merely be sorted late: concatenating left
            # column then right column puts a page-bottom block in the MIDDLE
            # of the page's text, which then lands inside a spell description
            # once pages are read as one continuous stream.
            continue
        entry = (y0, x0, y1, x1, text)
        if x0 < mid < x1:
            spanning.append(entry)
        elif ((x0 + x1) / 2.0) < mid:
            left.append(entry)
        else:
            right.append(entry)
    return spanning, left, right


def _runs(blocks, page_width, page_height, margin_ratio, run_gap, grow_gap):
    """Full-width table runs, plus what is left of each column.

    The four steps are documented in `columns_of`, which is the only place they
    are explained; `tables_of` needs the same runs and must not re-derive them
    from a second, drifting copy of the rule.
    """
    spanning, left, right = _classify(blocks, page_width, page_height, margin_ratio)

    spanning.sort(key=lambda b: (b[0], b[1]))
    runs = []
    for block in spanning:
        if runs and block[0] - max(b[2] for b in runs[-1]) < run_gap:
            runs[-1].append(block)
        else:
            runs.append([block])

    # Step 3. A block printed inside the table's own vertical extent is one of
    # its cells. Done before step 4 so that a stray cell cannot masquerade as
    # the opposite-column neighbour that blocks a caption from being absorbed.
    def swallow(run, column):
        top = min(b[0] for b in run)
        bottom = max(b[2] for b in run)
        inside = [b for b in column if b[0] >= top and b[2] <= bottom]
        run.extend(inside)
        column[:] = [b for b in column if not (b[0] >= top and b[2] <= bottom)]

    for run in runs:
        swallow(run, left)
        swallow(run, right)

    # Step 4. Indices, not values: two blocks with identical geometry and text
    # would compare equal, and removing "a block equal to this one" from a list
    # is not the same as removing this one.
    def absorb(run, column, opposite):
        while True:
            top = min(b[0] for b in run)
            best = None
            for i, block in enumerate(column):
                if block[2] > top or top - block[2] >= grow_gap:
                    continue
                if best is None or block[2] > column[best][2]:
                    best = i
            if best is None:
                return
            block = column[best]
            if any(not (o[2] <= block[0] or o[0] >= block[2]) for o in opposite):
                return
            run.append(block)
            column.pop(best)

    for run in runs:
        absorb(run, left, right)
        absorb(run, right, left)

    left.sort(key=lambda b: (b[0], b[1]))
    right.sort(key=lambda b: (b[0], b[1]))
    runs.sort(key=lambda run: min(b[0] for b in run))
    for run in runs:
        run.sort(key=lambda b: (b[0], b[1]))
    return runs, left, right


def _flat(text):
    """`normalise`, with every line break flattened to a single space.

    A caption printed on one line of a table is printed as ordinary prose in
    the entry that cross-references it, and prose wraps: the source says
    "functions as shown in the Apparatus of the Crab\nLevers table", so
    searching for the caption in the block's normalised text finds nothing.
    Flattening is only ever used for MATCHING; no flattened string is emitted.
    """
    return re.sub(r"\s+", " ", normalise(text)).strip()


def entry_heads(page):
    """Every entry head line on the page, as (text, block bbox).

    A head is a line set WHOLLY in `HEAD_FONT` at `HEAD_SIZE` -- wholly,
    because "Creature Type: Humanoid" puts a semibold label and a regular value
    on one line and is not a head, and because a spell name that shares its
    line with anything else is not one either. The bbox returned is the BLOCK's,
    not the line's: what an anchor needs is the block a head opens.
    """
    heads = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", ()):
            whole = _flat("".join(span["text"] for span in line["spans"]))
            head = _flat("".join(
                span["text"] for span in line["spans"]
                if span["font"] == HEAD_FONT
                and abs(span["size"] - HEAD_SIZE) < 0.01
            ))
            if whole and head == whole:
                heads.append((whole, tuple(block["bbox"])))
    return heads


def _head_at(block, heads):
    """The head text a column block opens, or None. `block` is a `_classify`
    entry, so its coordinates are (y0, x0, y1, x1)."""
    for text, bbox in heads:
        if (abs(block[0] - bbox[1]) <= ANCHOR_TOL
                and abs(block[1] - bbox[0]) <= ANCHOR_TOL):
            return text
    return None


def _anchor_of(run, left, right, heads):
    """The entry a page-foot float belongs to, or None. See `float_anchors`."""
    bottom = max(b[2] for b in run)
    if any(b[0] >= bottom for b in left + right):
        return None                       # something is printed below it
    top = min(b[0] for b in run)
    caption = _flat(normalise(run[0][4]).split("\n")[0])
    if len(caption) < MIN_CAPTION:
        return None

    owners = []
    for column, name in ((left, "left"), (right, "right")):
        for index, block in enumerate(column):
            if block[0] >= top:
                continue
            head = _head_at(block, heads)
            if head is None or len(head) < MIN_CAPTION:
                continue
            if not (caption == head or caption.startswith(head + " ")):
                continue
            end = len(column)
            for j in range(index + 1, len(column)):
                if column[j][0] >= top or _head_at(column[j], heads) is not None:
                    end = j
                    break
            body = column[index + 1:end]
            if not any(caption in _flat(b[4]) for b in body):
                continue                  # the entry never points at the table
            owners.append((name, column[end - 1], head))

    if not owners:
        return None
    if len(owners) > 1:
        raise ExtractorError(
            "the full-width table captioned %r is claimed by %d entries on one "
            "page (%s). Two entries cannot own one float, and guessing which "
            "would put a table into a record that does not print it. Nothing "
            "has been re-anchored and the extraction is stopping here."
            % (caption, len(owners), ", ".join(repr(o[2]) for o in owners))
        )
    return owners[0][0], owners[0][1]


def float_anchors(page, run_gap=RUN_GAP, grow_gap=GROW_GAP, margin_ratio=0.93):
    """Where each re-anchored page-foot float belongs, as (run top, column, y).

    THE DEFECT THIS REPAIRS, and it was published. `columns_of` reads a page in
    its PRINTED order, which is right for a table printed under the entry it
    belongs to and wrong for one that has floated to the foot of the page away
    from it. EN p.210 prints the "Apparatus of the Crab Levers" table full-width
    at the page foot, below both columns. The Apparatus's own entry is the whole
    LEFT column; the right column holds three unrelated magic items, the last of
    which is Armor of Resistance. Printed order therefore appended a ten-row
    lever table to Armor of Resistance, and `srd:item:en:armor-of-resistance`
    shipped 1581 characters of which 1294 belonged to another item.

    This is not a reading-order defect -- the order IS the page's. It is an
    ANCHORING defect, and repairing it needs the source to say who owns the
    table. It says so TWICE, and this function requires both statements:

    1. **The caption names the entry, typographically.** "Apparatus of the Crab
       Levers" begins with "Apparatus of the Crab", which is printed on the same
       page as a head line -- `HEAD_FONT` at `HEAD_SIZE`, the face and size the
       source uses for an entry title and for nothing else.

    2. **The entry names the caption, in its own prose.** The Apparatus's text
       ends "Each lever, from left to right, functions as shown in the Apparatus
       of the Crab Levers table." The reference is printed; it is not inferred.

    WHY BOTH, MEASURED. Signal 1 alone fires three times over the two documents
    and two of them are wrong: "Shield (Utilize Action to Don or Doff)" and
    "Bouclier (s'enfile ou se retire au prix de l'action Utilisation)" are
    SUB-CATEGORY LABELS inside the Armor table, and they begin with the name of
    the Shield armor entry printed higher on the same page. Re-anchoring on
    signal 1 alone would tear those labels out of the Armor table and drop them
    into the Shield record. Neither is cross-referenced by any entry, so signal
    2 refuses both.

    Signal 2 alone is worse: it fires on six page-foot floats, and one of them
    -- FR p.91 "Héritages fiélons" -- is ALREADY CORRECTLY PLACED. The Tiefling
    entry spans both columns and its cross-reference sits in the left one, so
    anchoring on the reference would have moved the table into the MIDDLE of the
    record it already ends. A cross-reference says which table an entry uses; it
    does not say where the table is printed.

    Together they fire ONCE over 744 pages and 66 full-width runs: EN p.210.
    That count is the measurement, not the target -- the rule is evaluated
    against every run in both documents and reported by
    `tests/test_float_anchoring.py`, which re-derives it from the PDFs.

    THE THREE THINGS IT WILL NOT DO:

      * It never re-anchors a run with anything printed below it on the page. A
        float that still has column text under it has not floated away from
        anything, and moving it would reorder a page that reads correctly.
      * It never moves text between pages. The owning entry must have its head
        ON the page that carries the table.
      * Two entries claiming one caption is an `ExtractorError`, not a choice.
        It does not happen on either pinned source; if a future one makes it
        happen, the build stops instead of picking.

    The anchor point is the END of the owning entry -- its head block and every
    block under it in the same column, up to the next head -- so the table lands
    where the entry ends and not where its cross-reference happens to sit.
    """
    blocks = page.get_text("blocks")
    runs, left, right = _runs(blocks, page.rect.width, page.rect.height,
                              margin_ratio, run_gap, grow_gap)
    heads = entry_heads(page)
    anchors = []
    for run in runs:
        anchor = _anchor_of(run, left, right, heads)
        if anchor is not None:
            anchors.append((min(b[0] for b in run), anchor[0], anchor[1][0]))
    return anchors


def columns_of(blocks, page_width, page_height=None, margin_ratio=0.93,
               run_gap=RUN_GAP, grow_gap=GROW_GAP, anchors=()):
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

    WHAT THIS FUNCTION USED TO DO, AND THE BUG IT SHIPPED. Until 2026-08-08 a
    block counted as spanning if it was wider than 0.7 of the page, and every
    spanning block on a page was emitted BEFORE both columns — flatly, at the
    top, whatever its vertical position. The docstring claimed they "keep their
    vertical position between the column groups they separate"; the code did
    not do that. Two defects followed, and both reached the published site:

      * A full-width table printed at the BOTTOM of a page (the Tiefling's
        "Fiendish Legacies", EN p.86) was hoisted above the whole page, and a
        table printed at the TOP (the Elf's "Elven Lineages", EN p.85) stayed
        at the top only by accident. Reading order was decided by block width,
        not by the page.
      * A table narrower than the 0.7 threshold but still crossing the gutter
        was filed as *column* text. "Legacy / Level 1 / Level 3 / Level 5" is
        398pt on a 594pt page — 0.67 — so the Tiefling's whole legacy table
        landed in the LEFT column, after the Human's description and before
        the Tiefling's own head line. `srd:species:en:human` shipped 541
        characters ending in the Tiefling's table.

    WHAT IT DOES NOW. A page is two-column in some vertical bands and
    full-width in others; the function models that instead of sorting by width.

    1. **Spanning is crossing the gutter, not being wide.** A block spans when
       it starts left of the page's vertical mid-line and ends right of it.
       Measured on both pinned PDFs: every block the old 0.7-width rule called
       spanning also crosses the mid-line (324 of 324 in EN, 326 of 326 in FR),
       so this is a strict widening and not a different rule — it adds 61 EN
       and 58 FR blocks that were wide tables all along. It is safe because the
       gutter is empty: the left column ends at x≈292 and the right begins at
       x=313.5, with the mid-line 297 between them, so ordinary body text never
       crosses it.

    2. **Adjacent spanning blocks form a run** — one table. `run_gap` is 12pt.
       Measured: consecutive spanning blocks inside one table are never more
       than 7.4pt apart in either document, and the smallest gap that is a real
       interruption is 18.75pt (a sub-category label sitting between two rows
       of the Weapons table). 12 sits in the empty space between the two.

    3. **A run swallows anything printed inside it.** A block whose whole
       vertical extent falls within the run's is a CELL of that table, not
       column text — a full-width table occupies the page at that height, so
       nothing can be printed beside it. This is what the French tables need
       and the English ones mostly do not: FR wraps its Level 1 cell onto more
       lines than EN does, which pushes the Level 3 / Level 5 cells out into
       their own block at x=346.7 or x=360 — right of the mid-line, and so
       filed as *right column* and emitted at the end of the page. That is why
       `srd:species:fr:tieffelin` shipped with a bare "rayon empoisonné
       immobilisation de personne" dangling after its own prose.

    4. **A run absorbs the caption printed above it.** `grow_gap` is 10pt, but
       the load-bearing condition is the second one: a block joins the run only
       if NO block of the opposite column overlaps it vertically — that is, only
       if the page is not in two-column mode at that height. Gap alone cannot
       decide it (ordinary same-column paragraph gaps have median 4.9pt and 90th
       percentile 7.9pt, squarely inside the caption range of 3.2–7.4pt). This
       is what moves "Fiendish Legacies" off the end of the Human's description
       and onto the front of its own table.

    5. **Runs cut the page into bands.** For each run in vertical order: emit
       the left-column blocks above it, then the right-column blocks above it,
       then the run itself. Then whatever is left, left column before right.
       On a page with no spanning block at all — 341 of 364 EN pages, 357 of
       380 FR — this reduces exactly to the old left-then-right order, which is
       why the vast majority of the document does not move.

    6. **A float that has floated away from its entry is put back.** Steps 1–5
       give the page's PRINTED order, and that is the right order for a table
       printed under the entry it belongs to. It is the wrong one for a table
       pushed to the foot of the page past three unrelated entries — which is
       how `srd:item:en:armor-of-resistance` shipped the Apparatus of the
       Crab's lever table. `anchors` comes from `float_anchors`, which decides
       ownership from what the source PRINTS about it and defaults to empty:
       given no anchors this function is exactly steps 1–5.
    """
    return _ordered(blocks, page_width, page_height, margin_ratio,
                    run_gap, grow_gap, anchors)


def _ordered(blocks, page_width, page_height, margin_ratio, run_gap, grow_gap,
             anchors=()):
    """Block payloads in reading order. `columns_of`'s docstring is the rule."""
    runs, left, right = _runs(blocks, page_width, page_height, margin_ratio,
                              run_gap, grow_gap)

    ordered = []
    for run in runs:
        top = min(b[0] for b in run)
        anchor = next(((name, y) for at, name, y in anchors
                       if abs(at - top) <= ANCHOR_TOL), None)
        if anchor is not None:
            # Emit the owning entry, then its table, and leave the rest of the
            # page to follow. Everything still comes out exactly once.
            column = left if anchor[0] == "left" else right
            while column and column[0][0] <= anchor[1]:
                ordered.append(column.pop(0)[4])
            ordered += [b[4] for b in run]
            continue
        while left and left[0][0] < top:
            ordered.append(left.pop(0)[4])
        while right and right[0][0] < top:
            ordered.append(right.pop(0)[4])
        ordered += [b[4] for b in run]
    ordered += [b[4] for b in left]
    ordered += [b[4] for b in right]
    return ordered


BAND_TOL = 2.0    # two lines printed on the same visual row of a table
COLUMN_TOL = 3.0  # a cell's left edge against its column's declared left edge


def tables_of(page, run_gap=RUN_GAP, grow_gap=GROW_GAP, margin_ratio=0.93):
    """Full-width tables on a page, read as CELLS rather than as text.

    WHY THIS EXISTS BESIDE `columns_of` AND NOT INSTEAD OF IT. Repairing the
    reading order gets a table's rows into the right place and the right order.
    It cannot get them into the right *cells*, because a cell boundary is not a
    line boundary: once the page is flattened to text, "Longstrider" and "Pass
    without Trace" are two consecutive lines and so are the two halves of a
    wrapped sentence. The species parser joins the lines of a paragraph with a
    space and produces "grande foulée passage sans trace" — two spell names run
    together, which is the defect the lot-8 measurement named.

    TEXT ALONE CANNOT SEPARATE THEM, and that is measured rather than assumed.
    The obvious rule — "a Level 1 cell ends in a full stop, so the two lines
    after the full stop are the Level 3 and Level 5 spells" — fails on the very
    first row of the French table: Drow's Level 1 cell wraps as "La portée de
    votre Vision dans le noir passe à 36 m." / "Vous connaissez également le
    sort mineur lumières" / "dansantes.", and the first of those lines ends in a
    full stop three lines early. What separates the cells is x: 66.6 for the
    lineage name, 117.4 for Level 1, 360.0 for Level 3, 451.8 for Level 5.

    So this reads geometry, from the same runs `columns_of` builds, and hands
    back cells. It is ADDITIVE: nothing about the text stream changes, and a
    parser that does not ask for tables sees exactly what it saw before.

    Returns a list of `{"caption", "columns", "rows"}`, one per full-width table
    on the page, in printed order. `caption` is None when the run has no caption
    line. `rows` is a list of lists of cell strings, one per declared column.

    THE THREE THINGS IT REFUSES TO GUESS, each returning the table with a
    `"defect"` key rather than a silently plausible shape:

      * a header band that does not resolve into at least two columns;
      * a row that puts two lines in the last column (which would mean the row
        split is wrong, since every table here holds one spell name per level);
      * a line whose left edge matches no declared column within COLUMN_TOL.

    THE ROW SPLIT IS ANCHORED ON THE LAST COLUMN, not the first. The first
    column looks like the natural anchor and is not: the French Elf table wraps
    "Elfe sylvestre" onto two lines at the SAME left edge, so counting rows by
    first-column lines yields four rows for a three-row table. The last column
    holds exactly one short line per row in every table this reads, which is
    asserted rather than trusted.

    CALIBRATED FOR THE SPECIES LINEAGE TABLES, AND IT SAYS SO RATHER THAN
    PRETENDING OTHERWISE. Swept over both pinned PDFs it finds 34 EN and 32 FR
    full-width tables and reports a defect on 31 and 27 of them. That is the
    intended behaviour, not a failure rate: the Weapons and Armor tables
    right-ALIGN their Weight and Cost columns, so a cell's left edge moves with
    the width of its own text and a left-edge anchor cannot address it; the
    class-progression tables split across more than one run. Those tables have
    working parsers already and this function is not their route. What matters
    is that it never returns a plausible wrong shape for them — every one of
    those tables comes back marked, and the four it is calibrated for (Elven
    Lineages and Fiendish Legacies, both languages) come back clean.
    """
    blocks = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        lines = []
        for line in block.get("lines", ()):
            text = normalise("".join(span["text"] for span in line["spans"]))
            if text:
                lines.append((round(line["bbox"][0], 2), round(line["bbox"][1], 2), text))
        if not lines:
            continue
        x0, y0, x1, y1 = block["bbox"]
        blocks.append((x0, y0, x1, y1, lines))

    runs, _left, _right = _runs(blocks, page.rect.width, page.rect.height,
                                margin_ratio, run_gap, grow_gap)

    tables = []
    for run in runs:
        lines = sorted((line for block in run for line in block[4]),
                       key=lambda l: (l[1], l[0]))
        tables.append(_table_from_lines(lines))
    return tables


def _bands(lines):
    """Group lines printed on the same visual row (`BAND_TOL` apart in y)."""
    bands = []
    for line in lines:
        if bands and line[1] - bands[-1][0] <= BAND_TOL:
            bands[-1][1].append(line)
        else:
            bands.append((line[1], [line]))
    return [sorted(band, key=lambda l: l[0]) for _y, band in bands]


def _table_from_lines(lines):
    bands = _bands(lines)
    caption = None
    header_at = 0
    if bands and len(bands[0]) == 1:
        caption = bands[0][0][2]
        header_at = 1
    if header_at >= len(bands) or len(bands[header_at]) < 2:
        return {"caption": caption, "columns": [], "rows": [],
                "defect": "no header band with two or more columns"}

    header = bands[header_at]
    anchors = [line[0] for line in header]
    columns = [line[2] for line in header]

    def column_of(x0):
        best, distance = None, None
        for index, anchor in enumerate(anchors):
            gap = abs(x0 - anchor)
            if distance is None or gap < distance:
                best, distance = index, gap
        return best if distance is not None and distance <= COLUMN_TOL else None

    body = [line for band in bands[header_at + 1:] for line in band]
    starts = sorted(line[1] for line in body if column_of(line[0]) == len(anchors) - 1)
    if not starts:
        return {"caption": caption, "columns": columns, "rows": [],
                "defect": "no line in the last column to anchor a row on"}

    rows, defect = [], None
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else None
        cells = [[] for _ in anchors]
        for x0, y0, text in body:
            if y0 < start - BAND_TOL:
                continue
            if end is not None and y0 >= end - BAND_TOL:
                continue
            column = column_of(x0)
            if column is None:
                defect = defect or ("line %r sits at x=%.1f, matching no column" % (text, x0))
                continue
            cells[column].append(text)
        if len(cells[-1]) != 1:
            defect = defect or (
                "row %d puts %d lines in the last column; the row split is wrong"
                % (index + 1, len(cells[-1])))
        rows.append([" ".join(cell) for cell in cells])

    table = {"caption": caption, "columns": columns, "rows": rows}
    if defect:
        table["defect"] = defect
    return table


def pages_pymupdf(pdf_path):
    fitz = _pymupdf()
    doc = fitz.open(pdf_path)
    try:
        pages = []
        for page in doc:
            blocks = page.get_text("blocks")
            ordered = columns_of(blocks, page.rect.width, page.rect.height,
                                 anchors=float_anchors(page))
            pages.append(normalise("\n".join(ordered)))
        return pages
    finally:
        doc.close()


# Bold AND italic, in PyMuPDF's own span flags (16 = bold, 2 = italic).
BOLD_ITALIC = 16 | 2


def emphasis_of(page, run_gap=RUN_GAP, grow_gap=GROW_GAP, margin_ratio=0.93):
    """The page's bold-italic phrases, in reading order.

    WHY A FONT AND NOT A SENTENCE SHAPE. A species' traits are printed as
    "Name. Text", and in ENGLISH each one starts its own paragraph, so the
    paragraph break alone would find them. In FRENCH it does not: the whole Elf
    entry arrives as ONE paragraph — "…traits spéciaux suivants. Ascendance
    féerique. Vous avez l'Avantage… mettre un terme. Lignage elfique. Vous
    appartenez…" — with no break anywhere between the five traits. Splitting
    that on "a short phrase before a full stop" is the Rules Glossary's trap
    with none of the Rules Glossary's defences: there is no line start to
    anchor on and no alphabetical safety net, and the entry is full of ordinary
    sentences that would qualify.

    What the source does state, unambiguously and in both languages, is
    typographic: a trait name is set in Cambria-BoldItalic and nothing else in
    the entry is. Measured over the species chapter: 33 bold-italic runs in EN
    and 33 in FR, and every one of them is a trait name — no sentence, no
    heading and no table cell qualifies. Spell names ARE italicised in this
    chapter ("le sort mineur *druidisme*") and are correctly not matched,
    because they are italic without being bold.

    Runs are joined across span and line boundaries, so a name that wraps comes
    back whole.
    """
    entries = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        phrases, current = [], []
        for line in block.get("lines", ()):
            for span in line["spans"]:
                if (span["flags"] & BOLD_ITALIC) == BOLD_ITALIC:
                    current.append(span["text"])
                elif current:
                    phrases.append("".join(current))
                    current = []
        if current:
            phrases.append("".join(current))
        if not phrases:
            continue
        x0, y0, x1, y1 = block["bbox"]
        entries.append((x0, y0, x1, y1, phrases))

    # The same anchors the text stream uses. A re-anchored float carries its
    # own emphasis with it, so the two streams cannot disagree about the
    # document's order -- which is load-bearing, because the species parser
    # consumes this stream once, in order, against the text.
    ordered = _ordered(entries, page.rect.width, page.rect.height,
                       margin_ratio, run_gap, grow_gap, float_anchors(page))
    out = []
    for phrases in ordered:
        for phrase in phrases:
            phrase = normalise(phrase).strip()
            if phrase:
                out.append(phrase)
    return out


def layout_pymupdf(pdf_path):
    """Per page: the geometry the text stream cannot carry.

    `tables` are cell-separated readings of the page's full-width tables;
    `emphasis` are its bold-italic phrases in reading order. Both are ADDITIVE
    — the text stream is untouched — and both exist because a cell boundary and
    a font change are facts the source states and a flattened string cannot.
    """
    fitz = _pymupdf()
    doc = fitz.open(pdf_path)
    try:
        return [{"tables": tables_of(page), "emphasis": emphasis_of(page)}
                for page in doc]
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
    """Tokens for comparison, with ordinals normalised.

    PyMuPDF emits "3e" as one token where pdftotext splits it. That is a
    difference between the two TOOLS, not between two readings of the source,
    and left alone it pushed eight pages below the agreement threshold for no
    real reason. A cross-check that flags its own tooling teaches you to ignore
    it.
    """
    text = re.sub(r"(\d+)\s*(?:er|ère|e|ème)\b", r"\1", text.lower())
    return _WORD.findall(text)


def running_lines(pages, threshold=0.5):
    """Lines that repeat on most pages: running headers and footers.

    Detected rather than hard-coded, so this keeps working for the German,
    Spanish and Italian SRDs without anyone remembering to add their footer
    text. Digits are masked before counting, so "Document de Référence du
    Système 5.2.1 118" and "... 119" are recognised as the same line.
    """
    if not pages:
        return set()
    seen = Counter()
    for page in pages:
        for line in set(l.strip() for l in page.split("\n") if l.strip()):
            seen[re.sub(r"\d+", "#", line)] += 1
    floor = max(2, int(len(pages) * threshold))
    return {line for line, count in seen.items() if count >= floor}


def strip_running(page, patterns):
    kept = []
    for line in page.split("\n"):
        if re.sub(r"\d+", "#", line.strip()) in patterns:
            continue
        kept.append(line)
    return "\n".join(kept)


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

    # `pages_pymupdf` already drops running headers/footers geometrically. Do
    # the same to the witness before comparing, or the check measures our own
    # preprocessing instead of the document.
    running = running_lines(witness)
    witness_cmp = [strip_running(p, running) for p in witness]

    report = compare_pages(primary, witness_cmp)
    suspect = [r for r in report if r["agreement"] < min_agreement]
    return {
        "extractor": extractor_id(),
        "cross_checker": cross_checker_id(),
        "pages": primary,
        # Geometry, beside the text and never instead of it. A parser that
        # does not ask for it sees exactly the stream it saw before.
        "layout": layout_pymupdf(pdf_path),
        "page_count": len(primary),
        "comparison": report,
        "suspect_pages": sorted(suspect, key=lambda r: r["agreement"]),
        "min_agreement": min_agreement,
    }
