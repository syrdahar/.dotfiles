import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["DESK_PDF_NO_NOTIFY"] = "1"
import pikepdf
from conftest import make_pdf, page_texts
from pdf.qtutil import ensure_app


import pytest

PAGES = []


@pytest.fixture(autouse=True)
def _shutdown():
    yield
    while PAGES:
        PAGES.pop().shutdown()


def make(tmp_path):
    ensure_app()
    from pdf.organizer import OrganizerPage
    a = make_pdf(tmp_path / "a.pdf", 3, "A{}"); b = make_pdf(tmp_path / "b.pdf", 2, "B{}")
    page = OrganizerPage("merge", [a, b])
    PAGES.append(page)
    return page


def test_load_two_files(tmp_path):
    page = make(tmp_path)
    assert page.list.count() == 5 and not page.dirty


def test_rotate_delete_undo(tmp_path):
    page = make(tmp_path)
    page.list.item(1).setSelected(True)
    page.rotate_selected(90)
    assert page.page_refs()[1].rotate == 90 and page.dirty
    page.delete_selected()
    assert page.list.count() == 4
    page.undo()
    assert page.list.count() == 5 and page.page_refs()[1].rotate == 90
    page.undo()
    assert page.page_refs()[1].rotate == 0
    page.redo()
    assert page.page_refs()[1].rotate == 90


def test_move_and_save(tmp_path):
    page = make(tmp_path)
    it = page.list.takeItem(4)          # B2 en tête (comme un glisser-déposer)
    page.list.insertItem(0, it)
    page.after_move()
    assert page.dirty
    out = page.save()
    assert out.name == "a-merged.pdf"
    assert page_texts(out) == ["B2", "A1", "A2", "A3", "B1"]
    assert not page.dirty


def test_reverse_and_extract(tmp_path):
    page = make(tmp_path)
    page.reverse_all()
    assert [r.index for r in page.page_refs()][:2] == [1, 0]
    page.undo()
    assert page.page_refs()[0].index == 0
    page.list.item(0).setSelected(True); page.list.item(2).setSelected(True)
    out = page.extract_selected()
    assert page_texts(out) == ["A1", "A3"]


def test_rotation_saved(tmp_path):
    page = make(tmp_path)
    page.list.item(0).setSelected(True)
    page.rotate_selected(-90)
    out = page.save()
    with pikepdf.open(out) as p:
        assert int(p.pages[0].obj.get("/Rotate", 0)) == 270
