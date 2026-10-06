import shutil, subprocess
import pymupdf as fitz
import pytest
from conftest import make_pdf, page_texts
from pdf import ops


def img_pdf(path, n=2):
    doc = fitz.open()
    for i in range(n):
        pg = doc.new_page()
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 1200, 1200), 0)
        pix.set_rect(pix.irect, (40 * i, 120, 200))
        for y in range(0, 1200, 7):   # du détail, pour que la compression ait du travail
            pix.set_rect(fitz.IRect(0, y, 1200, y + 2), (255, (y * 3) % 256, 0))
        pg.insert_image(fitz.Rect(50, 50, 550, 550), pixmap=pix)
    doc.save(path)
    return path


def test_compress_smaller_or_skipped(tmp_path):
    src = img_pdf(tmp_path / "big.pdf", 3)
    out = ops.compress(src, "strong")
    before, after = ops.LAST_GAIN
    assert out and out[0].name == "big-compressed.pdf"
    assert out[0].stat().st_size < src.stat().st_size and after < before
    assert len(fitz.open(out[0])) == 3
    assert [p.name for p in tmp_path.iterdir() if ".tmp" in p.name] == []


def test_compress_already_optimal(tmp_path):
    src = tmp_path / "tiny.pdf"
    make_pdf(src, 1, "x")
    subprocess.run(["qpdf", "--object-streams=generate", "--compress-streams=y", "--replace-input", str(src)], check=False)
    out = ops.compress(src, "light")
    before, after = ops.LAST_GAIN
    assert (out == []) == (after >= before)
    if not out:
        assert not (tmp_path / "tiny-compressed.pdf").exists()


def test_images_roundtrip(tmp_path):
    src = img_pdf(tmp_path / "i.pdf", 2)
    [d] = ops.pdf_to_images(src, "png", 72)
    imgs = sorted(d.iterdir())
    assert d.name == "i-images" and len(imgs) == 2 and imgs[0].suffix == ".png"
    [back] = ops.images_to_pdf(imgs)
    assert back.name.endswith("-images.pdf") and len(fitz.open(back)) == 2
    [back2] = ops.images_to_pdf(imgs, fit="image")
    assert len(fitz.open(back2)) == 2
    [jd] = ops.pdf_to_images(src, "jpg", 72, ranges="2")
    assert [p.suffix for p in jd.iterdir()] == [".jpg"]
    [ex] = ops.extract_images(src)
    assert ex.name == "i-extracted" and len(list(ex.iterdir())) >= 2


def test_images_webp(tmp_path):
    w = tmp_path / "a.webp"
    subprocess.run(["magick", "-size", "50x40", "xc:red", str(w)], check=True)
    [out] = ops.images_to_pdf([w])
    assert len(fitz.open(out)) == 1


def test_extract_images_none(pdf3):
    with pytest.raises(ops.OpError):
        ops.extract_images(pdf3)


def test_to_text(pdf3):
    [txt] = ops.convert(pdf3)
    assert txt.suffix == ".txt" and "PAGE 2" in txt.read_text()


def test_markdown_to_pdf(tmp_path):
    md = tmp_path / "n.md"; md.write_text("# Titre\n\nBonjour **monde**")
    [out] = ops.convert(md)
    assert out.name == "n.pdf" and "Bonjour" in fitz.open(out)[0].get_text()


def test_txt_to_pdf(tmp_path):
    f = tmp_path / "t.txt"; f.write_text("ligne <b>brute</b>\nsuite")
    [out] = ops.convert(f)
    assert "<b>brute</b>" in fitz.open(out)[0].get_text()


def test_local_html_webpage(tmp_path):
    h = tmp_path / "p.html"; h.write_text("<title>Ma page</title><p>Salut</p>")
    [out] = ops.webpage(str(h), tmp_path / "dl")
    assert out.name == "Ma page.pdf" and "Salut" in fitz.open(out)[0].get_text()


def test_webpage_unreachable(tmp_path):
    with pytest.raises(ops.OpError):
        ops.webpage("http://127.0.0.1:9/nothing", tmp_path)


@pytest.mark.skipif(shutil.which("soffice") is None, reason="LibreOffice absent")
def test_office(tmp_path):
    src = tmp_path / "a.txt"; src.write_text("Bonjour office")
    subprocess.run(["soffice", "--headless", "--convert-to", "odt", "--outdir", str(tmp_path), str(src)],
                   check=True, capture_output=True, timeout=120)
    [out] = ops.convert(tmp_path / "a.odt")
    assert "Bonjour office" in fitz.open(out)[0].get_text()


def test_office_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda n: None)
    f = tmp_path / "a.docx"; f.write_bytes(b"x")
    with pytest.raises(ops.OpError, match="libreoffice"):
        ops.convert(f)


def test_convert_unsupported(tmp_path):
    f = tmp_path / "a.xyz"; f.write_bytes(b"x")
    with pytest.raises(ops.OpError):
        ops.convert(f)
