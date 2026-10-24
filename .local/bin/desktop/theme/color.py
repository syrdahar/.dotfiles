"""Colorimétrie partagée par palette.py et recolor.py : sRGB ↔ OKLab ↔ OKLCH, contraste WCAG.

Toutes les fonctions scalaires prennent/rendent des tuples ; les hex sont « #rrggbb » minuscules.
Les versions *_np travaillent sur des tableaux numpy (N, 3) pour l'analyse d'image.
"""
import math

import numpy as np

PALETTE_DIR = "~/.config/desktop/theme/palettes"
ROLES = ("base", "mantle", "surface", "overlay", "text", "subtext",
         "cyan", "blue", "magenta", "pink", "gold", "orange", "red", "green")


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in rgb)


def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c):
    c = c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return c * 255


def rgb_to_oklab(rgb):
    r, g, b = (_lin(float(v)) for v in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = (math.copysign(abs(x) ** (1 / 3), x) for x in (l, m, s))
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def oklab_to_rgb_unclipped(lab):
    L, a, b = lab
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    lin = (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
           -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
           -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)
    return tuple(_gam(min(max(c, 0.0), 1.0)) if -1e-4 <= c <= 1 + 1e-4 else math.nan for c in lin)


def oklab_to_lch(lab):
    L, a, b = lab
    return (L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360)


def lch_to_oklab(lch):
    L, C, h = lch
    return (L, C * math.cos(math.radians(h)), C * math.sin(math.radians(h)))


def hex_to_lch(h):
    return oklab_to_lch(rgb_to_oklab(hex_to_rgb(h)))


def lch_to_hex(lch):
    """OKLCH → hex, en réduisant le chroma jusqu'à entrer dans le gamut sRGB."""
    L, C, h = lch
    L = min(max(L, 0.0), 1.0)
    C = max(C, 0.0)
    for _ in range(60):
        rgb = oklab_to_rgb_unclipped(lch_to_oklab((L, C, h)))
        if not any(math.isnan(v) for v in rgb):
            return rgb_to_hex(rgb)
        C *= 0.95
    return rgb_to_hex(oklab_to_rgb_unclipped((L, 0.0, 0.0)))


def oklab_dist(h1, h2):
    a, b = rgb_to_oklab(hex_to_rgb(h1)), rgb_to_oklab(hex_to_rgb(h2))
    return math.dist(a, b)


def hue_diff(h1, h2):
    """Écart signé h2 − h1 ramené dans ]-180, 180]."""
    d = (h2 - h1) % 360
    return d - 360 if d > 180 else d


def circ_mean(hues, weights=None):
    w = np.ones(len(hues)) if weights is None else np.asarray(weights, float)
    r = np.radians(np.asarray(hues, float))
    s, c = (w * np.sin(r)).sum(), (w * np.cos(r)).sum()
    return math.degrees(math.atan2(s, c)) % 360


def luminance(h):
    r, g, b = (_lin(float(v)) for v in hex_to_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(h1, h2):
    a, b = sorted((luminance(h1), luminance(h2)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def rgb_to_oklab_np(rgb):
    """(N, 3) uint8/float 0-255 → (N, 3) OKLab."""
    c = np.asarray(rgb, float) / 255
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                   [0.2119034982, 0.6806995451, 0.1073969566],
                   [0.0883024619, 0.2817188376, 0.6299787005]])
    M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                   [1.9779984951, -2.4285922050, 0.4505937099],
                   [0.0259040371, 0.7827717662, -0.8086757660]])
    return np.cbrt(c @ M1.T) @ M2.T
