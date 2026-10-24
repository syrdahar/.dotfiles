#!/usr/bin/env python3
"""Génère les thèmes Kvantum « NeonGraffiti » (look neon) et « NeonGraffitiGlass »
(look glass) à partir de KvArcDark, recoloré avec la palette Neon Graffiti
(~/.config/waybar/colors.css).

  ~/.config/Kvantum/neon-graffiti-build.py      régénère les deux thèmes

Les gris d'Arc sont projetés sur une rampe indigo (même ordre de luminosité,
donc les reliefs du SVG restent cohérents) ; le bleu d'accent devient magenta.
Le look actif est choisi par ~/.config/Kvantum/kvantum.kvconfig
→ looks/{neon,glass}.kvconfig (symlink géré par rice.sh look).
"""
import re
from pathlib import Path

SRC = Path("/usr/share/Kvantum/KvArcDark")
OUT = Path.home() / ".config/Kvantum"

# couleurs d'accent d'Arc → palette
ACCENTS = {
    "#5294e2": "#c23d9e",  # accent principal → magenta
    "#4693e6": "#b0368f",
    "#3176bf": "#9a2f7e",
    "#58acff": "#ff5fb7",  # survol → rose
    "#0582ff": "#29b4d7",  # focus → cyan
    "#b74aff": "#29b4d7",
    "#f04a50": "#e0485a",  # fermer / erreur → rouge
}

# rampes : luminosité d'un gris d'Arc → couleur (interpolation linéaire entre ancres)
RAMPS = {
    "neon": [(0.000, "#000000"), (0.070, "#07050f"), (0.140, "#100c1f"), (0.230, "#1a1530"),
             (0.270, "#201a3a"), (0.330, "#2e2650"), (0.400, "#493459"), (0.580, "#8c7fa3"),
             (0.850, "#e6ddf0"), (1.000, "#ffffff")],
    "glass": [(0.000, "#000000"), (0.070, "#0b0818"), (0.140, "#161129"), (0.230, "#221b3c"),
              (0.270, "#2a2346"), (0.330, "#382e5a"), (0.400, "#54406a"), (0.580, "#978ab0"),
              (0.850, "#ece5f5"), (1.000, "#ffffff")],
}

COLORS = {  # [GeneralColors] de chaque variante
    "neon": {
        "window.color": "#1a1530", "base.color": "#120e24", "alt.base.color": "#171229",
        "button.color": "#221b3c", "light.color": "#493459", "mid.light.color": "#2a2346",
        "dark.color": "#07050f", "mid.color": "#0b0818",
    },
    "glass": {
        "window.color": "#221b3c", "base.color": "#1a1530", "alt.base.color": "#1f1937",
        "button.color": "#2a2346", "light.color": "#54406a", "mid.light.color": "#322a50",
        "dark.color": "#0b0818", "mid.color": "#100c1f",
    },
}
COMMON_COLORS = {
    "highlight.color": "#c23d9e", "inactive.highlight.color": "#7a2d68",
    "text.color": "#e6ddf0", "window.text.color": "#e6ddf0", "button.text.color": "#e6ddf0",
    "disabled.text.color": "#e6ddf066", "tooltip.text.color": "#e6ddf0",
    "highlight.text.color": "#ffffff", "link.color": "#29b4d7", "link.visited.color": "#ff5fb7",
    "progress.indicator.text.color": "#ffffff",
}
GENERAL = {  # [%General]
    "neon": {"translucent_windows": "false", "reduce_window_opacity": "0", "reduce_menu_opacity": "0"},
    "glass": {"translucent_windows": "true", "reduce_window_opacity": "12", "reduce_menu_opacity": "8"},
}
HACKS = {"neon": {"transparent_dolphin_view": "false"}, "glass": {"transparent_dolphin_view": "true"}}


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def hexc(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in c)


def lum(c):
    r, g, b = (v / 255 for v in c)
    return 0.299 * r + 0.587 * g + 0.114 * b


def ramp(l, anchors):
    for (l0, c0), (l1, c1) in zip(anchors, anchors[1:]):
        if l <= l1:
            t = 0 if l1 == l0 else (l - l0) / (l1 - l0)
            a, b = rgb(c0), rgb(c1)
            return hexc([a[i] + (b[i] - a[i]) * t for i in range(3)])
    return anchors[-1][1]


def recolor(hex6, variant):
    h = hex6.lower()
    if h in ACCENTS:
        return ACCENTS[h]
    c = rgb(h)
    if max(c) - min(c) > 40:          # couleur saturée inconnue : laissée telle quelle
        return h
    return ramp(lum(c), RAMPS[variant])


def set_keys(text, section, values):
    """Remplace (ou ajoute) des clés dans une section d'un .kvconfig."""
    m = re.search(rf"^\[{re.escape(section)}\]\n(.*?)(?=^\[|\Z)", text, re.S | re.M)
    body = m.group(1)
    for k, v in values.items():
        if re.search(rf"^{re.escape(k)}=", body, re.M):
            body = re.sub(rf"^{re.escape(k)}=.*$", f"{k}={v}", body, flags=re.M)
        else:
            body = body.rstrip("\n") + f"\n{k}={v}\n"
    return text[:m.start(1)] + body + text[m.end(1):]


def build(variant, name):
    svg = (SRC / "KvArcDark.svg").read_text()
    svg = re.sub(r"#[0-9a-fA-F]{6}\b", lambda m: recolor(m.group(0), variant), svg)
    kv = (SRC / "KvArcDark.kvconfig").read_text()
    kv = re.sub(r"^comment=.*$", f"comment=Neon Graffiti ({variant}) — dérivé de KvArcDark (Tsu Jan)", kv, flags=re.M)
    kv = set_keys(kv, "%General", GENERAL[variant])
    kv = set_keys(kv, "GeneralColors", {**COLORS[variant], **COMMON_COLORS})
    kv = set_keys(kv, "Hacks", HACKS[variant])
    # textes des boutons / menus codés en dur dans les sections : blanc Arc → texte de la palette
    kv = re.sub(r"=#ffffffc8\b", "=#e6ddf0", kv)
    kv = re.sub(r"(text\.[a-z]+\.color)=white\b", r"\1=#ffffff", kv)
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.svg").write_text(svg)
    (d / f"{name}.kvconfig").write_text(kv)
    print(f"{d}  ok")


if __name__ == "__main__":
    build("neon", "NeonGraffiti")
    build("glass", "NeonGraffitiGlass")
