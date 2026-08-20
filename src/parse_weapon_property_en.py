"""Weapon-property parser for the English SRD 5.2.1.

CALIBRATED against the pinned EN PDF on 2026-08-20, the `Properties` section
of the Equipment chapter (p. 89-90). 11 properties, 0 anomalies.

The reading is shared with the three sibling modules and lives in
`weapon_sections.py`, which carries the calibration in full — including the
reason the eleventh property, `Improvised Weapons`, comes back from INSIDE
the mastery block and why the region is therefore read whole rather than cut
at the `Mastery Properties` heading.

WHY THIS IS ITS OWN GENRE AND NOT GLOSSARY MATERIAL (architect's arbitration,
2026-08-20): the Rules Glossary carries exactly one `reach` entry, the combat
one, and NOT the weapon property `Reach`. Pouring these eleven into the
glossary would CREATE the duplicate that does not exist yet. Two texts, one
word, two genres.
"""

import weapon_sections

LANG = "en"
KIND = weapon_sections.PROPERTY_KIND


def parse(pages, suspect_pages=()):
    return weapon_sections.parse(pages, suspect_pages, LANG, KIND)
