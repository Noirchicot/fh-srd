"""Weapon-mastery parser for the French SRD 5.2.1.

CALIBRATED against the pinned FR PDF on 2026-08-20, the `Propriétés botte`
section of the Équipement chapter (p. 96). 8 bottes, 0 anomalies.

🔴 FRENCH DOES NOT SAY "MAÎTRISE" FOR THIS. It says **botte**, in the fencing
sense. The section is `Propriétés botte`, the weapons table's sixth column is
`Botte d'arme`, the level-1 class feature is `Bottes d'arme`. Meanwhile
`Maîtrise des armes` DOES exist in French and sits on the previous page
(p. 95) — it is the *proficiency* rule, "add your proficiency bonus to the
attack roll". Two notions, two neighbouring sections, one French word: an
anchor on "maîtrise" brings back the wrong section and says nothing.

📌 The eight names are unguessable from English and are read off the page:
Coup double (= Nick) · Écorchure (= Graze) · Enchaînement (= Cleave) ·
Ouverture (= Vex) · Poussée (= Push) · Ralentissement (= Slow) ·
Renversement (= Topple) · Sape (= Sap). No root and no rank pairs them; the
mapping above is written here for a human reader only — nothing in this
repository joins the two languages, per `layers/TRADUCTION.md`.
"""

import weapon_sections

LANG = "fr"
KIND = weapon_sections.MASTERY_KIND


def parse(pages, suspect_pages=()):
    return weapon_sections.parse(pages, suspect_pages, LANG, KIND)
