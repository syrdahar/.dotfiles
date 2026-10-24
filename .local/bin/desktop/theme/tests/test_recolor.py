import contextlib
import glob
import io
import json
import os
import subprocess
import sys

import pytest

import recolor

THEME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECOLOR = os.path.join(THEME_DIR, "recolor.py")
NEON_PATH = recolor.P0_PATH


@pytest.fixture(scope="module")
def p0():
    return recolor.load_colors(NEON_PATH)


@pytest.fixture(scope="module")
def p1():
    """Palette de test : tous les rôles changés."""
    return {
        "base": "#101010", "mantle": "#202020", "surface": "#303030", "overlay": "#404040",
        "text": "#f0f0f0", "subtext": "#a0a0a0", "cyan": "#ff0000", "blue": "#00ff00",
        "magenta": "#0000ff", "pink": "#ff00ff", "gold": "#ffff00", "orange": "#00ffff",
        "red": "#800000", "green": "#008000",
    }


def _manifest():
    return recolor.read_manifest()


def test_manifest_has_entries_and_no_symlinks():
    entries = _manifest()
    assert len(entries) >= 30
    for rel in entries:
        assert not os.path.islink(os.path.join(recolor.SOURCES_DIR, rel)), rel
        assert os.path.isfile(os.path.join(recolor.SOURCES_DIR, rel)), rel


def test_golden_identity_with_neon(p0):
    for rel in _manifest():
        src = os.path.join(recolor.SOURCES_DIR, rel)
        with open(src, encoding="utf-8", newline="") as f:
            text = f.read()
        assert recolor.recolor_text(text, p0, p0, name=rel) == text, rel


def test_live_matches_active_palette():
    """Les fichiers live = rendu de la palette active (desk theme), neon-graffiti à défaut."""
    active = os.path.expanduser("~/.local/state/desk/theme/palette.json")
    pal = active if os.path.exists(active) else NEON_PATH
    out = subprocess.run([sys.executable, "-I", RECOLOR, "render", pal, "--check"],
                         capture_output=True, text=True)
    lines = [l for l in out.stdout.splitlines() if l.strip()]
    assert out.returncode == 0, out.stdout + out.stderr
    assert len(lines) == len(_manifest())
    assert all(l.startswith("same ") for l in lines), [l for l in lines if not l.startswith("same ")]


@pytest.mark.parametrize("src,expected", [
    ("#29b4d7", "#ff0000"),
    ("#29B4D7", "#FF0000"),
    ("#29b4d7cc", "#ff0000cc"),
    ("rgba(29b4d7ee)", "rgba(ff0000ee)"),
    ("rgb(29b4d7)", "rgb(ff0000)"),
    ("rgba(41, 180, 215, 0.45)", "rgba(255, 0, 0, 0.45)"),
    ("rgb(41,180,215)", "rgb(255,0,0)"),
    ("$cyanHex    = 29b4d7", "$cyanHex    = ff0000"),
    ("#ffffff", "#ffffff"),
    ("#d97757", "#d97757"),
    ("$cyan", "$cyan"),
    ("@magenta", "@magenta"),
    ("$goldHexee", "$goldHexee"),
    ("alpha(@magenta, 0.45)", "alpha(@magenta, 0.45)"),
    ("url(#abc123)", "url(#abc123)"),
    ("#abc123def", "#abc123def"),
    ("id=\"a1b2c3\"", "id=\"a1b2c3\""),
])
def test_formats(p0, p1, src, expected):
    assert recolor.recolor_text(src, p0, p1, name="x.conf") == expected


def test_kde_line_only_in_colors_files(p0, p1):
    line = "ForegroundLink=41,180,215\n"
    assert recolor.recolor_text(line, p0, p1, name="NeonGraffiti.colors") == "ForegroundLink=255,0,0\n"
    assert recolor.recolor_text(line, p0, p1, name="other.conf") == line


def test_map_color_identity_and_fixes(p0, p1):
    assert recolor.map_color("#29b4d7", p0, p0) == "#29b4d7"
    assert recolor.map_color("#ffffff", p0, p1) == "#ffffff"
    assert recolor.map_color("#29b4d7", p0, p1) == "#ff0000"


def test_map_cli(p0):
    out = subprocess.run([sys.executable, "-I", RECOLOR, "map", NEON_PATH, "#29b4d7"],
                         capture_output=True, text=True)
    assert out.returncode == 0
    assert out.stdout.strip() == "#29b4d7"


def _palette_file(tmp_path, colors):
    p = tmp_path / "palette.json"
    p.write_text(json.dumps({"name": "test", "source": "test", "colors": colors}))
    return str(p)


def test_write_mode_root_and_drift(tmp_path, p1):
    root = tmp_path / "root"
    root.mkdir()
    pal = _palette_file(tmp_path, p1)
    # premier rendu : écriture de tous les fichiers
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        assert recolor.render(pal, root=str(root)) == 0
    assert buf.getvalue().count("wrote ") == len(_manifest())
    state = root / ".local" / "state" / "desk" / "theme" / "rendered.sha"
    record = json.loads(state.read_text())
    assert len(record) == len(_manifest())
    # un fichier rendu est bien recoloré
    hypr = root / ".config" / "hypr" / "colors.conf"
    assert "$cyan      = rgb(ff0000)" in hypr.read_text()
    # second rendu identique : rien n'est écrit, aucun backup
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        recolor.render(pal, root=str(root))
    assert "wrote " not in buf.getvalue() and "DRIFT" not in buf.getvalue()
    assert glob.glob(str(hypr) + ".bak-theme-*") == []
    # édition manuelle puis nouveau rendu : backup + DRIFT
    hypr.write_text(hypr.read_text() + "# edit manuel\n")
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        recolor.render(pal, root=str(root))
    assert "DRIFT .config/hypr/colors.conf" in buf.getvalue()
    baks = glob.glob(str(hypr) + ".bak-theme-*")
    assert len(baks) == 1
    assert "# edit manuel" in open(baks[0], encoding="utf-8").read()
    assert "# edit manuel" not in hypr.read_text()


def test_write_mode_refuses_symlink(tmp_path, p1):
    root = tmp_path / "root"
    (root / ".config" / "hypr").mkdir(parents=True)
    dest = tmp_path / "elsewhere.conf"
    dest.write_text("keep\n")
    link = root / ".config" / "hypr" / "colors.conf"
    os.symlink(dest, link)
    pal = _palette_file(tmp_path, p1)
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        recolor.render(pal, root=str(root))
    assert "WARN symlink .config/hypr/colors.conf" in buf.getvalue()
    assert os.path.islink(link)
    assert dest.read_text() == "keep\n"


def test_write_mode_keeps_file_mode(tmp_path, p1):
    root = tmp_path / "root"
    target = root / ".config" / "hypr" / "colors.conf"
    target.parent.mkdir(parents=True)
    target.write_text("old\n")
    os.chmod(target, 0o600)
    with contextlib.redirect_stdout(io.StringIO()):
        recolor.render(_palette_file(tmp_path, p1), root=str(root))
    assert (os.stat(target).st_mode & 0o777) == 0o600


def test_hash3_short_hex():
    import recolor
    p0 = recolor.load_colors(recolor.P0_PATH)
    p1 = dict(p0, overlay="#7a1010", surface="#501010", base="#200808", mantle="#300a0a")
    assert recolor.recolor_text('fill="#fff"', p0, p1, "a.svg") == 'fill="#fff"'
    out = recolor.recolor_text('stop-color:#666;', p0, p1, "a.svg")
    assert out.startswith("stop-color:#") and len(out) == len("stop-color:#666666;")
    assert recolor.recolor_text('#666', p0, p0, "a.svg") == '#666'
    assert recolor.recolor_text('&#123;', p0, p1, "a.svg") == '&#123;'
