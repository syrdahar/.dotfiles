"""Langue d'affichage (même état que desk lang : ~/.local/state/desk/lang, fr | en)."""
import os
from pathlib import Path

STATE = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "desk"


def _lang():
    try:
        v = (STATE / "lang").read_text().strip()
    except OSError:
        v = os.environ.get("DESK_LANG", "en")
    return "fr" if v == "fr" else "en"


LANG = _lang()


def t(fr, en):
    return fr if LANG == "fr" else en


def bi(label):
    """« français ‖ english » → libellé dans la langue courante."""
    if " ‖ " not in label:
        return label
    fr, en = label.split(" ‖ ", 1)
    return t(fr, en)
