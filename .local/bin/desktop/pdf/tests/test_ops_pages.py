import pymupdf as fitz
import pikepdf, pytest
from conftest import make_pdf, page_texts
from pdf import ops


def test_merge(tmp_path):
    a = make_pdf(tmp_path / "a.pdf", 2, "A{}"); b = make_pdf(tmp_path / "b.pdf", 1, "B{}")
    [out] = ops.merge([a, b])
    assert out.name == "a-merged.pdf"
    assert page_texts(out) == ["A1", "A2", "B1"]
    assert [e[1] for e in fitz.open(out).get_toc()] == ["a", "b"]


def test_split_each_every_ranges(pdf3):
    [d] = ops.split(pdf3, "each")
    assert sorted(p.name for p in d.iterdir()) == ["doc-001.pdf", "doc-002.pdf", "doc-003.pdf"]
    [d2] = ops.split(pdf3, "every", n=2)
    assert [len(page_texts(p)) for p in sorted(d2.iterdir())] == [2, 1]
    [d3] = ops.split(pdf3, "ranges", ranges="1,2-3")
    assert [page_texts(p) for p in sorted(d3.iterdir())] == [["PAGE 1"], ["PAGE 2", "PAGE 3"]]


def test_rotate_subset(pdf3):
    [out] = ops.rotate(pdf3, 90, "2")
    with pikepdf.open(out) as p:
        assert [int(pg.obj.get("/Rotate", 0)) for pg in p.pages] == [0, 90, 0]


def test_remove_extract_reverse(pdf3):
    assert page_texts(ops.remove_pages(pdf3, "2")[0]) == ["PAGE 1", "PAGE 3"]
    assert page_texts(ops.extract_pages(pdf3, "3,1")[0]) == ["PAGE 3", "PAGE 1"]
    assert page_texts(ops.reverse(pdf3)[0]) == ["PAGE 3", "PAGE 2", "PAGE 1"]
    with pytest.raises(ops.OpError):
        ops.remove_pages(pdf3, "1-3")


def test_build_across_files(tmp_path):
    a = make_pdf(tmp_path / "a.pdf", 2, "A{}"); b = make_pdf(tmp_path / "b.pdf", 1, "B{}")
    out = ops.build([ops.PageRef(b, 0, 180), ops.PageRef(a, 1)], tmp_path / "x.pdf")
    assert page_texts(out) == ["B1", "A2"]
    with pikepdf.open(out) as p:
        assert int(p.pages[0].obj.get("/Rotate", 0)) == 180


def test_protect_unlock(pdf3):
    [prot] = ops.protect(pdf3, "s3cret", forbid_print_copy=True)
    with pytest.raises(pikepdf.PasswordError):
        pikepdf.open(prot)
    with pikepdf.open(prot, password="s3cret") as p:
        assert p.encryption.R == 6
        assert not p.allow.print_highres
    with pytest.raises(ops.PasswordError) as e:
        ops.unlock(prot)
    assert not e.value.wrong
    with pytest.raises(ops.PasswordError) as e:
        ops.unlock(prot, "bad")
    assert e.value.wrong
    [un] = ops.unlock(prot, "s3cret")
    assert not pikepdf.open(un).is_encrypted
    assert page_texts(un) == ["PAGE 1", "PAGE 2", "PAGE 3"]


def test_encrypted_input_to_other_op(pdf3):
    [prot] = ops.protect(pdf3, "pw")
    with pytest.raises(ops.PasswordError):
        ops.rotate(prot, 90)
    [out] = ops.rotate(prot, 90, password="pw")
    assert not pikepdf.open(out).is_encrypted
    [m] = ops.merge([prot, pdf3], password="pw")
    assert len(page_texts(m)) == 6


def test_no_overwrite(pdf3):
    a = ops.reverse(pdf3)[0]; b = ops.reverse(pdf3)[0]
    assert a.name == "doc-reordered.pdf" and b.name == "doc-reordered-2.pdf"


def test_bad_range_is_operror(pdf3):
    with pytest.raises(ops.OpError):
        ops.rotate(pdf3, 90, "7")


def test_not_a_pdf(tmp_path):
    f = tmp_path / "x.pdf"; f.write_text("hello")
    with pytest.raises(ops.OpError):
        ops.reverse(f)
