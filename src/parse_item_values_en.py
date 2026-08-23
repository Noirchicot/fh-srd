"""The English magic item value table (p.206). See `parse_item_values`."""

import parse_item_values


def parse(pages, suspect_pages=()):
    return parse_item_values.parse(pages, suspect_pages, "en")
