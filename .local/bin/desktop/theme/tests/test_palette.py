import json
import os
import subprocess
import sys

import pytest

THEME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PALETTE_PY = os.path.join(THEME_DIR, "palette.py")

import palette  # noqa: E402  (conftest.py puts THEME_DIR on sys.path)
from color import ROLES, contrast, hex_to_lch, hue_diff  # noqa: E402

PRESET_NAMES = ["catppuccin-mocha", "tokyo-night", "rose-pine", "gruvbox-dark",
                "nord", "dracula", "kanagawa", "everforest", "neon-graffiti"]
ACCENTS = ("cyan", "blue", "magenta", "pink", "gold", "orange", "red", "green")
IMAGES = {
    "einstein": "/home/dorian/Images/Wallpapers/einstein.jpg",
    "osx_like": "/home/dorian/Images/Wallpapers/osx_like.jpg",
    "ski": "/home/dorian/Images/Wallpapers/ski.jpg",
}


def _lightness(hex_):
    return hex_to_lch(hex_)[0]


def _check_palette_shape(pal):
    palette.validate(pal)
    assert set(pal["colors"]) == set(ROLES)


def _check_contrast(pal):
    c = pal["colors"]
    assert contrast(c["text"], c["base"]) >= 7.0
    for r in ACCENTS:
        assert contrast(c[r], c["base"]) >= 4.5, r


@pytest.mark.parametrize("name", PRESET_NAMES)
def test_preset_valid(name):
    pal = palette.load_preset(name)
    _check_palette_shape(pal)
    c = pal["colors"]
    assert pal["source"] == "preset"
    assert _lightness(c["base"]) < _lightness(c["mantle"]) < _lightness(c["surface"]) < _lightness(c["overlay"])
    assert contrast(c["text"], c["base"]) >= 7.0


def test_preset_list_contains_all_presets():
    assert set(PRESET_NAMES) <= set(palette.list_presets())


def test_validate_rejects_bad_palette():
    good = palette.load_preset("nord")
    bad = json.loads(json.dumps(good))
    bad["colors"]["cyan"] = "#12345"
    with pytest.raises(ValueError):
        palette.validate(bad)
    missing = json.loads(json.dumps(good))
    del missing["colors"]["gold"]
    with pytest.raises(ValueError):
        palette.validate(missing)


@pytest.mark.parametrize("img", sorted(IMAGES))
def test_auto_palette_valid_and_contrast(img):
    if not os.path.exists(IMAGES[img]):
        pytest.fail("fond absent (déplacé de ~/Images/Wallpapers ?)")
    pal = palette.auto_palette(IMAGES[img])
    _check_palette_shape(pal)
    assert pal["name"] == img
    assert pal["source"] == "auto:" + IMAGES[img]
    _check_contrast(pal)


@pytest.mark.parametrize("img", sorted(IMAGES))
def test_auto_palette_deterministic_cli(img):
    if not os.path.exists(IMAGES[img]):
        pytest.fail("fond absent (déplacé de ~/Images/Wallpapers ?)")
    outs = []
    for _ in range(2):
        r = subprocess.run([sys.executable, "-I", PALETTE_PY, "auto", IMAGES[img], "--no-cache"],
                           capture_output=True, text=True, check=True)
        outs.append(json.loads(r.stdout))
    assert outs[0] == outs[1]


def test_einstein_accents_come_from_image():
    """Sanité : la teinte cyan de la palette auto d'einstein.jpg est proche d'une
    teinte accent néon (cyan, magenta ou or).

    XFAIL volontaire : avec l'algorithme du spec (histogramme C², pics gloutons),
    einstein.jpg donne a1 ≈ 26° (rouge-orangé des tags), qui n'est à moins de 40°
    d'aucune teinte néon (cyan 220°, magenta 340°, or 90°). Les accents restent
    issus de l'image ; l'écart est documenté dans le rapport, pas masqué.
    """
    if not os.path.exists(IMAGES["einstein"]):
        pytest.fail("fond absent (déplacé de ~/Images/Wallpapers ?)")
    pal = palette.auto_palette(IMAGES["einstein"])
    neon = palette.load_preset("neon-graffiti")["colors"]
    cyan_h = hex_to_lch(pal["colors"]["cyan"])[2]
    refs = [hex_to_lch(neon[r])[2] for r in ("cyan", "magenta", "gold")]
    assert any(abs(hue_diff(cyan_h, ref)) <= 40 for ref in refs)


@pytest.mark.parametrize("name", ["neon-graffiti"])
def test_swatch_writes_png(tmp_path, name):
    out = tmp_path / "s.png"
    palette.swatch(palette.load_preset(name), str(out))
    assert out.stat().st_size > 0
