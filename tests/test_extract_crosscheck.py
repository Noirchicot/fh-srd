"""The extractor cross-check must still be able to fail.

After the running-header and ordinal fixes, the two extractors agree on all 380
pages of the French SRD. That is the right answer -- but a check that never
fires and a check that is broken look identical from the outside, so this
proves it can still catch a real divergence.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import extract  # noqa: E402


def main():
    a = ["le sort inflige 8d6 dégâts de feu", "portée 45 m"]

    # identical input -> perfect agreement
    same = extract.compare_pages(a, list(a))
    assert all(p["agreement"] == 1.0 for p in same), same
    print("  ok  identical pages agree at 1.0")

    # a dropped word is caught
    b = ["le sort inflige dégâts de feu", "portée 45 m"]
    rep = extract.compare_pages(a, b)
    assert rep[0]["agreement"] < 1.0, rep[0]
    assert "8d6" in rep[0]["only_pymupdf"], rep[0]
    print("  ok  a dropped word is detected (agreement %.3f)" % rep[0]["agreement"])

    # a changed number is caught -- the case that matters most for rules text
    c = ["le sort inflige 8d4 dégâts de feu", "portée 45 m"]
    rep = extract.compare_pages(a, c)
    assert rep[0]["agreement"] < 1.0, rep[0]
    print("  ok  a changed damage die is detected (agreement %.3f)" % rep[0]["agreement"])

    # a whole missing page is caught
    rep = extract.compare_pages(a, ["le sort inflige 8d6 dégâts de feu"])
    assert rep[1]["agreement"] == 0.0, rep[1]
    print("  ok  a missing page is detected")

    # ordinal tokenisation is normalised, NOT reported as a divergence
    rep = extract.compare_pages(["sort du 3e niveau"], ["sort du 3 e niveau"])
    assert rep[0]["agreement"] == 1.0, (
        "ordinal tokenisation still counts as a divergence: %s" % rep[0]
    )
    print("  ok  ordinal tokenisation does not count as a divergence")

    # running headers are detected without hard-coding their text
    pages = ["Document de Référence 5.2.1 12\nrègle A",
             "Document de Référence 5.2.1 13\nrègle B",
             "Document de Référence 5.2.1 14\nrègle C"]
    running = extract.running_lines(pages)
    assert running, "no running line detected"
    stripped = [extract.strip_running(p, running) for p in pages]
    assert all("Référence" not in p for p in stripped), stripped
    assert all("règle" in p for p in stripped), "stripping ate real content"
    print("  ok  running headers detected by repetition, content preserved")

    print("PASS test_extract_crosscheck")


if __name__ == "__main__":
    main()
