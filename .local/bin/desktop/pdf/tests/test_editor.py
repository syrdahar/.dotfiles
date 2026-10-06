import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["DESK_PDF_NO_NOTIFY"] = "1"
import pymupdf as fitz
import pytest
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QColor, QImage
from conftest import make_pdf
from pdf.qtutil import ensure_app

PAGES = []


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    while PAGES:
        PAGES.pop().shutdown()


def editor(path, mode="edit"):
    ensure_app()
    from pdf.editor import EditorPage
    page = EditorPage(path, mode)
    PAGES.append(page)
    return page


def sig_png():
    from pdf.signature import png_bytes
    img = QImage(120, 40, QImage.Format.Format_ARGB32)
    img.fill(QColor(20, 40, 140))
    return png_bytes(img)


def test_text_shape_undo_save(pdf3):
    ed = editor(pdf3)
    assert len(ed.slots) == 3 and not ed.dirty
    ed.scene.addItem(ed.text_obj(QPointF(100, 100), "Bonjour"))
    ed.record()
    ed.create("rect", QPointF(50, ed.slots[1][0] + 50), QPointF(150, ed.slots[1][0] + 120), [])
    assert len(ed.objects()) == 2 and ed.dirty
    ed.undo()
    assert len(ed.objects()) == 1
    ed.redo()
    assert len(ed.objects()) == 2
    out = ed.save()
    assert out.name == "doc-edited.pdf" and not ed.dirty
    d = fitz.open(out)
    assert [a.type[1] for a in d[0].annots()] == ["FreeText"]
    pg1 = d[1]
    assert [a.type[1] for a in pg1.annots()] == ["Square"]
    r = pg1.first_annot.rect
    assert abs(r.x0 - 50) < 3 and abs(r.y0 - 50) < 3


def test_redact_via_editor(pdf3, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    ed = editor(pdf3)
    r = fitz.open(pdf3)[0].search_for("PAGE 1")[0]
    ed.create("redact", QPointF(r.x0 - 2, r.y0 - 2), QPointF(r.x1 + 2, r.y1 + 2), [])
    out = ed.save()
    assert "PAGE 1" not in fitz.open(out)[0].get_text()


def test_sign_duplicate_flatten(pdf3, monkeypatch):
    from PyQt6.QtWidgets import QInputDialog
    ed = editor(pdf3, "sign")
    ed.sig_png = sig_png()
    ed.create("signature", QPointF(300, 700), QPointF(300, 700), [])
    [sig] = ed.objects()
    sig.setSelected(True)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("1-3", True))
    ed.duplicate_selected()
    assert len(ed.objects()) == 3
    ed.stamp_date()
    out = ed.save()
    assert out.name == "doc-signed.pdf"
    d = fitz.open(out)
    for i in range(3):
        pg = d[i]
        assert list(pg.annots()) == [] and len(pg.get_images()) == 1
    assert any(c.isdigit() for c in d[0].get_text() + d[1].get_text() + d[2].get_text())


def test_form_panel(tmp_path):
    src = tmp_path / "f.pdf"
    doc = fitz.open(); pg = doc.new_page()
    w = fitz.Widget(); w.field_name = "nom"; w.field_type = fitz.PDF_WIDGET_TYPE_TEXT; w.rect = fitz.Rect(50, 50, 250, 80)
    pg.add_widget(w); doc.save(src)
    ed = editor(src, "sign")
    widget, _ = ed.fields["nom"]
    widget.setText("Dorian H.")
    assert ed.dirty
    out = ed.save()
    pg = fitz.open(out)[0]
    assert "Dorian H." in pg.get_text() and list(pg.widgets()) == []


def test_signature_import_and_library(tmp_path, monkeypatch):
    ensure_app()
    from pdf import signature
    monkeypatch.setattr(signature, "SIG_DIR", tmp_path / "sigs")
    img = QImage(300, 120, QImage.Format.Format_RGB32)
    img.fill(QColor("white"))
    for x in range(60, 240):
        for y in range(58, 64):
            img.setPixelColor(x, y, QColor(10, 10, 10))
    f = tmp_path / "scan.png"; img.save(str(f))
    out = signature.import_image(f)
    assert out.width() < 200 and out.height() < 20
    assert out.pixelColor(0, 0).alpha() == 0
    assert out.pixelColor(out.width() // 2, out.height() // 2).alpha() > 200
    p = signature.save_png(out)
    assert signature.library() == [p] and oct(p.stat().st_mode)[-3:] == "600"


def test_pad_image():
    ensure_app()
    from pdf.signature import Pad
    pad = Pad()
    pad.resize(400, 200)
    assert pad.image() is None
    pad._press(QPointF(20, 100)); pad._move(QPointF(120, 80)); pad._move(QPointF(220, 120)); pad._release()
    img = pad.image()
    assert img is not None and img.width() > 200 and img.pixelColor(0, 0).alpha() == 0
