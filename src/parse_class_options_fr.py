"""Class-option parser for the French SRD 5.2.1.

CALIBRATED against the pinned FR PDF on 2026-08-24:

    `Options de Manifestation occulte`   p. 70-73   28 entrées, 23 avec prérequis
    `Options de Métamagie`               p. 52-53   10 entrées, toutes avec un coût

🔴 LE FRANÇAIS NE DIT PAS « INVOCATION ». Il dit **Manifestation occulte** — et
**Arcanum mystique** pour l'autre aptitude de l'Occultiste. Chercher
« invocation » dans le corpus français ne ramène RIEN et fait conclure, à tort,
que la donnée n'y est pas. Mesurer la chose, jamais son nom.

🔴 ET LES PAGES ANGLAISES NE VALENT RIEN ICI. Le français range ses classes
selon leurs noms français : *Ensorceleur* est la cinquième là où *Sorcerer* est
la dixième, si bien que la Métamagie est p. 66 en anglais et **p. 52** en
français. Seize pages d'écart dans le même livre. Tous les repères de
`class_options.py` sont des LIGNES, jamais des pages.

📌 Les vingt-huit noms français ne se déduisent d'aucun nom anglais : *Mille
visages* (Mask of Many Faces), *Buveuse de vie* (Lifedrinker), *Décharge
déchirante* (Agonizing Blast), *Pas aérien* (Ascendant Step). Et chaque liste
est alphabétique **dans sa propre langue** : *Décharge déchirante* est 3e en
français quand *Agonizing Blast* est 1er en anglais. ⛔ Rien ici n'apparie les
deux langues — un appariement par position serait faux dans les deux sens à la
fois et ne se contredirait jamais. C'est le travail de `correspond.py` et d'une
personne qui le signe.

📌 Le libellé du coût est « Coût : » et celui du prérequis « Prérequis : », tous
deux avec l'espace fine insécable du typographe français — déjà ramenée à une
espace ordinaire par `extract.normalise` avant d'arriver ici.
"""

import class_options

LANG = "fr"
KIND = class_options.KIND
WANTS_LAYOUT = True


def parse(pages, suspect_pages=(), layout=()):
    return class_options.parse(pages, suspect_pages, layout, LANG)
