"""Noms de sortie (à côté de l'original, jamais d'écrasement) et écriture atomique."""
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path


def unique(p):
    """p, sinon p-2, p-3… (fichier ou dossier)."""
    p = Path(p)
    if not p.exists():
        return p
    stem, ext = (p.stem, p.suffix) if p.suffix and not p.is_dir() else (p.name, "")
    i = 2
    while (c := p.with_name(f"{stem}-{i}{ext}")).exists():
        i += 1
    return c


def out_path(src, suffix, ext=".pdf", directory=None):
    src = Path(src)
    name = f"{src.stem}-{suffix}" if suffix else src.stem
    return unique(Path(directory or src.parent) / f"{name}{ext}")


def out_dir(src, suffix):
    src = Path(src)
    return unique(src.parent / f"{src.stem}-{suffix}")


@contextmanager
def atomic_file(dest):
    """Fournit un fichier temporaire du même dossier ; renommé en dest si tout va bien."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{dest.name}.tmp-", dir=dest.parent)
    os.close(fd)
    tmp = Path(tmp)
    try:
        yield tmp
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)


@contextmanager
def atomic_dir(dest):
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f".{dest.name}.tmp-", dir=dest.parent))
    try:
        yield tmp
        os.replace(tmp, dest)
    finally:
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
