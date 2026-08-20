"""Weapon-mastery parser for the English SRD 5.2.1.

CALIBRATED against the pinned EN PDF on 2026-08-20, the `Mastery Properties`
section of the Equipment chapter (p. 90). 8 masteries, 0 anomalies.

The reading is shared and lives in `weapon_sections.py`.

WHAT THIS CLOSES: all 38 weapon records already carry the NAME of their
mastery (`data.mastery: "Topple"`) and none of them carried its definition,
in any genre, in either language. The join a consumer needs is by name, so
these eight records take the identifier space `srd:weapon-mastery:en:<slug>`
and the closed count is guarded — the section's eight heads are additionally
required to be the same eight words the Weapons table's own column uses.

A mastery is NOT a weapon property in the SRD's own terms, which is why they
are two genres and not one: a property applies to anyone holding the weapon,
a mastery is LOCKED — "usable only by a character who has a feature, such as
Weapon Mastery, that unlocks the property", says the section's first line.
"""

import weapon_sections

LANG = "en"
KIND = weapon_sections.MASTERY_KIND


def parse(pages, suspect_pages=()):
    return weapon_sections.parse(pages, suspect_pages, LANG, KIND)
