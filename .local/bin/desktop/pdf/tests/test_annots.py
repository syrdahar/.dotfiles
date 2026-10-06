import pymupdf as fitz
import pytest
from conftest import make_pdf
from pdf import annots, ops


def png(w=40, h=20):
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, w, h), 1)
    pix.set_rect(pix.irect, (20, 40, 140, 255))
    return pix.tobytes("png")


def test_redaction_removes_text(pdf3, tmp_path):
    r = fitz.open(pdf3)[0].search_for("PAGE 1")[0]
    out = annots.apply(pdf3, [annots.MaskItem(0, tuple(r), redact=True)], tmp_path / "o.pdf")
    assert "PAGE 1" not in fitz.open(out)[0].get_text()


def test_whiteout_also_removes_text(pdf3, tmp_path):
    r = fitz.open(pdf3)[1].search_for("PAGE 2")[0]
    out = annots.apply(pdf3, [annots.MaskItem(1, tuple(r), redact=False)], tmp_path / "o.pdf")
    assert "PAGE 2" not in fitz.open(out)[1].get_text()


def test_text_and_shapes_are_annotations(pdf3, tmp_path):
    items = [annots.TextItem(0, (100, 200, 300, 230), "Bonjour é"),
             annots.ShapeItem(1, "rect", (50, 50, 150, 150), color=(1, 0, 0)),
             annots.ShapeItem(1, "ellipse", (200, 50, 300, 150)),
             annots.ShapeItem(1, "arrow", (0, 0, 0, 0), p1=(10, 300), p2=(200, 320)),
             annots.HighlightItem(2, (60, 70, 200, 110)),
             annots.InkItem(2, [[(100, 400), (150, 420), (200, 400)]], color=(0, 0, 1), width=2)]
    out = annots.apply(pdf3, items, tmp_path / "o.pdf")
    d = fitz.open(out)
    assert [a.type[1] for a in d[0].annots()] == ["FreeText"]
    pg0 = d[0]
    assert "Bonjour é" in pg0.first_annot.info["content"]
    assert sorted(a.type[1] for a in d[1].annots()) == ["Circle", "Line", "Square"]
    assert sorted(a.type[1] for a in d[2].annots()) == ["Highlight", "Ink"]


def test_images_and_signatures_in_content(pdf3, tmp_path):
    items = [annots.ImageItem(0, (100, 100, 200, 150), png()),
             annots.SignatureItem(1, (300, 600, 460, 680), png())]
    out = annots.apply(pdf3, items, tmp_path / "o.pdf")
    d = fitz.open(out)
    assert len(d[0].get_images()) == 1 and len(d[1].get_images()) == 1
    assert list(d[1].annots()) == []


def test_flatten_bakes(pdf3, tmp_path):
    out = annots.apply(pdf3, [annots.TextItem(0, (100, 200, 300, 230), "Signé")], tmp_path / "o.pdf", flatten=True)
    p = fitz.open(out)[0]
    assert list(p.annots()) == [] and "Signé" in p.get_text()


def make_form(path):
    d = fitz.open(); pg = d.new_page()
    w = fitz.Widget(); w.field_name = "nom"; w.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    w.rect = fitz.Rect(50, 50, 250, 80); pg.add_widget(w)
    c = fitz.Widget(); c.field_name = "ok"; c.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
    c.rect = fitz.Rect(50, 100, 70, 120); pg.add_widget(c)
    k = fitz.Widget(); k.field_name = "pays"; k.field_type = fitz.PDF_WIDGET_TYPE_COMBOBOX
    k.choice_values = ["France", "Suisse"]; k.rect = fitz.Rect(50, 140, 250, 160); pg.add_widget(k)
    d.save(path); return path


def test_form_fields_and_fill(tmp_path):
    src = make_form(tmp_path / "f.pdf")
    fields = {f["name"]: f for f in annots.form_fields(src)}
    assert fields["nom"]["type"] == "text" and fields["ok"]["type"] == "checkbox"
    assert fields["pays"]["choices"] == ["France", "Suisse"] and fields["nom"]["page"] == 0
    out = annots.apply(src, [], tmp_path / "o.pdf", form={"nom": "Dorian", "ok": True, "pays": "Suisse"})
    vals = {w.field_name: w.field_value for w in fitz.open(out)[0].widgets()}
    assert vals["nom"] == "Dorian" and vals["pays"] == "Suisse" and vals["ok"] not in ("Off", False, "")
    flat = annots.apply(src, [], tmp_path / "f2.pdf", form={"nom": "Dorian"}, flatten=True)
    pg = fitz.open(flat)[0]
    assert "Dorian" in pg.get_text() and list(pg.widgets()) == []


def test_rotated_page_coordinates(tmp_path):
    src = make_pdf(tmp_path / "r.pdf", 1)
    d = fitz.open(src); d[0].set_rotation(90); d.save(tmp_path / "rot.pdf")
    # visuellement (page tournée, 842 × 595) : un masque en haut à gauche
    out = annots.apply(tmp_path / "rot.pdf", [annots.MaskItem(0, (0, 0, 842, 595), redact=True)], tmp_path / "o.pdf")
    assert fitz.open(out)[0].get_text().strip() == ""
    out2 = annots.apply(tmp_path / "rot.pdf", [annots.ShapeItem(0, "rect", (10, 10, 110, 60))], tmp_path / "o2.pdf")
    doc = fitz.open(out2)
    page = doc[0]
    vis = (page.first_annot.rect * page.rotation_matrix).normalize()
    assert abs(vis.x0 - 10) < 3 and abs(vis.y0 - 10) < 3 and abs(vis.width - 100) < 4   # + épaisseur du trait


def test_encrypted_source(pdf3, tmp_path):
    [prot] = ops.protect(pdf3, "pw")
    with pytest.raises(ops.PasswordError):
        annots.apply(prot, [], tmp_path / "o.pdf")
    out = annots.apply(prot, [annots.TextItem(0, (10, 10, 100, 30), "x")], tmp_path / "o.pdf", password="pw")
    assert not fitz.open(out).needs_pass
