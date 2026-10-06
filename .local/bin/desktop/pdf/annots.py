"""Éditeur, côté moteur (sans Qt) : objets posés sur les pages → PDF (PyMuPDF).

Coordonnées en points PDF, origine en haut à gauche de la page telle qu'on la voit
(rotation /Rotate déjà appliquée) ; converties ici dans le repère non tourné de la page.
Ordre d'application : champs de formulaire, masques (contenu réellement supprimé),
annotations, images et signatures (insérées dans le contenu), puis aplatissement éventuel.
"""
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf as fitz

from . import ops
from .errors import OpError
from .i18n import t
from .naming import atomic_file

FONTS = {"helv": "Helv", "tiro": "TiRo", "cour": "Cour"}


@dataclass
class TextItem:
    page: int
    rect: tuple
    text: str
    font: str = "helv"
    size: float = 12
    color: tuple = (0, 0, 0)


@dataclass
class ShapeItem:
    page: int
    kind: str                     # rect | ellipse | line | arrow
    rect: tuple
    p1: tuple = None              # line / arrow
    p2: tuple = None
    color: tuple = (0.9, 0.1, 0.2)
    width: float = 1.5
    fill: tuple = None


@dataclass
class HighlightItem:
    page: int
    rect: tuple
    color: tuple = (1, 0.9, 0)


@dataclass
class InkItem:
    page: int
    strokes: list
    color: tuple = (0.1, 0.2, 0.6)
    width: float = 1.5


@dataclass
class ImageItem:
    page: int
    rect: tuple
    png: bytes = field(repr=False, default=b"")


@dataclass
class MaskItem:
    page: int
    rect: tuple
    redact: bool = False          # False : masquage blanc · True : caviardage noir


@dataclass
class SignatureItem:
    page: int
    rect: tuple
    png: bytes = field(repr=False, default=b"")


ITEM_TYPES = (TextItem, ShapeItem, HighlightItem, InkItem, ImageItem, MaskItem, SignatureItem)


# ── Repère ───────────────────────────────────────────────────
def _rect(page, r):
    """Rectangle visuel → repère non tourné de la page."""
    return (fitz.Rect(r) * page.derotation_matrix).normalize()


def _pt(page, p):
    return fitz.Point(p) * page.derotation_matrix


# ── Formulaires ──────────────────────────────────────────────
WIDGET_TYPES = {fitz.PDF_WIDGET_TYPE_TEXT: "text", fitz.PDF_WIDGET_TYPE_CHECKBOX: "checkbox",
                fitz.PDF_WIDGET_TYPE_COMBOBOX: "combo", fitz.PDF_WIDGET_TYPE_LISTBOX: "list",
                fitz.PDF_WIDGET_TYPE_RADIOBUTTON: "radio"}


def form_fields(src, password=None):
    """Champs remplissables : [{name, type, value, choices, page, rect (visuel)}]."""
    out, seen = [], set()
    with ops.open_doc(src, password) as doc:
        for page in doc:
            for w in page.widgets() or []:
                kind = WIDGET_TYPES.get(w.field_type)
                if not kind or not w.field_name:
                    continue
                key = (w.field_name, kind)
                if key in seen and kind != "radio":
                    continue
                seen.add(key)
                value = w.field_value
                if kind == "checkbox":
                    value = value not in (False, "Off", "", None)
                vis = fitz.Rect(w.rect) * page.rotation_matrix
                out.append({"name": w.field_name, "type": kind, "value": value,
                            "choices": list(w.choice_values or []) if kind in ("combo", "list") else
                            ([w.on_state()] if kind == "radio" else []),
                            "page": page.number, "rect": tuple(vis.normalize())})
    return out


def _fill(doc, form):
    for page in doc:
        for w in page.widgets() or []:
            if w.field_name not in form:
                continue
            v = form[w.field_name]
            if w.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                w.field_value = w.on_state() if v else "Off"
            elif w.field_type == fitz.PDF_WIDGET_TYPE_RADIOBUTTON:
                w.field_value = w.on_state() if v in (True, w.on_state()) else "Off"
            else:
                w.field_value = "" if v is None else str(v)
            w.update()


# ── Application ──────────────────────────────────────────────
def _annot(page, it):
    col = tuple(it.color) if getattr(it, "color", None) is not None else None
    if isinstance(it, TextItem):
        a = page.add_freetext_annot(_rect(page, it.rect), it.text, fontsize=it.size,
                                    fontname=FONTS.get(it.font, "Helv"), text_color=col,
                                    rotate=page.rotation)
        a.update()
    elif isinstance(it, ShapeItem):
        if it.kind in ("line", "arrow"):
            a = page.add_line_annot(_pt(page, it.p1), _pt(page, it.p2))
            if it.kind == "arrow":
                a.set_line_ends(fitz.PDF_ANNOT_LE_NONE, fitz.PDF_ANNOT_LE_OPEN_ARROW)
        elif it.kind == "ellipse":
            a = page.add_circle_annot(_rect(page, it.rect))
        else:
            a = page.add_rect_annot(_rect(page, it.rect))
        a.set_colors(stroke=col, fill=tuple(it.fill) if it.fill else None)
        a.set_border(width=it.width)
        a.update()
    elif isinstance(it, HighlightItem):
        a = page.add_highlight_annot(_rect(page, it.rect).quad)
        a.set_colors(stroke=col)
        a.update()
    elif isinstance(it, InkItem):
        strokes = [[tuple(_pt(page, p)) for p in s] for s in it.strokes if len(s) > 1]
        if strokes:
            a = page.add_ink_annot(strokes)
            a.set_colors(stroke=col)
            a.set_border(width=it.width)
            a.update()
    elif isinstance(it, (ImageItem, SignatureItem)):
        if it.png:
            page.insert_image(fitz.Rect(it.rect) * page.derotation_matrix, stream=it.png,
                              keep_proportion=True, rotate=-page.rotation % 360 if page.rotation else 0)


def apply(src, items, dest, form=None, flatten=False, password=None):
    """Écrit src + objets dans dest (écriture atomique) → dest."""
    dest = Path(dest)
    doc = ops.open_doc(src, password)
    try:
        n = len(doc)
        for it in items:
            if not 0 <= it.page < n:
                raise OpError(t(f"Page {it.page + 1} inexistante", f"Page {it.page + 1} does not exist"))
        if form:
            _fill(doc, form)
        masked = set()
        for it in items:
            if isinstance(it, MaskItem):
                page = doc[it.page]
                page.add_redact_annot(_rect(page, it.rect), fill=(0, 0, 0) if it.redact else (1, 1, 1))
                masked.add(it.page)
        for p in masked:
            doc[p].apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
        for it in items:
            if not isinstance(it, MaskItem):
                _annot(doc[it.page], it)
        if flatten:
            doc.bake(annots=True, widgets=True)
        with atomic_file(dest) as tmp:
            doc.save(tmp, garbage=3, deflate=True)
    finally:
        doc.close()
    return dest
