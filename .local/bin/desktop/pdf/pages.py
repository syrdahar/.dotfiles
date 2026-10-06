"""Plages de pages : « 1-3,5,8- » (à partir de 1 ; « 8- » = jusqu'à la fin ; « -3 » = 1 à 3)."""
import re

from .errors import OpError
from .i18n import t

_ITEM = re.compile(r"^(\d*)\s*(-)?\s*(\d*)$")


class RangeError(OpError, ValueError):
    pass


def parse_groups(spec, n):
    """→ une liste d'indices (à partir de 0) par élément séparé par une virgule."""
    spec = (spec or "").strip()
    if spec in ("", "all", "*"):
        return [list(range(n))]
    groups = []
    for item in spec.split(","):
        item = item.strip()
        m = _ITEM.match(item)
        if not item or not m or (not m[1] and not m[3]) or (not m[2] and m[3]):
            raise RangeError(t(f"Plage invalide : « {item} » (exemple : 1-3,5,8-)",
                               f"Invalid range: \"{item}\" (example: 1-3,5,8-)"))
        a = int(m[1]) if m[1] else 1
        b = a if not m[2] else (int(m[3]) if m[3] else n)
        if not (1 <= a <= n and 1 <= b <= n):
            raise RangeError(t(f"Page hors du document : « {item} » ({n} pages)",
                               f"Page out of range: \"{item}\" ({n} pages)"))
        if b < a:
            raise RangeError(t(f"Plage à l'envers : « {item} »", f"Reversed range: \"{item}\""))
        groups.append(list(range(a - 1, b)))
    return groups


def parse_ranges(spec, n):
    """→ indices aplatis, sans doublon, dans l'ordre donné."""
    seen, out = set(), []
    for g in parse_groups(spec, n):
        for i in g:
            if i not in seen:
                seen.add(i)
                out.append(i)
    return out
