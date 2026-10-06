import pytest
from pdf.naming import out_path, out_dir, atomic_file, atomic_dir


def test_out_path_suffix_and_unique(tmp_path):
    src = tmp_path / "NDA.pdf"; src.write_bytes(b"x")
    p = out_path(src, "signed")
    assert p == tmp_path / "NDA-signed.pdf"
    p.write_bytes(b"y")
    assert out_path(src, "signed") == tmp_path / "NDA-signed-2.pdf"


def test_out_path_ext_and_dir(tmp_path):
    src = tmp_path / "a.docx"
    assert out_path(src, "", ".pdf") == tmp_path / "a.pdf"
    assert out_path(src, "x", directory=tmp_path / "d") == tmp_path / "d" / "a-x.pdf"


def test_out_dir_unique(tmp_path):
    src = tmp_path / "r.pdf"
    (tmp_path / "r-split").mkdir()
    assert out_dir(src, "split") == tmp_path / "r-split-2"


def test_atomic_file_cleans_on_error(tmp_path):
    dest = tmp_path / "o.pdf"
    with pytest.raises(RuntimeError):
        with atomic_file(dest) as tmp:
            tmp.write_bytes(b"half"); raise RuntimeError
    assert list(tmp_path.iterdir()) == []


def test_atomic_file_ok(tmp_path):
    dest = tmp_path / "o.pdf"
    with atomic_file(dest) as tmp:
        tmp.write_bytes(b"ok")
    assert dest.read_bytes() == b"ok" and len(list(tmp_path.iterdir())) == 1


def test_atomic_dir(tmp_path):
    dest = tmp_path / "out"
    with pytest.raises(RuntimeError):
        with atomic_dir(dest) as d:
            (d / "f").write_text("x"); raise RuntimeError
    assert list(tmp_path.iterdir()) == []
    with atomic_dir(dest) as d:
        (d / "f").write_text("x")
    assert (dest / "f").exists()
