#!/usr/bin/env python3
"""Palettes desk : auto (image → palette), presets (JSON), swatch PNG.

CLI :
  palette.py auto IMAGE [--no-cache]   → JSON sur stdout
  palette.py preset NAME               → JSON sur stdout
  palette.py list                      → noms des presets (un par ligne, triés)
  palette.py swatch PALETTE.json OUT.png
  palette.py validate PALETTE.json
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import hashlib
import json
import re

import numpy as np
from PIL import Image, ImageDraw

from color import (ROLES, PALETTE_DIR, circ_mean, contrast, hex_to_lch, hue_diff,
                   lch_to_hex, rgb_to_oklab_np)

CACHE_DIR = os.path.expanduser("~/.cache/desk/theme")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
THUMB = 200
N_BINS = 36
BIN_DEG = 10.0


def _palette_dir():
    return os.path.expanduser(PALETTE_DIR)


def _neon():
    """Valeurs L/C/h (OKLCH) des rôles de neon-graffiti : « ADN néon »."""
    with open(os.path.join(_palette_dir(), "neon-graffiti.json"), encoding="utf-8") as f:
        colors = json.load(f)["colors"]
    return {r: hex_to_lch(colors[r]) for r in ROLES}


def _circ_dist(a, b):
    return abs(hue_diff(a, b))


def _analyze(image_path):
    """Analyse d'image : hd, Cm, a1, a2, a3 (teintes des accents, degrés)."""
    im = Image.open(image_path)
    im.thumbnail((THUMB, THUMB))
    im = im.convert("RGB")
    rgb = np.asarray(im, dtype=float).reshape(-1, 3)
    lab = rgb_to_oklab_np(rgb)
    L = lab[:, 0]
    C = np.hypot(lab[:, 1], lab[:, 2])
    h = np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) % 360.0

    hd = circ_mean(h, weights=C)
    cm = float(C.mean())

    # Pics d'accent
    sel = (C >= 0.06) & (L >= 0.25) & (L <= 0.95)
    hs, ws = h[sel], C[sel]
    hist = np.zeros(N_BINS)
    if sel.any():
        bins = np.floor(hs / BIN_DEG).astype(int) % N_BINS
        np.add.at(hist, bins, ws)
    # lissage circulaire [1, 2, 1]
    sm = (np.roll(hist, 1) + 2 * hist + np.roll(hist, -1)) / 4.0

    peaks = []
    work = sm.copy()
    first_w = None
    while len(peaks) < 5 and work.max() > 0:
        i = int(np.argmax(work))
        w = float(sm[i])
        if first_w is None:
            first_w = w
        elif w < 0.08 * first_w:
            break
        center = BIN_DEG * i + BIN_DEG / 2
        if sel.any():
            d = np.abs(((h[sel] - center) + 180.0) % 360.0 - 180.0)
            near = d <= 15.0
            if near.any():
                peak_h = circ_mean(hs[near], weights=ws[near])
            else:
                peak_h = center % 360.0
        else:
            peak_h = center % 360.0
        peaks.append(peak_h)
        for k in range(-4, 5):  # ±40° = ±4 bins
            work[(i + k) % N_BINS] = 0.0

    # Complétion des accents
    if not peaks:
        peaks.append(hd)
    while len(peaks) < 3:
        a1 = peaks[0]
        cands = [(a1 + 45.0) % 360.0, (a1 - 45.0) % 360.0]   # analogues : reste dans l'ambiance
        best = max(cands, key=lambda c: min(_circ_dist(c, p) for p in peaks))
        peaks.append(best)
    return {"hd": hd, "Cm": cm, "a1": peaks[0], "a2": peaks[1], "a3": peaks[2], "peaks": peaks}


ACCENTS = ("cyan", "magenta", "gold")
CHROMATIC = ("cyan", "blue", "magenta", "pink", "gold", "orange", "red", "green")


def _assign_accents(peaks, neon):
    """Pics (≤ 5, du plus fort au plus faible) → rôles cyan/magenta/gold : on choisit 3 pics et leur
    ordre en minimisant l'écart de teinte aux rôles néon + 10° de pénalité par rang de pic."""
    from itertools import permutations
    best = min(permutations(range(len(peaks)), 3),
               key=lambda p: sum(_circ_dist(neon[r][2], peaks[i]) + 10.0 * i
                                 for r, i in zip(ACCENTS, p)))
    return {r: peaks[i] for r, i in zip(ACCENTS, best)}


def _dna(h, neon):
    """L et C du rôle néon chromatique dont la teinte est la plus proche de h (évite jaune sombre = kaki)."""
    r = min(CHROMATIC, key=lambda r: _circ_dist(neon[r][2], h))
    return neon[r][0], neon[r][1]


def _build(name, source, an):
    """Construit les 14 couleurs à partir de l'analyse."""
    neon = _neon()
    hd, cm = an["hd"], an["Cm"]
    acc = _assign_accents(an.get("peaks") or (an["a1"], an["a2"], an["a3"]), neon)
    accents_h = tuple(acc.values())

    def adjust(base_h):
        """Teinte sémantique, tirée de 20 % vers l'accent le plus proche s'il est à < 60°."""
        near = min(accents_h, key=lambda a: _circ_dist(base_h, a))
        d = hue_diff(base_h, near)
        if abs(d) < 60.0:
            return (base_h + 0.20 * d) % 360.0
        return base_h % 360.0

    hues = dict(acc)
    for r in ("blue", "pink", "orange", "red", "green"):
        hues[r] = adjust(neon[r][2])
    neutral_c_factor = 0.5 if cm < 0.03 else 1.0
    acc_factor = min(max(cm / 0.08, 0.85), 1.15)

    lch = {}
    for r in ("base", "mantle", "surface", "overlay", "text", "subtext"):
        L, C, _ = neon[r]
        lch[r] = (L, C * neutral_c_factor, hd)
    for r, h in hues.items():
        L, C = _dna(h, neon) if r in ACCENTS else neon[r][:2]
        lch[r] = (L, max(C * acc_factor, 0.12), h)

    hexes = {r: lch_to_hex(lch[r]) for r in ROLES if r in lch}

    # Contraste texte / fond
    L, C, h = lch["text"]
    base = hexes["base"]
    while contrast(lch_to_hex((L, C, h)), base) < 7.0 and L < 0.98:
        L = min(L + 0.02, 0.98)
    lch["text"] = (L, C, h)
    hexes["text"] = lch_to_hex(lch["text"])

    # Contraste accents / fond
    for r in ("cyan", "blue", "magenta", "pink", "gold", "orange", "red", "green"):
        L, C, h = lch[r]
        while contrast(lch_to_hex((L, C, h)), base) < 4.5 and L < 0.95:
            L = min(L + 0.02, 0.95)
        lch[r] = (L, C, h)
        hexes[r] = lch_to_hex(lch[r])

    return {"name": name, "source": source,
            "colors": {r: hexes[r] for r in ROLES}}


def auto_palette(image_path):
    """Palette auto (dict JSON) depuis une image. Déterministe."""
    image_path = os.path.abspath(image_path)
    stem = os.path.splitext(os.path.basename(image_path))[0]
    an = _analyze(image_path)
    return _build(stem, "auto:" + image_path, an)


def _sha1_file(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def get_auto(image_path):
    """Palette auto avec cache ~/.cache/desk/theme/<sha1 du fichier>.json."""
    image_path = os.path.abspath(image_path)
    key = _sha1_file(image_path)
    cache_file = os.path.join(CACHE_DIR, key + ".json")
    stem = os.path.splitext(os.path.basename(image_path))[0]
    if os.path.exists(cache_file):
        try:
            with open(cache_file, encoding="utf-8") as f:
                pal = json.load(f)
            validate(pal)
            pal["name"] = stem
            pal["source"] = "auto:" + image_path
            return pal
        except (ValueError, OSError):
            pass
    pal = auto_palette(image_path)
    os.makedirs(CACHE_DIR, exist_ok=True)
    tmp = cache_file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(pal, f, indent=1)
    os.replace(tmp, cache_file)
    return pal


def validate(pal):
    """Lève ValueError si la palette n'est pas valide (14 rôles, #rrggbb)."""
    if not isinstance(pal, dict) or not isinstance(pal.get("colors"), dict):
        raise ValueError("palette: objet 'colors' manquant")
    colors = pal["colors"]
    missing = [r for r in ROLES if r not in colors]
    if missing:
        raise ValueError("rôles manquants : " + ", ".join(missing))
    extra = [r for r in colors if r not in ROLES]
    if extra:
        raise ValueError("rôles inconnus : " + ", ".join(extra))
    for r in ROLES:
        v = colors[r]
        if not isinstance(v, str) or not HEX_RE.match(v):
            raise ValueError("couleur invalide pour %s : %r" % (r, v))
    return pal


def load_preset(name):
    path = os.path.join(_palette_dir(), name + ".json")
    with open(path, encoding="utf-8") as f:
        pal = json.load(f)
    return validate(pal)


def list_presets():
    d = _palette_dir()
    return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json"))


def swatch(palette, out_png):
    """Bande de 14 pastilles (48 px) sur fond = base, supersamplée ×4."""
    validate(palette)
    colors = palette["colors"]
    d, gap, pad, scale, radius = 48, 8, 16, 4, 16
    w = 2 * pad + len(ROLES) * d + (len(ROLES) - 1) * gap
    h = 2 * pad + d
    S = scale
    big = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(big)
    dr.rounded_rectangle([0, 0, w * S - 1, h * S - 1], radius=radius * S,
                         fill=colors["base"])
    for i, r in enumerate(ROLES):
        x = (pad + i * (d + gap)) * S
        y = pad * S
        dr.ellipse([x, y, x + d * S - 1, y + d * S - 1], fill=colors[r])
    img = big.resize((w, h), Image.LANCZOS)
    img.save(out_png)
    return out_png


def _load_json_file(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="palette.py")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("auto", help="palette depuis une image")
    p.add_argument("image")
    p.add_argument("--no-cache", action="store_true")

    p = sub.add_parser("preset", help="palette preset en JSON")
    p.add_argument("name")

    sub.add_parser("list", help="liste des presets")

    p = sub.add_parser("swatch", help="PNG de la bande de couleurs")
    p.add_argument("palette")
    p.add_argument("out")

    p = sub.add_parser("validate", help="valide un fichier palette")
    p.add_argument("palette")

    args = ap.parse_args(argv)
    try:
        if args.cmd == "auto":
            pal = auto_palette(args.image) if args.no_cache else get_auto(args.image)
            print(json.dumps(pal, indent=1))
        elif args.cmd == "preset":
            print(json.dumps(load_preset(args.name), indent=1))
        elif args.cmd == "list":
            for n in list_presets():
                print(n)
        elif args.cmd == "swatch":
            swatch(_load_json_file(args.palette), args.out)
        elif args.cmd == "validate":
            validate(_load_json_file(args.palette))
            print("ok")
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print("erreur : %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
