import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["DESK_PDF_NO_NOTIFY"] = "1"
import pikepdf, pytest
from conftest import make_pdf
from pdf import app as appmod
from pdf.qtutil import ensure_app


@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setattr(appmod, "FAVORITES", tmp_path / "fav")
    ensure_app()
    w = appmod.MainWindow()
    yield w
    w.close()


def test_home_has_16_tiles(win):
    assert len(win.home.tiles) == 16
    assert win.home.order()[0] == "merge"


def test_favorite_goes_first(win):
    win.home.tiles["sign"].star.click()
    assert win.home.order()[0] == "sign"
    win.home.tiles["sign"].star.click()
    assert win.home.order()[0] == "merge"


def test_drop_filters_tiles(win, pdf3):
    win.home.add_files([pdf3])
    assert win.home.tiles["compress"].isEnabled()
    assert not win.home.tiles["img2pdf"].isEnabled()
    assert not win.home.tiles["merge"].isEnabled()


def test_simple_tool_runs(win, pdf3):
    win.open_tool("rotate", [pdf3])
    page = win.page
    page.widgets["angle"].setCurrentIndex(page.widgets["angle"].findData("180"))
    page.worker = None
    from pdf.qtutil import Worker
    got = {}
    w = Worker("rotate", page.inputs(), page.values())
    w.done.connect(lambda p, n: got.update(paths=p))
    w.run()   # synchrone
    [out] = got["paths"]
    with pikepdf.open(out) as p:
        assert int(p.pages[0].obj.get("/Rotate", 0)) == 180


def test_split_visibility(win, pdf3):
    win.open_tool("split", [pdf3])
    page = win.page
    assert page.rows["ranges"][1].isHidden()
    page.widgets["mode"].setCurrentIndex(page.widgets["mode"].findData("ranges"))
    assert not page.rows["ranges"][1].isHidden()
