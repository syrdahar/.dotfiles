"""Transfert de palette : sources Neon Graffiti -> fichiers live, pour une palette cible.

Usage :
  recolor.py render PALETTE.json [--root DIR] [--check]
  recolor.py map PALETTE.json '#29b4d7'

Voir docs/specs/2026-10-09-desk-theme-design.md, section « Transfert de palette ».
"""
import argparse
import functools
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from color import (ROLES, hex_to_lch, hex_to_rgb, hue_diff, lch_to_hex,  # noqa: E402
                   rgb_to_hex, rgb_to_oklab)

THEME_CONF = os.path.expanduser("~/.config/desktop/theme")
P0_PATH = os.path.join(THEME_CONF, "palettes", "neon-graffiti.json")
MANIFEST_PATH = os.path.join(THEME_CONF, "manifest.txt")
SOURCES_DIR = os.path.join(THEME_CONF, "sources")
STATE_REL = os.path.join(".local", "state", "desk", "theme", "rendered.sha")

FIXES = {"#ffffff", "#000000", "#d97757"}  # couleurs inchangées (orange Claude, blancs, noirs)

_cache = {}


# --------------------------------------------------------------------------- palettes

def colors_of(palette):
    """Accepte un JSON complet ({"colors": {...}}) ou directement le dict rôle -> hex."""
    colors = palette.get("colors", palette)
    out = {}
    for role in ROLES:
        if role not in colors:
            raise ValueError("rôle manquant dans la palette : %s" % role)
        out[role] = colors[role].strip().lower()
    return out


def load_colors(path):
    with open(path, encoding="utf-8") as f:
        return colors_of(json.load(f))


@functools.lru_cache(maxsize=None)
def _lch(hex6):
    return hex_to_lch(hex6)


def _norm(hex_str):
    h = hex_str.strip().lower()
    return h if h.startswith("#") else "#" + h


# --------------------------------------------------------------------------- couleur

def map_color(hex6, p0, p1):
    """Transfère une couleur de P0 vers P1 (étapes 1 à 4 de la spec). Retourne « #rrggbb »."""
    c = _norm(hex6)
    key = (c, tuple(p0[r] for r in ROLES), tuple(p1[r] for r in ROLES))
    if key in _cache:
        return _cache[key]
    result = _map_color(c, p0, p1)
    _cache[key] = result
    return result


def _map_color(c, p0, p1):
    if c in FIXES:
        return c
    lab_c = rgb_to_oklab(hex_to_rgb(c))
    best_role, best_d = None, None
    for role in ROLES:
        lab_r = rgb_to_oklab(hex_to_rgb(_norm(p0[role])))
        d = sum((x - y) ** 2 for x, y in zip(lab_c, lab_r))
        if best_d is None or d < best_d:
            best_role, best_d = role, d
    r = best_role
    if _norm(p1[r]) == _norm(p0[r]):
        return c
    Lc, Cc, hc = _lch(c)
    L0, C0, h0 = _lch(_norm(p0[r]))
    L1, C1, h1 = _lch(_norm(p1[r]))
    L = L1 + (Lc - L0)
    C = max(0.0, C1 + (Cc - C0))
    if Cc < 0.02:
        h = h1
    else:
        h = (h1 + hue_diff(h0, hc)) % 360
    return _norm(lch_to_hex((L, C, h)))


def _fmt(orig, value6):
    """Casse du hex d'origine : majuscules si l'origine contient une majuscule, sinon minuscules."""
    return value6.upper() if any(ch.isupper() for ch in orig) else value6.lower()


def _map_hex6(orig, p0, p1):
    """orig = 6 chiffres hex tels qu'écrits dans le fichier ; retourne 6 chiffres mappés."""
    mapped = map_color("#" + orig.lower(), p0, p1)[1:]
    if mapped == orig.lower():
        return orig  # identité exacte : on ne touche pas au texte
    return _fmt(orig, mapped)


# --------------------------------------------------------------------------- regex

# #rrggbb ou #rrggbbaa ; pas dans url(#id) ; pas suivi d'un caractère de mot.
RE_HASH = re.compile(r"(?<!url\()#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?(?![0-9A-Za-z_-])")
# #rgb (3 chiffres, SVG Kvantum) : réécrit en #rrggbb seulement si la couleur change.
RE_HASH3 = re.compile(r"(?<!url\()(?<![0-9A-Za-z_&])#([0-9a-fA-F]{3})(?![0-9A-Za-z_-])")
# rgb(rrggbb) / rgba(rrggbb) / rgba(rrggbbaa) (Hyprland) ; alpha hex conservé.
RE_FUNC_HEX = re.compile(r"\b(rgba?)\(([0-9a-fA-F]{6})([0-9a-fA-F]{2})?\)", re.IGNORECASE)
# rgb(R, G, B) / rgba(R, G, B, a) en décimal ; espaces et alpha conservés.
RE_FUNC_DEC = re.compile(
    r"\b(rgba?\(\s*)(\d{1,3})(\s*,\s*)(\d{1,3})(\s*,\s*)(\d{1,3})((?:\s*,[^()]*)?\))",
    re.IGNORECASE)
# Clé=R,G,B (fichiers .colors KDE)
RE_KDE = re.compile(r"^([ \t]*[A-Za-z0-9_]+=)(\d{1,3}),(\d{1,3}),(\d{1,3})([ \t]*)$", re.M)
# $nameHex = rrggbb (hypr/colors.conf)
RE_BARE = re.compile(
    r"^([ \t]*\$[A-Za-z0-9_]*Hex[A-Za-z0-9_]*[ \t]*=[ \t]*)([0-9a-fA-F]{6})(?![0-9A-Za-z_])",
    re.M)


def _dec_to_hex(r, g, b):
    return rgb_to_hex((int(r), int(g), int(b)))


def recolor_text(text, p0, p1, name=""):
    """Recolore toutes les couleurs reconnues de `text`. `name` (chemin) sert à choisir les formats."""
    p0 = colors_of(p0)
    p1 = colors_of(p1)

    def hash_sub(m):
        return "#" + _map_hex6(m.group(1), p0, p1) + (m.group(2) or "")

    def hash3_sub(m):
        short = m.group(1)
        full = "".join(ch * 2 for ch in short)
        mapped = _map_hex6(full, p0, p1)
        return m.group(0) if mapped == full else "#" + mapped

    def func_hex_sub(m):
        fn, hx, alpha = m.group(1), m.group(2), m.group(3) or ""
        return fn + "(" + _map_hex6(hx, p0, p1) + alpha + ")"

    def func_dec_sub(m):
        try:
            r, g, b = (int(m.group(i)) for i in (2, 4, 6))
        except ValueError:  # pragma: no cover
            return m.group(0)
        if max(r, g, b) > 255:
            return m.group(0)
        mapped = hex_to_rgb(map_color(_dec_to_hex(r, g, b), p0, p1))
        return (m.group(1) + str(mapped[0]) + m.group(3) + str(mapped[1]) + m.group(5)
                + str(mapped[2]) + m.group(7))

    def kde_sub(m):
        r, g, b = (int(m.group(i)) for i in (2, 3, 4))
        if max(r, g, b) > 255:
            return m.group(0)
        mapped = hex_to_rgb(map_color(_dec_to_hex(r, g, b), p0, p1))
        return "%s%d,%d,%d%s" % (m.group(1), mapped[0], mapped[1], mapped[2], m.group(5))

    def bare_sub(m):
        return m.group(1) + _map_hex6(m.group(2), p0, p1)

    text = RE_HASH.sub(hash_sub, text)
    text = RE_HASH3.sub(hash3_sub, text)
    text = RE_FUNC_HEX.sub(func_hex_sub, text)
    text = RE_FUNC_DEC.sub(func_dec_sub, text)
    if name.endswith(".colors"):
        text = RE_KDE.sub(kde_sub, text)
    if name == "" or name.endswith(".conf"):
        text = RE_BARE.sub(bare_sub, text)
    return text


# --------------------------------------------------------------------------- manifest / rendu

def read_manifest(path=MANIFEST_PATH):
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            entries.append(s)
    return entries


def _read_text(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def _sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _sha_file(path):
    with open(path, "rb") as f:
        return _sha_bytes(f.read())


def _load_state(state_path):
    if not os.path.exists(state_path):
        return {}
    with open(state_path, encoding="utf-8") as f:
        return json.load(f)


def _atomic_write(path, text, mode):
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=d, prefix="." + os.path.basename(path) + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def render(palette_path, root=None, check=False, out=None):
    """Rend les fichiers live. Retourne le code de sortie (1 si --check trouve un DIFF)."""
    out = out or sys.stdout
    root = root or os.path.expanduser("~")
    p0 = load_colors(P0_PATH)
    p1 = load_colors(palette_path)
    entries = read_manifest()
    state_path = os.path.join(root, STATE_REL)
    record = _load_state(state_path)
    rc = 0

    for rel in entries:
        src = os.path.join(SOURCES_DIR, rel)
        target = os.path.join(root, rel)
        rendered = recolor_text(_read_text(src), p0, p1, name=rel)
        if check:
            same = os.path.isfile(target) and not os.path.islink(target) \
                and _read_text(target) == rendered
            if same:
                print("same %s" % rel, file=out)
            else:
                print("DIFF %s" % rel, file=out)
                rc = 1
            continue

        if os.path.islink(target):
            print("WARN symlink %s : ignoré" % rel, file=out)
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        exists = os.path.isfile(target)
        current = _read_text(target) if exists else None
        if current == rendered:
            print("unchanged %s" % rel, file=out)
            record[rel] = _sha_bytes(rendered.encode("utf-8"))
            continue
        if exists and rel in record and _sha_file(target) != record[rel]:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            bak = "%s.bak-theme-%s" % (target, stamp)
            shutil.copy2(target, bak)
            print("DRIFT %s (sauvegarde : %s)" % (rel, os.path.basename(bak)), file=out)
        mode = stat.S_IMODE(os.stat(target).st_mode) if exists \
            else stat.S_IMODE(os.stat(src).st_mode)
        _atomic_write(target, rendered, mode)
        record[rel] = _sha_bytes(rendered.encode("utf-8"))
        print("wrote %s" % rel, file=out)

    if not check:
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        _atomic_write(state_path, json.dumps(record, indent=2, sort_keys=True) + "\n", 0o644)
    return rc


# --------------------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(prog="recolor.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("render", help="rend les fichiers live depuis sources/")
    pr.add_argument("palette")
    pr.add_argument("--root", help="écrit sous DIR au lieu de $HOME")
    pr.add_argument("--check", action="store_true", help="n'écrit rien ; same/DIFF par fichier")
    pm = sub.add_parser("map", help="affiche la couleur transférée (debug)")
    pm.add_argument("palette")
    pm.add_argument("color")
    args = ap.parse_args(argv)

    if args.cmd == "render":
        return render(args.palette, root=args.root, check=args.check)
    if args.cmd == "map":
        print(map_color(args.color, load_colors(P0_PATH), load_colors(args.palette)))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
