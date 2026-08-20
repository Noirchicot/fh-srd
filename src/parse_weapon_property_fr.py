"""Weapon-property parser for the French SRD 5.2.1.

CALIBRATED against the pinned FR PDF on 2026-08-20, the `Propriétés` section
of the Équipement chapter (p. 95-96). 11 properties, 0 anomalies.

⚠️ THE PAGE SPAN IS 95-96, not 95: the mandate's own note put the French
properties on p. 95 alone, from a bare `fitz` read. Through `extract.py`,
`Lourde`, `Munitions`, `Polyvalente` and `Portée` land on p. 96 — which is
precisely why `Lourde`, being the FIRST line of a page, needs the page-start
head rule in `weapon_sections.py` and not the blank-line rule.

The eleven names are French's own alphabet, read off the page and not
translated: Allonge · Armes improvisées · Chargement · Deux mains · Finesse ·
Lancer · Légère · Lourde · Munitions · Polyvalente · Portée. `Allonge` is
first here where its English counterpart `Reach` is eighth, so nothing pairs
by rank — `layers/TRADUCTION.md`.
"""

import weapon_sections

LANG = "fr"
KIND = weapon_sections.PROPERTY_KIND


def parse(pages, suspect_pages=()):
    return weapon_sections.parse(pages, suspect_pages, LANG, KIND)
