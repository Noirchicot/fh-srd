"""La table de valeur des objets magiques, côté français (p.217).

⚠️ Elle n'est PAS à la même page que l'anglaise, et ses nombres portent une
espace insécable pour les milliers — repliée par `extract.normalise` avant que
ce lecteur ne la voie. Voir `parse_item_values`.
"""

import parse_item_values


def parse(pages, suspect_pages=()):
    return parse_item_values.parse(pages, suspect_pages, "fr")
