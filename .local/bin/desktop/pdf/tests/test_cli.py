import json, os, pathlib, subprocess, sys
from conftest import make_pdf
DIR = pathlib.Path(__file__).resolve().parents[2]


def cli(*a, stdin=""):
    env = {"PATH": "/usr/bin", "HOME": str(pathlib.Path.home()), "DESK_PDF_LOG": os.devnull}
    return subprocess.run([sys.executable, "-m", "pdf.cli", *map(str, a)], cwd=DIR, input=stdin,
                          capture_output=True, text=True, env=env)


def test_tools_list():
    r = cli("tools")
    rows = [l.split("\t") for l in r.stdout.splitlines()]
    ids = [row[0] for row in rows]
    assert r.returncode == 0 and len(ids) == 16 and ids[0] == "merge" and "webpage" in ids
    assert all(len(row) == 5 and " ‖ " in row[1] for row in rows)


def test_options_json():
    opts = json.loads(cli("options", "compress").stdout)
    assert opts[0]["key"] == "level" and opts[0]["default"] == "recommended"
    assert {c[0] for c in opts[0]["choices"]} == {"light", "recommended", "strong"}


def test_run_and_codes(pdf3):
    r = cli("run", "rotate", "--opt", "angle=180", pdf3)
    assert r.returncode == 0 and r.stdout.strip().endswith("doc-rotated.pdf")
    r = cli("run", "remove", "--opt", "ranges=9", pdf3)
    assert r.returncode == 1 and "9" in r.stderr
    assert cli("run", "nope", pdf3).returncode == 2
    assert cli("run", "rotate", "--opt", "bogus", pdf3).returncode == 2


def test_merge_takes_all_files(tmp_path):
    a = make_pdf(tmp_path / "a.pdf", 1); b = make_pdf(tmp_path / "b.pdf", 2)
    r = cli("run", "merge", a, b)
    assert r.returncode == 0 and r.stdout.strip().endswith("a-merged.pdf")


def test_per_file_tools_process_each(tmp_path):
    a = make_pdf(tmp_path / "a.pdf", 1); b = make_pdf(tmp_path / "b.pdf", 2)
    r = cli("run", "rearrange", a, b)
    assert r.returncode == 0 and len(r.stdout.split()) == 2


def test_password_flow(pdf3):
    r = cli("run", "protect", "--password-stdin", pdf3, stdin="\nsecret\n")
    prot = r.stdout.strip()
    assert r.returncode == 0 and "secret" not in r.stderr + r.stdout
    assert cli("run", "unlock", prot).returncode == 3
    bad = cli("run", "unlock", "--password-stdin", prot, stdin="bad\n")
    assert bad.returncode == 3 and "bad" not in bad.stderr
    assert cli("run", "unlock", "--password-stdin", prot, stdin="secret\n").returncode == 0


def test_log_never_contains_password(pdf3, tmp_path):
    log = tmp_path / "pdf.log"
    env = {"PATH": "/usr/bin", "HOME": str(pathlib.Path.home()), "DESK_PDF_LOG": str(log)}
    subprocess.run([sys.executable, "-m", "pdf.cli", "run", "protect", "--password-stdin", str(pdf3)],
                   cwd=DIR, input="\nhunter2\n", capture_output=True, text=True, env=env)
    prot = pdf3.with_name("doc-protected.pdf")
    subprocess.run([sys.executable, "-m", "pdf.cli", "run", "unlock", "--password-stdin", str(prot)],
                   cwd=DIR, input="wrongpw\n", capture_output=True, text=True, env=env)
    text = log.read_text()
    assert "protect" in text and "hunter2" not in text and "wrongpw" not in text
