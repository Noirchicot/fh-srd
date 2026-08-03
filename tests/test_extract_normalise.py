"""normalise() must keep paragraph breaks without inventing any.

PyMuPDF merges a whole multi-paragraph passage into ONE text block and marks
the second and later paragraphs with a tab right after the newline -- the
printed first-line indent. Found while calibrating the English spell parser:
without this, "Fireball"'s "Using a Higher-Level Spell Slot." paragraph was
indistinguishable from a same-paragraph line wrap, and got silently glued to
the previous sentence. A table row's tab sits mid-line ("Str\\t18 +4"), never
right after a newline, so it must NOT be treated as a paragraph break -- the
negative control below proves that.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402


def main():
    # A block-internal paragraph start (tab right after the newline) becomes
    # a real blank line.
    raw = "cessful one.\n\t Flammable objects start burning.\n\t Using a Higher-Level Spell Slot. More text."
    out = extract.normalise(raw)
    assert "\n\n" in out, repr(out)
    paras = out.split("\n\n")
    assert len(paras) == 3, paras
    assert paras[0] == "cessful one."
    assert paras[1] == "Flammable objects start burning."
    assert paras[2] == "Using a Higher-Level Spell Slot. More text."
    print("  ok  tab-marked paragraph starts become blank lines")

    # A plain mid-sentence line wrap (no tab) stays a single newline, not a
    # paragraph break -- promoting every newline would be a different bug,
    # just as silent as the one this fixes.
    wrapped = "A bright streak flashes from you to a point you\nchoose within range."
    out = extract.normalise(wrapped)
    assert "\n\n" not in out, repr(out)
    assert out == "A bright streak flashes from you to a point you choose within range." \
        or out == "A bright streak flashes from you to a point you\nchoose within range.", out
    print("  ok  an ordinary line wrap is not promoted to a paragraph break")

    # NEGATIVE CONTROL: a table's mid-line tab (never right after a newline)
    # must not be mistaken for a paragraph start.
    table = "Str\t 18 +4\n+4\n Dex\t12 +1\n+1"
    out = extract.normalise(table)
    assert "\n\n" not in out, (
        "a mid-line table tab was mistaken for a paragraph break: %r" % out
    )
    print("  ok  negative control: a mid-line table tab is not a paragraph break")

    # A SOFT hyphen (U+00AD) mid-word must be stripped outright, not treated
    # as a real hyphen or left to render. Found calibrating the class parser
    # on "Meta\xadmagic" and "Short\xadsword" -- WotC's own layout engine
    # inserts it, not a line break, so the existing plain-"-" dehyphenator
    # never sees it.
    soft = "Meta­magic Options and a Short­sword"
    out = extract.normalise(soft)
    assert "­" not in out, repr(out)
    assert out == "Metamagic Options and a Shortsword", out
    print("  ok  a soft hyphen mid-word is stripped, not rendered")

    # NEGATIVE CONTROL: an ordinary printable hyphen must survive -- this is
    # a different character (U+002D) and carries real information (e.g.
    # "Well-earned", "self-aware").
    real = "a well-earned rest"
    out = extract.normalise(real)
    assert out == "a well-earned rest", (
        "an ordinary hyphen must not be touched by the soft-hyphen strip: %r" % out
    )
    print("  ok  negative control: an ordinary hyphen is untouched")

    print("PASS test_extract_normalise")


if __name__ == "__main__":
    main()
