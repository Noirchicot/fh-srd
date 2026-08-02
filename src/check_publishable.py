"""The publish gate — one command that answers "may this ship?"

Run it before any export leaves this repository:

    python3 src/check_publishable.py

It refuses on any of these, and says which:

  1. a record outside the `srd` layer  — this repository imports SRD and
     nothing else; content from books Eric owns goes to a separate FHPC mirror
     by his decision, precisely so there is nothing to filter and nothing that
     can leak by being forgotten;
  2. a source whose attribution has not been transcribed from the PDF;
  3. a record missing its licence, attribution or provenance;
  4. a reconciliation failure — a candidate the parser examined that ended up
     neither as a record nor as a stated exclusion, i.e. something dropped in
     silence. (This replaced an earlier "the exclusion register must not be
     empty" rule, which the first real import showed to be wrong: 339 spells,
     nothing rejected, a legitimately empty register.);
  5. a tripwire hit — a trademark, a piece of product identity or a known
     non-SRD name found in the text, however it got there.

Exit code 0 means every check passed. It does not mean a lawyer said yes.
"""

import sys

import db
import sources
import tripwire

# This repository imports the SRD. The other three layers exist in the schema
# because the architecture calls for them and because the FHPC will carry them
# — but nothing here may populate them.
IMPORTER_LAYERS = {"srd"}


def check(conn, verbose=True):
    failures = []

    def say(line):
        if verbose:
            print(line)

    # 1 — layer confinement
    layers = {
        row["layer"]: row["n"]
        for row in conn.execute(
            "SELECT layer, count(*) AS n FROM record GROUP BY layer"
        )
    }
    stray = {k: v for k, v in layers.items() if k not in IMPORTER_LAYERS}
    if stray:
        failures.append("records outside the srd layer: %s" % stray)
        say("  FAIL  layer confinement — %s" % stray)
    else:
        say("  ok    layer confinement (%d srd records, nothing else)"
            % layers.get("srd", 0))

    # 2 — attribution transcribed, not guessed
    unverified = [
        s["id"]
        for s in sources.load_lock()["sources"]
        if not s.get("attribution_verified")
    ]
    if unverified:
        failures.append("sources with unverified attribution: %s" % unverified)
        say("  FAIL  attribution unverified — %s" % unverified)
    else:
        say("  ok    every source attribution transcribed from its PDF")

    # 3 — provenance on every record
    gaps = conn.execute("SELECT count(*) FROM provenance_gaps").fetchone()[0]
    if gaps:
        failures.append("%d record(s) without licence or attribution" % gaps)
        say("  FAIL  provenance — %d gap(s)" % gaps)
    else:
        say("  ok    provenance complete on every record")

    # 4 — reconciliation: nothing was dropped in silence
    #
    # REPLACED the earlier "the exclusion register must not be empty" rule.
    # That rule was a crude proxy, and the real French import proved it wrong:
    # 339 spells parsed, nothing rejected, register legitimately empty -- and
    # the gate refused a perfectly good base. Demanding a non-empty register
    # would have pushed someone to invent an entry to satisfy it.
    #
    # What actually needs guaranteeing is that every candidate the parser
    # looked at ended up either as a record or as a stated exclusion. A missing
    # rule is invisible; a rejected one is at least written down.
    run = conn.execute("SELECT * FROM import_run LIMIT 1").fetchone()
    if run is None:
        failures.append("no import_run row: the base cannot say how it was built")
        say("  FAIL  no import ledger")
    else:
        examined = run["candidates_examined"]
        accounted = run["record_count"] + run["rejected_count"]
        if examined != accounted:
            failures.append(
                "reconciliation: %d candidate(s) examined but %d accounted for "
                "-- %d disappeared without being recorded as an exclusion"
                % (examined, accounted, examined - accounted)
            )
            say("  FAIL  reconciliation %d != %d" % (examined, accounted))
        else:
            say("  ok    reconciliation: %d examined = %d kept + %d rejected"
                % (examined, run["record_count"], run["rejected_count"]))
    excl = conn.execute("SELECT count(*) FROM exclusion").fetchone()[0]
    say("        exclusion register: %d entries" % excl)

    # 5 — the tripwire
    hits = tripwire.scan_base(conn)
    if hits:
        families = tripwire.summarise(hits)
        failures.append(
            "tripwire: %d hit(s) across %s" % (len(hits), sorted(families))
        )
        say("  FAIL  tripwire — %d hit(s)" % len(hits))
        for family in sorted(families):
            for hit in families[family][:5]:
                say("          [%s] %r in %s" % (family, hit["term"], hit["where"]))
                say("               ...%s..." % hit["context"][:100])
    else:
        say("  ok    tripwire clean (%d patterns)" % len(tripwire.COMPILED))

    return failures


def main():
    conn = db.connect()
    print("publish gate")
    failures = check(conn)
    if failures:
        print("\nREFUSED — %d check(s) failed:" % len(failures))
        for f in failures:
            print("  - %s" % f)
        print("\nThis is not legal advice. It is the mechanical part only.")
        return 1
    print("\nAll checks passed. This is the mechanical part only — it is not")
    print("legal advice and it is not a decision to publish.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
