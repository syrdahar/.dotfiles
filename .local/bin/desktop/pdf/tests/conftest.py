import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))   # ~/.local/bin/desktop
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))       # conftest importable
import pymupdf as fitz
import pytest


def make_pdf(path, n=3, text="PAGE {}"):
    doc = fitz.open()
    for i in range(n):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 100), text.format(i + 1), fontsize=24)
    doc.save(path)
    return path


@pytest.fixture
def pdf3(tmp_path):
    return make_pdf(tmp_path / "doc.pdf", 3)


def page_texts(path, password=None):
    doc = fitz.open(path)
    if password:
        doc.authenticate(password)
    return [p.get_text().strip() for p in doc]
