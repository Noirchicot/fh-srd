"""Class-option parser for the English SRD 5.2.1.

CALIBRATED against the pinned EN PDF on 2026-08-24:

    `Eldritch Invocation Options`   p. 72-74   28 entries, 23 with a prerequisite
    `Metamagic Options`             p. 66-67   10 entries, every one with a cost

The reading is shared with the French sibling and lives in `class_options.py`,
which carries the calibration in full — including why an entry's name is read
from the face the source sets it in rather than from the shape of its line,
and why an invocation record carries no `cost` key at all.

📌 THE FIVE NAMES THE ARCHITECT MEASURED AS ABSENT FROM EVERY EXPORT — Agonizing
Blast, Devil's Sight, Eldritch Spear, Repelling Blast, Mask of Many Faces — plus
the six metamagic options — Careful, Distant, Empowered, Quickened, Subtle and
Twinned Spell — are all read by this parser. They were never missing from the
book; they had simply never been extracted.

⛔ `Mystic Arcanum` is NOT one of these. It is a Warlock class FEATURE (p. 72,
"Level 11: Mystic Arcanum") that lets its owner choose a SPELL from the Warlock
spell list, which is a genre this base already holds. It prints no list of its
own and is deliberately not a `class-option`.

⛔ THE ARTIFICER'S INFUSIONS ARE NOT AT THE SRD, and will not be. The class is
absent from SRD 5.2.1 entirely; it arrives through the homebrew door like any
book somebody owns. Nothing here invents them.
"""

import class_options

LANG = "en"
KIND = class_options.KIND
WANTS_LAYOUT = True


def parse(pages, suspect_pages=(), layout=()):
    return class_options.parse(pages, suspect_pages, layout, LANG)
