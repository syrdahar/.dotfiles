"""Moteur de desk pdf : une fonction par outil, sans interface.

Chaque outil reçoit des chemins et des options, écrit à côté de l'original
(naming.out_path / out_dir, jamais d'écrasement, écriture atomique) et
retourne la liste des chemins créés. Les erreurs sont des OpError au message
lisible ; PasswordError quand un mot de passe manque ou est faux.
"""
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import pymupdf as fitz
import pikepdf

from .errors import OpError, PasswordError
from .i18n import t
from .naming import atomic_dir, atomic_file, out_dir, out_path
from .pages import RangeError, parse_groups, parse_ranges  # noqa: F401  (RangeError réexporté)

WARNINGS = []   # avertissements non bloquants de la dernière opération (PDF réparé…)


# ── Ouverture ────────────────────────────────────────────────
def _password_error(src, password):
    if password:
        return PasswordError(t(f"Mot de passe incorrect pour {Path(src).name}",
                               f"Wrong password for {Path(src).name}"), wrong=True)
    return PasswordError(t(f"{Path(src).name} est protégé par un mot de passe",
                           f"{Path(src).name} is password-protected"))


def open_pdf(src, password=None):
    """pikepdf.Pdf ; les PDF abîmés sont réparés par qpdf (avertissement dans WARNINGS)."""
    try:
        pdf = pikepdf.open(src, password=password or "")
    except pikepdf.PasswordError:
        raise _password_error(src, password) from None
    except FileNotFoundError:
        raise OpError(t(f"Fichier introuvable : {src}", f"File not found: {src}")) from None
    except pikepdf.PdfError as e:
        raise OpError(t(f"{Path(src).name} n'est pas un PDF lisible ({e})",
                        f"{Path(src).name} is not a readable PDF ({e})")) from None
    if pdf.get_warnings():
        WARNINGS.append(t(f"{Path(src).name} était abîmé : réparé automatiquement",
                          f"{Path(src).name} was damaged: repaired automatically"))
    return pdf


def open_doc(src, password=None):
    """Même chose pour PyMuPDF (fitz.Document déjà déverrouillé)."""
    try:
        doc = fitz.open(src)
    except Exception as e:  # noqa: BLE001 — fitz lève des types variés
        raise OpError(t(f"{Path(src).name} n'est pas un PDF lisible ({e})",
                        f"{Path(src).name} is not a readable PDF ({e})")) from None
    if doc.needs_pass and not doc.authenticate(password or ""):
        doc.close()
        raise _password_error(src, password)
    return doc


def _save(pdf, dest, **kw):
    with atomic_file(dest) as tmp:
        pdf.save(tmp, **kw)
    return dest


def _copy_info(src_pdf, dst_pdf):
    try:
        for k, v in src_pdf.docinfo.items():
            dst_pdf.docinfo[k] = v
    except Exception:  # noqa: BLE001 — métadonnées cassées : on s'en passe
        pass


def _subset(src, indices, dest, password=None):
    with open_pdf(src, password) as pdf:
        new = pikepdf.new()
        _copy_info(pdf, new)
        for i in indices:
            new.pages.append(pdf.pages[i])
        return _save(new, dest)


# ── Pages ────────────────────────────────────────────────────
@dataclass
class PageRef:
    src: Path
    index: int
    rotate: int = 0


def build(pages, dest, passwords=None):
    """Assemble des pages de plusieurs PDF (organiseur) → dest."""
    passwords = passwords or {}
    opened = {}
    try:
        new = pikepdf.new()
        for ref in pages:
            key = Path(ref.src)
            if key not in opened:
                opened[key] = open_pdf(key, passwords.get(key))
                if len(opened) == 1:
                    _copy_info(opened[key], new)
            new.pages.append(opened[key].pages[ref.index])
            if ref.rotate % 360:
                new.pages[-1].rotate(ref.rotate % 360, relative=True)
        if not len(new.pages):
            raise OpError(t("Aucune page à enregistrer", "No page to save"))
        return _save(new, Path(dest))
    finally:
        for p in opened.values():
            p.close()


def merge(files, password=None):
    files = [Path(f) for f in files]
    if len(files) < 2:
        raise OpError(t("Il faut au moins deux fichiers à fusionner", "Merging needs at least two files"))
    dest = out_path(files[0], "merged")
    out, toc = fitz.open(), []
    for f in files:
        with open_doc(f, password) as doc:
            start = len(out)
            out.insert_pdf(doc, links=True, annots=True)
            toc.append([1, f.stem, start + 1])
            toc += [[lvl + 1, title, page + start] for lvl, title, page, *_ in doc.get_toc(simple=False)]
    out.set_toc(toc)
    with atomic_file(dest) as tmp:
        out.save(tmp, garbage=3, deflate=True)
    return [dest]


def split(src, mode="each", n=1, ranges="", password=None):
    src = Path(src)
    with open_pdf(src, password) as pdf:
        total = len(pdf.pages)
        if mode == "each":
            groups = [[i] for i in range(total)]
        elif mode == "every":
            n = int(n)
            if n < 1:
                raise OpError(t("N doit être ≥ 1", "N must be ≥ 1"))
            groups = [list(range(i, min(i + n, total))) for i in range(0, total, n)]
        elif mode == "ranges":
            groups = parse_groups(ranges, total)
        else:
            raise OpError(f"split: mode {mode!r}")
        dest = out_dir(src, "split")
        with atomic_dir(dest) as d:
            for k, g in enumerate(groups, 1):
                new = pikepdf.new()
                _copy_info(pdf, new)
                for i in g:
                    new.pages.append(pdf.pages[i])
                new.save(d / f"{src.stem}-{k:03d}.pdf")
    return [dest]


def rotate(src, angle=90, ranges="", password=None):
    angle = int(angle)
    if angle % 90:
        raise OpError(t("L'angle doit être un multiple de 90", "Angle must be a multiple of 90"))
    with open_pdf(src, password) as pdf:
        for i in parse_ranges(ranges, len(pdf.pages)):
            pdf.pages[i].rotate(angle, relative=True)
        return [_save(pdf, out_path(src, "rotated"))]


def remove_pages(src, ranges, password=None):
    with open_pdf(src, password) as pdf:
        drop = set(parse_ranges(ranges, len(pdf.pages)))
        if len(drop) == len(pdf.pages):
            raise OpError(t("Impossible de supprimer toutes les pages", "Cannot remove every page"))
        for i in sorted(drop, reverse=True):
            del pdf.pages[i]
        return [_save(pdf, out_path(src, "removed"))]


def extract_pages(src, ranges, password=None):
    with open_pdf(src, password) as pdf:
        idx = parse_ranges(ranges, len(pdf.pages))
    return [_subset(src, idx, out_path(src, "extract"), password)]


def reverse(src, password=None):
    with open_pdf(src, password) as pdf:
        n = len(pdf.pages)
    return [_subset(src, range(n - 1, -1, -1), out_path(src, "reordered"), password)]


# ── Sécurité ─────────────────────────────────────────────────
def protect(src, password_new, forbid_print_copy=False, password=None):
    if not password_new:
        raise OpError(t("Mot de passe vide", "Empty password"))
    if forbid_print_copy:
        allow = pikepdf.Permissions(print_lowres=False, print_highres=False, extract=False,
                                    modify_other=False, modify_assembly=False, modify_annotation=False,
                                    modify_form=False, accessibility=True)
        owner = secrets.token_urlsafe(24)   # sinon le mot de passe d'ouverture lèverait les restrictions
    else:
        allow, owner = pikepdf.Permissions(), password_new
    with open_pdf(src, password) as pdf:
        enc = pikepdf.Encryption(owner=owner, user=password_new, R=6, allow=allow)
        return [_save(pdf, out_path(src, "protected"), encryption=enc)]


def unlock(src, password=None):
    with open_pdf(src, password) as pdf:
        if not pdf.is_encrypted:
            raise OpError(t(f"{Path(src).name} n'est pas protégé", f"{Path(src).name} is not protected"))
        return [_save(pdf, out_path(src, "unlocked"), encryption=False)]


# ── Outils externes ──────────────────────────────────────────
PKG = {"gs": "ghostscript", "qpdf": "qpdf", "pdftoppm": "poppler", "pdfimages": "poppler",
       "pdftotext": "poppler", "magick": "imagemagick", "soffice": "libreoffice-fresh"}


def _run(cmd, timeout=300):
    try:
        return subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                              timeout=timeout, check=True, stdin=subprocess.DEVNULL)
    except FileNotFoundError:
        raise OpError(t(f"{cmd[0]} est introuvable (sudo pacman -S {PKG.get(cmd[0], cmd[0])})",
                        f"{cmd[0]} not found (sudo pacman -S {PKG.get(cmd[0], cmd[0])})")) from None
    except subprocess.TimeoutExpired:
        raise OpError(t(f"{cmd[0]} : délai dépassé ({timeout} s)", f"{cmd[0]}: timed out ({timeout} s)")) from None
    except subprocess.CalledProcessError as e:
        why = next((l for l in reversed((e.stderr or "").splitlines()) if l.strip()), f"code {e.returncode}")
        raise OpError(f"{cmd[0]} : {why[:200]}") from None


@contextmanager
def _workdir():
    d = Path(tempfile.mkdtemp(prefix="desk-pdf-"))   # 0700 : les copies déchiffrées n'y sont lisibles que par toi
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


@contextmanager
def _plain(src, password=None):
    """Chemin d'une version non chiffrée de src (src lui-même s'il ne l'est pas).
    Les outils externes ne voient ainsi jamais le mot de passe (ni dans ps, ni ailleurs)."""
    with open_pdf(src, password) as pdf:
        if not pdf.is_encrypted:
            yield Path(src)
            return
        with _workdir() as d:
            pdf.save(d / "plain.pdf", encryption=False)
            yield d / "plain.pdf"


# ── Compression ──────────────────────────────────────────────
LEVELS = {"light": "/printer", "recommended": "/ebook", "strong": "/screen"}
LAST_GAIN = None   # (taille avant, taille après) de la dernière compression


def compress(src, level="recommended", password=None):
    global LAST_GAIN
    src = Path(src)
    if level not in LEVELS:
        raise OpError(f"compress: level {level!r}")
    with _plain(src, password) as plain, _workdir() as d:
        _run(["gs", "-q", "-dSAFER", "-dNOPAUSE", "-dBATCH", "-sDEVICE=pdfwrite",
              "-dCompatibilityLevel=1.7", f"-dPDFSETTINGS={LEVELS[level]}",
              "-dDetectDuplicateImages=true", f"-sOutputFile={d / 'gs.pdf'}", plain])
        _run(["qpdf", "--object-streams=generate", "--recompress-flate", "--compression-level=9",
              d / "gs.pdf", d / "out.pdf"])
        before, after = src.stat().st_size, (d / "out.pdf").stat().st_size
        LAST_GAIN = (before, after)
        if after >= before:
            return []
        dest = out_path(src, "compressed")
        with atomic_file(dest) as tmp:
            shutil.copyfile(d / "out.pdf", tmp)
    return [dest]


# ── Images ───────────────────────────────────────────────────
NATIVE_IMG = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".jp2"}
IMAGE_EXT = NATIVE_IMG | {".webp", ".heic", ".heif", ".avif", ".gif", ".bmp", ".svg"}


def images_to_pdf(images, fit="a4"):
    import img2pdf
    images = [Path(i) for i in images]
    if not images:
        raise OpError(t("Aucune image", "No image"))
    if fit == "a4":
        a4 = (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297))
        layout = img2pdf.get_layout_fun(a4, fit=img2pdf.FitMode.into, auto_orient=True)
    else:
        layout = img2pdf.default_layout_fun
    dest = out_path(images[0], "images")
    with _workdir() as d:
        ready = []
        for k, img in enumerate(images):
            if not img.exists():
                raise OpError(t(f"Fichier introuvable : {img}", f"File not found: {img}"))
            if img.suffix.lower() not in NATIVE_IMG:
                img = _flatten_img(img, d / f"{k:04d}.png")
            ready.append(img)
        for k, img in enumerate(ready):   # img2pdf refuse la transparence : on l'aplatit sur blanc
            try:
                img2pdf.convert(str(img))
            except img2pdf.AlphaChannelError:
                ready[k] = _flatten_img(img, d / f"{k:04d}-flat.png")
            except Exception as e:  # noqa: BLE001
                raise OpError(t(f"Image illisible : {img.name} ({e})", f"Unreadable image: {img.name} ({e})")) from None
        with atomic_file(dest) as tmp:
            tmp.write_bytes(img2pdf.convert([str(i) for i in ready], layout_fun=layout))
    return [dest]


def _flatten_img(src, dest):
    _run(["magick", f"{src}[0]", "-background", "white", "-alpha", "remove", "-alpha", "off", dest])
    return dest


def pdf_to_images(src, fmt="png", dpi=150, ranges="", password=None):
    src = Path(src)
    if fmt not in ("png", "jpg"):
        raise OpError(f"pdf2img: format {fmt!r}")
    flag = ["-png"] if fmt == "png" else ["-jpeg", "-jpegopt", "quality=90"]
    with _plain(src, password) as plain:
        with open_pdf(plain) as pdf:
            n = len(pdf.pages)
        dest = out_dir(src, "images")
        with atomic_dir(dest) as d:
            if not (ranges or "").strip():
                _run(["pdftoppm", *flag, "-r", int(dpi), plain, d / src.stem])
            else:
                width = len(str(n))
                for i in parse_ranges(ranges, n):
                    _run(["pdftoppm", *flag, "-r", int(dpi), "-f", i + 1, "-l", i + 1, "-singlefile",
                          plain, d / f"{src.stem}-{i + 1:0{width}d}"])
    return [dest]


def extract_images(src, password=None):
    src = Path(src)
    with _plain(src, password) as plain:
        dest = out_dir(src, "extracted")
        with atomic_dir(dest) as d:
            _run(["pdfimages", "-all", plain, d / src.stem])
            if not any(d.iterdir()):
                raise OpError(t(f"{src.name} ne contient aucune image", f"{src.name} contains no image"))
    return [dest]


# ── Conversion ───────────────────────────────────────────────
OFFICE_EXT = {".doc", ".docx", ".odt", ".rtf", ".xls", ".xlsx", ".ods", ".csv",
              ".ppt", ".pptx", ".odp", ".odg", ".wpd", ".pages", ".key", ".numbers"}
WEB_EXT = {".html", ".htm", ".xhtml", ".md", ".markdown", ".txt"}
CONVERTIBLE_EXT = OFFICE_EXT | WEB_EXT | {".pdf"}


def to_text(src, password=None):
    src = Path(src)
    dest = out_path(src, "", ".txt")
    with _plain(src, password) as plain, atomic_file(dest) as tmp:
        _run(["pdftotext", "-layout", "-enc", "UTF-8", plain, tmp])
    return [dest]


def _web_render(source, dest, timeout=30):
    """Sous-processus python3 -m pdf.web → titre de la page."""
    with atomic_file(dest) as tmp:
        try:
            r = subprocess.run([sys.executable, "-m", "pdf.web", source, str(tmp), str(timeout)],
                               cwd=Path(__file__).resolve().parent.parent, capture_output=True,
                               text=True, timeout=timeout + 15, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            raise OpError(t(f"Délai dépassé ({timeout} s)", f"Timed out ({timeout} s)")) from None
        if r.returncode or not tmp.stat().st_size:
            why = next((l for l in reversed(r.stderr.splitlines()) if l.strip()), "?")
            raise OpError(t(f"Rendu impossible : {why}", f"Rendering failed: {why}"))
    return r.stdout.strip()


def convert(src, password=None):
    src = Path(src)
    ext = src.suffix.lower()
    if ext == ".pdf":
        return to_text(src, password)
    if ext in WEB_EXT:
        dest = out_path(src, "", ".pdf")
        _web_render(str(src), dest)
        return [dest]
    if ext in OFFICE_EXT:
        if not shutil.which("soffice"):
            raise OpError(t("LibreOffice n'est pas installé (sudo pacman -S libreoffice-fresh)",
                            "LibreOffice is not installed (sudo pacman -S libreoffice-fresh)"))
        dest = out_path(src, "", ".pdf")
        with _workdir() as d:   # profil LibreOffice isolé : marche même si LibreOffice est déjà ouvert
            _run(["soffice", f"-env:UserInstallation=file://{d / 'profile'}", "--headless",
                  "--convert-to", "pdf", "--outdir", d / "out", src], timeout=120)
            produced = next((d / "out").glob("*.pdf"), None)
            if not produced:
                raise OpError(t(f"LibreOffice n'a pas converti {src.name}", f"LibreOffice could not convert {src.name}"))
            with atomic_file(dest) as tmp:
                shutil.copyfile(produced, tmp)
        return [dest]
    raise OpError(t(f"Format non pris en charge : {src.name}", f"Unsupported format: {src.name}"))


def _safe_name(title, fallback):
    name = re.sub(r"[\x00-\x1f/\\:*?\"<>|]+", " ", title or "").strip(" .")
    return (re.sub(r"\s+", " ", name)[:120] or fallback)


def webpage(source, directory=None):
    source = source.strip()
    directory = Path(directory or Path.home() / "Downloads")
    directory.mkdir(parents=True, exist_ok=True)
    tmp_dest = directory / f".desk-pdf-web-{os.getpid()}.pdf"
    try:
        title = _web_render(source, tmp_dest)
        fallback = re.sub(r"^\w+://", "", source).split("/")[0] or "page"
        dest = out_path(Path(_safe_name(title, fallback) + ".pdf"), "", ".pdf", directory)
        os.replace(tmp_dest, dest)
    finally:
        tmp_dest.unlink(missing_ok=True)
    return [dest]
