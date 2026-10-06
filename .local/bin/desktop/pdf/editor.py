"""Éditeur (Edit PDF / Sign PDF) : pages en défilement continu, objets posés par-dessus.

Scène en points PDF (1 unité = 1 pt), pages empilées verticalement ; seules les pages
visibles sont rendues (cache limité). Les objets restent modifiables jusqu'à
l'enregistrement, qui passe par annots.apply (edit : annotations standard, case
« Aplatir » ; sign : tout est aplati).
"""
import datetime
from collections import OrderedDict
from pathlib import Path

import pymupdf as fitz
from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import (QAction, QActionGroup, QBrush, QColor, QFont, QFontMetricsF, QImage, QKeySequence,
                         QPainter, QPainterPath, QPainterPathStroker, QPen, QPixmap, QPolygonF, QShortcut,
                         QTransform)
from PyQt6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QFileDialog, QFormLayout, QGraphicsItem,
                             QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene, QGraphicsView, QHBoxLayout,
                             QInputDialog, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton, QScrollArea,
                             QSpinBox, QToolBar, QVBoxLayout, QWidget)

from . import annots, ops
from .errors import OpError
from .history import History
from .i18n import LANG, t
from .naming import out_path
from .pages import parse_ranges
from .qtutil import error, icon, notify_done, run_with_password

GAP = 16                  # espace entre les pages (pt)
CACHE = 10                # pages rendues gardées en mémoire
QFONTS = {"helv": "Liberation Sans", "tiro": "Liberation Serif", "cour": "Liberation Mono"}
HANDLE = 8


def qcolor(c):
    return QColor.fromRgbF(*c) if c is not None else QColor(0, 0, 0, 0)


def rgb(qc):
    return (round(qc.redF(), 4), round(qc.greenF(), 4), round(qc.blueF(), 4))


# ── Objets posés sur les pages ───────────────────────────────
class Obj:
    """Mixin commun : sérialisation (historique) et conversion vers annots.*Item."""
    kind = ""

    def setup(self):
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setZValue(10)

    def state(self):
        raise NotImplementedError


class BoxObj(QGraphicsItem, Obj):
    """Objet rectangulaire redimensionnable (poignée en bas à droite)."""

    def __init__(self, kind, rect, **data):
        super().__init__()
        self.kind, self.w, self.h = kind, max(4.0, rect.width()), max(4.0, rect.height())
        self.props = data
        self.setPos(rect.topLeft())
        self.setup()
        self.resizing = False
        self.pix = QPixmap()
        if data.get("png"):
            self.pix.loadFromData(data["png"])

    def boundingRect(self):
        return QRectF(-2, -2, self.w + HANDLE + 4, self.h + HANDLE + 4)

    def rect(self):
        return QRectF(0, 0, self.w, self.h)

    def paint(self, p, _opt, _w=None):
        r, d = self.rect(), self.props
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        match self.kind:
            case "text":
                p.setPen(qcolor(d["color"]))
                f = QFont(QFONTS.get(d["font"], "Liberation Sans"))
                f.setPixelSize(max(1, round(d["size"])))
                p.setFont(f)
                p.drawText(r.adjusted(2, 1, -2, -1), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, d["text"])
            case "rect" | "ellipse":
                p.setPen(QPen(qcolor(d["color"]), d["width"]))
                p.setBrush(Qt.BrushStyle.NoBrush)
                (p.drawEllipse if self.kind == "ellipse" else p.drawRect)(r)
            case "highlight":
                c = qcolor(d["color"])
                c.setAlphaF(0.4)
                p.fillRect(r, c)
            case "whiteout":
                p.fillRect(r, QColor("white"))
                p.setPen(QPen(QColor(120, 120, 120), 0.8, Qt.PenStyle.DashLine))
                p.drawRect(r)
            case "redact":
                p.fillRect(r, QColor("black"))
            case "image" | "signature":
                p.drawPixmap(r, self.pix, QRectF(self.pix.rect()))
        if self.isSelected():
            p.setPen(QPen(QColor("#ff4fa3"), 1, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(r)
            p.fillRect(QRectF(self.w - HANDLE / 2, self.h - HANDLE / 2, HANDLE, HANDLE), QColor("#ff4fa3"))

    def _on_handle(self, pos):
        return self.isSelected() and abs(pos.x() - self.w) <= HANDLE and abs(pos.y() - self.h) <= HANDLE

    def hoverMoveEvent(self, e):
        self.setCursor(Qt.CursorShape.SizeFDiagCursor if self._on_handle(e.pos()) else Qt.CursorShape.SizeAllCursor)

    def mousePressEvent(self, e):
        if self._on_handle(e.pos()):
            self.resizing = True
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self.resizing:
            self.prepareGeometryChange()
            w, h = max(6.0, e.pos().x()), max(6.0, e.pos().y())
            if self.kind in ("image", "signature") and not self.pix.isNull():
                h = w * self.pix.height() / max(1, self.pix.width())   # proportions conservées
            self.w, self.h = w, h
            self.update()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self.resizing = False
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        if self.kind == "text" and self.scene() and hasattr(self.scene(), "editor"):
            self.scene().editor.edit_text(self)
            return
        super().mouseDoubleClickEvent(e)

    def fit_text(self):
        """Ajuste la taille au texte (texte : pas de retour à la ligne automatique)."""
        d = self.props
        f = QFont(QFONTS.get(d["font"], "Liberation Sans"))
        f.setPixelSize(max(1, round(d["size"])))
        fm = QFontMetricsF(f)
        lines = d["text"].split("\n") or [""]
        self.prepareGeometryChange()
        self.w = max(20.0, max(fm.horizontalAdvance(l) for l in lines) + 10)
        self.h = fm.lineSpacing() * len(lines) + 6
        self.update()

    def state(self):
        return {"kind": self.kind, "x": self.pos().x(), "y": self.pos().y(), "w": self.w, "h": self.h, **self.props}


class LineObj(QGraphicsItem, Obj):
    def __init__(self, kind, p1, p2, **data):
        super().__init__()
        self.kind, self.props = kind, data
        self.setPos(p1)
        self.d = p2 - p1
        self.setup()

    def boundingRect(self):
        m = 8 + self.props["width"]
        return QRectF(QPointF(0, 0), self.d).normalized().adjusted(-m, -m, m, m)

    def shape(self):
        path = QPainterPath(QPointF(0, 0))
        path.lineTo(self.d)
        st = QPainterPathStroker()
        st.setWidth(10)
        return st.createStroke(path)

    def paint(self, p, _opt, _w=None):
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = qcolor(self.props["color"])
        pen = QPen(c, self.props["width"], Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        if self.isSelected():
            p.setPen(QPen(QColor("#ff4fa3"), self.props["width"] + 4))
            p.setOpacity(0.35)
            p.drawLine(QPointF(0, 0), self.d)
            p.setOpacity(1)
        p.setPen(pen)
        p.drawLine(QPointF(0, 0), self.d)
        if self.kind == "arrow":
            import math
            ang = math.atan2(self.d.y(), self.d.x())
            size = 6 + 2 * self.props["width"]
            a1 = self.d - QPointF(math.cos(ang - 0.45) * size, math.sin(ang - 0.45) * size)
            a2 = self.d - QPointF(math.cos(ang + 0.45) * size, math.sin(ang + 0.45) * size)
            p.drawPolyline(QPolygonF([a1, self.d, a2]))

    def state(self):
        return {"kind": self.kind, "x": self.pos().x(), "y": self.pos().y(), "dx": self.d.x(), "dy": self.d.y(), **self.props}


class InkObj(QGraphicsItem, Obj):
    kind = "ink"

    def __init__(self, points, **data):
        super().__init__()
        self.props = data
        origin = points[0]
        self.setPos(origin)
        self.pts = [p - origin for p in points]
        self.setup()

    def path(self):
        path = QPainterPath(self.pts[0])
        for q in self.pts[1:]:
            path.lineTo(q)
        return path

    def boundingRect(self):
        m = 4 + self.props["width"]
        return self.path().boundingRect().adjusted(-m, -m, m, m)

    def paint(self, p, _opt, _w=None):
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.isSelected():
            p.setPen(QPen(QColor("#ff4fa3"), self.props["width"] + 4))
            p.setOpacity(0.35)
            p.drawPath(self.path())
            p.setOpacity(1)
        p.setPen(QPen(qcolor(self.props["color"]), self.props["width"], Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(self.path())

    def state(self):
        return {"kind": "ink", "x": self.pos().x(), "y": self.pos().y(),
                "pts": [(q.x(), q.y()) for q in self.pts], **self.props}


def obj_from_state(s):
    s = dict(s)
    kind, x, y = s.pop("kind"), s.pop("x"), s.pop("y")
    if kind in ("line", "arrow"):
        dx, dy = s.pop("dx"), s.pop("dy")
        return LineObj(kind, QPointF(x, y), QPointF(x + dx, y + dy), **s)
    if kind == "ink":
        pts = [QPointF(x + a, y + b) for a, b in s.pop("pts")]
        return InkObj(pts, **s)
    w, h = s.pop("w"), s.pop("h")
    return BoxObj(kind, QRectF(x, y, w, h), **s)


# ── Vue ──────────────────────────────────────────────────────
class EditorView(QGraphicsView):
    def __init__(self, editor):
        super().__init__(editor.scene)
        self.editor = editor
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.setBackgroundBrush(QColor(40, 40, 48))
        self.start = None
        self.temp = None
        self.points = []

    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.editor.zoom_by(1.15 if e.angleDelta().y() > 0 else 1 / 1.15)
            return
        super().wheelEvent(e)

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self.editor.schedule_render()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if not self.editor.user_zoom:
            self.editor.fit_width()
        self.editor.schedule_render()

    def mousePressEvent(self, e):
        tool = self.editor.tool
        if tool == "select" or e.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(e)
            return
        pos = self.mapToScene(e.position().toPoint())
        if self.editor.page_at(pos) is None:
            return
        self.start = pos
        st = self.editor.style_data()
        if tool in ("rect", "ellipse", "highlight", "whiteout", "redact"):
            self.temp = QGraphicsRectItem(QRectF(pos, pos))
            self.temp.setPen(QPen(QColor("#ff4fa3"), 1, Qt.PenStyle.DashLine))
            self.temp.setZValue(20)
            self.scene().addItem(self.temp)
        elif tool in ("line", "arrow"):
            self.temp = LineObj(tool, pos, pos + QPointF(0.1, 0.1), color=st["color"], width=st["width"])
            self.scene().addItem(self.temp)
        elif tool == "pen":
            self.points = [pos]
            self.temp = InkObj([pos, pos], color=st["color"], width=st["width"])
            self.scene().addItem(self.temp)

    def mouseMoveEvent(self, e):
        if self.start is None or self.temp is None:
            super().mouseMoveEvent(e)
            return
        pos = self.mapToScene(e.position().toPoint())
        tool = self.editor.tool
        if isinstance(self.temp, QGraphicsRectItem):
            self.temp.setRect(QRectF(self.start, pos).normalized())
        elif tool in ("line", "arrow"):
            self.temp.prepareGeometryChange()
            self.temp.d = pos - self.start
            self.temp.update()
        elif tool == "pen":
            self.points.append(pos)
            self.temp.prepareGeometryChange()
            self.temp.pts = [q - self.points[0] for q in self.points]
            self.temp.update()

    def mouseReleaseEvent(self, e):
        tool = self.editor.tool
        if tool == "select" or e.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(e)
            self.editor.maybe_record()
            return
        pos = self.mapToScene(e.position().toPoint())
        start, temp = self.start, self.temp
        self.start, self.temp = None, None
        if start is None:
            return
        if temp is not None:
            self.scene().removeItem(temp)
        self.editor.create(tool, start, pos, self.points)
        self.points = []


# ── Page de l'éditeur ────────────────────────────────────────
class EditorPage(QWidget):
    def __init__(self, path, mode="edit"):
        super().__init__()
        self.path, self.mode = Path(path).resolve(), mode
        self.password, self.saved = None, None
        self.sig_png = None
        doc = run_with_password(self, self._open)
        if doc is None:
            raise OpError(t("Ouverture annulée", "Opening cancelled"))
        self.doc = doc
        self.scene = QGraphicsScene(self)
        self.scene.editor = self
        self.slots = []                 # (top, largeur, hauteur) par page, visuel
        self.page_items = {}            # index → QGraphicsPixmapItem rendu
        self.cache = OrderedDict()
        self.zoom = 1.0
        self.user_zoom = False       # tant que False : la page suit la largeur de la vue
        self.tool = "select"
        self.color = (0.1, 0.2, 0.6) if mode == "sign" else (0.9, 0.1, 0.2)
        self.text_color = (0.05, 0.05, 0.1)
        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.setInterval(30)
        self.render_timer.timeout.connect(self.render_visible)

        self.build_ui()
        self.layout_pages()
        self.form_initial = {}
        self.build_form()
        self.history = History(self.items_state(), self.history_changed)
        self.history_changed()
        QTimer.singleShot(0, lambda: self.fit_width())

    def _open(self, password=None):
        doc = ops.open_doc(self.path, password)
        self.password = password
        return doc

    def shutdown(self):
        self.render_timer.stop()

    # ── interface ──
    def build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 8)
        tb = QToolBar()
        tb.setIconSize(tb.iconSize() * 0.9)
        self.actions = QActionGroup(self)
        self.actions.setExclusive(True)
        tools_edit = [("select", "edit-select", t("Sélection / déplacer (V)", "Select / move (V)"), "V"),
                      ("text", "insert-text", t("Texte (T)", "Text (T)"), "T"),
                      ("highlight", "draw-highlight", t("Surligner (H)", "Highlight (H)"), "H"),
                      ("rect", "draw-rectangle", t("Rectangle (R)", "Rectangle (R)"), "R"),
                      ("ellipse", "draw-ellipse", t("Ellipse (E)", "Ellipse (E)"), "E"),
                      ("line", "draw-line", t("Ligne (L)", "Line (L)"), "L"),
                      ("arrow", "draw-arrow", t("Flèche (A)", "Arrow (A)"), "A"),
                      ("pen", "draw-freehand", t("Stylo (P)", "Pen (P)"), "P"),
                      ("image", "insert-image", t("Image (I)", "Image (I)"), "I"),
                      ("whiteout", "draw-eraser", t("Masquer en blanc (W)", "White-out (W)"), "W"),
                      ("redact", "view-private", t("Caviarder : supprime le contenu (X)", "Redact: removes content (X)"), "X")]
        tools_sign = [tools_edit[0], tools_edit[1], tools_edit[7]]
        for key, ic, tip, sc in (tools_sign if self.mode == "sign" else tools_edit):
            a = QAction(icon(ic, "draw-freehand"), tip, self)
            a.setCheckable(True)
            a.setShortcut(QKeySequence(sc))
            a.setData(key)
            a.triggered.connect(lambda _=False, k=key: self.set_tool(k))
            self.actions.addAction(a)
            tb.addAction(a)
        self.actions.actions()[0].setChecked(True)
        tb.addSeparator()
        for ic, tip, fn in (("zoom-out", t("Zoom − (Ctrl+molette)", "Zoom − (Ctrl+wheel)"), lambda: self.zoom_by(1 / 1.2)),
                            ("zoom-in", t("Zoom +", "Zoom +"), lambda: self.zoom_by(1.2)),
                            ("zoom-fit-width", t("Largeur de la fenêtre (Ctrl+0)", "Fit width (Ctrl+0)"), lambda: self.fit_width(True))):
            a = QAction(icon(ic), tip, self)
            a.triggered.connect(fn)
            tb.addAction(a)
        tb.addSeparator()
        self.undo_act = QAction(icon("edit-undo"), t("Annuler (Ctrl+Z)", "Undo (Ctrl+Z)"), self)
        self.undo_act.triggered.connect(self.undo)
        self.redo_act = QAction(icon("edit-redo"), t("Rétablir (Ctrl+Maj+Z)", "Redo (Ctrl+Shift+Z)"), self)
        self.redo_act.triggered.connect(self.redo)
        del_act = QAction(icon("edit-delete"), t("Supprimer l'objet (Suppr)", "Delete object (Del)"), self)
        del_act.triggered.connect(self.delete_selected)
        for a in (self.undo_act, self.redo_act, del_act):
            tb.addAction(a)
        lay.addWidget(tb)

        split = QHBoxLayout()
        split.setSpacing(6)
        self.pages_list = QListWidget()
        self.pages_list.setFixedWidth(52)
        self.pages_list.setToolTip(t("Aller à la page", "Go to page"))
        for i in range(len(self.doc)):
            self.pages_list.addItem(f"  {i + 1}")
        self.pages_list.currentRowChanged.connect(self.goto_page)
        split.addWidget(self.pages_list)
        self.view = EditorView(self)
        split.addWidget(self.view, 1)

        side = QWidget()
        sl = QVBoxLayout(side)
        sl.setContentsMargins(6, 0, 0, 0)
        st = QLabel(t("Style", "Style"))
        st.setStyleSheet("font-weight: 600")
        sl.addWidget(st)
        form = QFormLayout()
        self.color_btn = QPushButton()
        self.color_btn.clicked.connect(self.pick_color)
        form.addRow(t("Couleur", "Color"), self.color_btn)
        self.font_box = QComboBox()
        for key, name in (("helv", "Helvetica"), ("tiro", "Times"), ("cour", "Courier")):
            self.font_box.addItem(name, key)
        self.font_box.currentIndexChanged.connect(self.style_changed)
        form.addRow(t("Police", "Font"), self.font_box)
        self.size_box = QSpinBox()
        self.size_box.setRange(5, 96)
        self.size_box.setValue(12)
        self.size_box.valueChanged.connect(self.style_changed)
        form.addRow(t("Taille du texte", "Text size"), self.size_box)
        self.width_box = QSpinBox()
        self.width_box.setRange(1, 20)
        self.width_box.setValue(2)
        self.width_box.valueChanged.connect(self.style_changed)
        form.addRow(t("Épaisseur", "Line width"), self.width_box)
        sl.addLayout(form)
        self.update_color_btn()

        if self.mode == "sign":
            from .signature import SignaturePanel
            self.sig_panel = SignaturePanel()
            self.sig_panel.chosen.connect(self.choose_signature)
            sl.addWidget(self.sig_panel, 2)
            row = QHBoxLayout()
            for text_, fn in ((t("Date", "Date"), self.stamp_date),
                              (t("Lu et approuvé", "Read and approved"), self.stamp_approved)):
                b = QPushButton(text_)
                b.clicked.connect(fn)
                row.addWidget(b)
            sl.addLayout(row)
            dup = QPushButton(icon("edit-copy"), t("Dupliquer sur d'autres pages…", "Duplicate on other pages…"))
            dup.setToolTip(t("Copie l'objet sélectionné (ex. paraphe) à la même place sur les pages choisies",
                             "Copies the selected object (e.g. initials) to the same spot on the chosen pages"))
            dup.clicked.connect(self.duplicate_selected)
            sl.addWidget(dup)

        self.form_box = QWidget()
        self.form_layout = QFormLayout(self.form_box)
        self.form_title = QLabel(t("Formulaire", "Form"))
        self.form_title.setStyleSheet("font-weight: 600")
        sl.addWidget(self.form_title)
        scroll = QScrollArea()
        scroll.setWidget(self.form_box)
        scroll.setWidgetResizable(True)
        self.form_scroll = scroll
        sl.addWidget(scroll, 1)
        sl.addStretch(0)

        self.flatten = QCheckBox(t("Aplatir", "Flatten"))
        self.flatten.setToolTip(t("Tout incruster dans la page (plus modifiable ensuite)",
                                  "Burn everything into the page (no longer editable)"))
        if self.mode == "sign":
            self.flatten.setChecked(True)
            self.flatten.setEnabled(False)
            self.flatten.setToolTip(t("Toujours aplati pour une signature", "Always flattened when signing"))
        sl.addWidget(self.flatten)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setEnabled(False)
        sl.addWidget(self.status)
        row = QHBoxLayout()
        save_as = QPushButton(icon("document-save-as"), "")
        save_as.setToolTip(t("Enregistrer sous…", "Save as…"))
        save_as.clicked.connect(lambda: self.save(ask=True))
        row.addWidget(save_as)
        save = QPushButton(icon("document-save"), t("Enregistrer", "Save"))
        save.setToolTip("Ctrl+S")
        save.setDefault(True)
        save.clicked.connect(lambda: self.save())
        row.addWidget(save, 1)
        sl.addLayout(row)
        if self.mode == "sign":
            ok = QPushButton(icon("application-certificate"), t("Signature certifiée → Okular", "Certified signature → Okular"))
            ok.setToolTip(t("Enregistre, puis ouvre le PDF signé dans Okular (Outils → Signer numériquement)",
                            "Saves, then opens the signed PDF in Okular (Tools → Digitally sign)"))
            ok.clicked.connect(self.open_okular)
            sl.addWidget(ok)
        side.setFixedWidth(270)
        split.addWidget(side)
        lay.addLayout(split, 1)

        for seq, fn in (("Ctrl+Z", self.undo), ("Ctrl+Shift+Z", self.redo), ("Ctrl+Y", self.redo),
                        ("Delete", self.delete_selected), ("Ctrl+S", self.save), ("Escape", lambda: self.set_tool("select")),
                        ("Ctrl++", lambda: self.zoom_by(1.2)), ("Ctrl+=", lambda: self.zoom_by(1.2)),
                        ("Ctrl+-", lambda: self.zoom_by(1 / 1.2)), ("Ctrl+0", lambda: self.fit_width(True))):
            QShortcut(QKeySequence(seq), self, fn)

    # ── pages ──
    def layout_pages(self):
        y = 0.0
        for i, page in enumerate(self.doc):
            w, h = page.rect.width, page.rect.height
            bg = QGraphicsRectItem(0, y, w, h)
            bg.setBrush(QBrush(QColor("white")))
            bg.setPen(QPen(Qt.PenStyle.NoPen))
            bg.setZValue(-20)
            self.scene.addItem(bg)
            self.slots.append((y, w, h))
            y += h + GAP
        maxw = max(s[1] for s in self.slots)
        self.scene.setSceneRect(-GAP, -GAP, maxw + 2 * GAP, y + GAP)

    def page_at(self, pos):
        for i, (top, w, h) in enumerate(self.slots):
            if top - GAP / 2 <= pos.y() <= top + h + GAP / 2:
                return i if -GAP <= pos.x() <= w + GAP else None
        return None

    def page_of(self, item):
        c = item.sceneBoundingRect().center()
        best, dist = 0, float("inf")
        for i, (top, w, h) in enumerate(self.slots):
            d = 0 if top <= c.y() <= top + h else min(abs(c.y() - top), abs(c.y() - top - h))
            if d < dist:
                best, dist = i, d
        return best

    def schedule_render(self):
        self.render_timer.start()

    def render_visible(self):
        vis = self.view.mapToScene(self.view.viewport().rect()).boundingRect()
        res = max(1.5, min(6.0, self.zoom * self.view.devicePixelRatioF() * 1.1))
        for i, (top, w, h) in enumerate(self.slots):
            if top + h < vis.top() - 200 or top > vis.bottom() + 200:
                continue
            key = self.cache.get(i)
            if key is not None and abs(key - res) / res < 0.25:
                self.cache.move_to_end(i)
                continue
            page = self.doc[i]
            pix = page.get_pixmap(matrix=fitz.Matrix(res, res), alpha=False, annots=True)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
            item = self.page_items.get(i)
            if item is None:
                item = QGraphicsPixmapItem()
                item.setZValue(-10)
                item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
                self.scene.addItem(item)
                self.page_items[i] = item
            item.setPixmap(QPixmap.fromImage(img))
            item.setScale(1 / res)
            item.setPos(0, top)
            self.cache[i] = res
            self.cache.move_to_end(i)
        while len(self.cache) > CACHE:
            old, _ = self.cache.popitem(last=False)
            item = self.page_items.pop(old, None)
            if item is not None:
                self.scene.removeItem(item)
        top_page = self.page_at(QPointF(10, vis.top() + 40))
        if top_page is not None and self.pages_list.currentRow() != top_page:
            self.pages_list.blockSignals(True)
            self.pages_list.setCurrentRow(top_page)
            self.pages_list.blockSignals(False)

    def goto_page(self, i):
        if 0 <= i < len(self.slots):
            top = self.slots[i][0]
            self.view.verticalScrollBar().setValue(int(self.view.mapFromScene(QPointF(0, top - 8)).y()
                                                       + self.view.verticalScrollBar().value()))

    def zoom_by(self, f):
        self.user_zoom = True
        self.set_zoom(self.zoom * f)

    def set_zoom(self, z):
        z = max(0.2, min(6.0, z))
        self.view.setTransform(QTransform.fromScale(z, z))
        self.zoom = z
        self.schedule_render()

    def fit_width(self, user=False):
        if user:
            self.user_zoom = False
        maxw = max(s[1] for s in self.slots) + 2 * GAP
        avail = self.view.viewport().width() - 4
        if avail > 50:
            self.set_zoom(avail / maxw)

    def current_page(self):
        vis = self.view.mapToScene(self.view.viewport().rect()).boundingRect()
        return self.page_at(QPointF(10, vis.center().y())) or 0

    # ── outils et style ──
    def set_tool(self, key):
        self.tool = key
        for a in self.actions.actions():
            a.setChecked(a.data() == key)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag if key == "select" else QGraphicsView.DragMode.NoDrag)
        self.view.viewport().setCursor(Qt.CursorShape.ArrowCursor if key == "select" else Qt.CursorShape.CrossCursor)

    def style_data(self):
        return {"color": self.color, "width": float(self.width_box.value())}

    def update_color_btn(self):
        c = qcolor(self.color).name()
        self.color_btn.setStyleSheet(f"background: {c}; min-height: 20px; border-radius: 4px")

    def pick_color(self):
        c = QColorDialog.getColor(qcolor(self.color), self, t("Couleur", "Color"))
        if c.isValid():
            self.color = rgb(c)
            self.update_color_btn()
            self.style_changed()

    def style_changed(self):
        """Applique le style aux objets sélectionnés."""
        changed = False
        for it in self.scene.selectedItems():
            if not isinstance(it, Obj):
                continue
            d = it.props
            if getattr(it, "kind", "") == "text":
                d.update(color=self.color, font=self.font_box.currentData(), size=float(self.size_box.value()))
                it.fit_text()
            elif "width" in d:
                d.update(color=self.color, width=float(self.width_box.value()))
                it.prepareGeometryChange()
            elif getattr(it, "kind", "") == "highlight":
                d.update(color=self.color)
            else:
                continue
            it.update()
            changed = True
        if changed:
            self.record()

    # ── création d'objets ──
    def create(self, tool, start, end, points):
        page = self.page_at(start)
        if page is None:
            return
        st = self.style_data()
        rect = QRectF(start, end).normalized()
        obj = None
        if tool in ("rect", "ellipse"):
            if rect.width() < 4 or rect.height() < 4:
                return
            obj = BoxObj(tool, rect, color=st["color"], width=st["width"])
        elif tool == "highlight":
            if rect.width() < 4 or rect.height() < 3:
                return
            obj = BoxObj("highlight", rect, color=(1, 0.9, 0))
        elif tool in ("whiteout", "redact"):
            if rect.width() < 3 or rect.height() < 3:
                return
            obj = BoxObj(tool, rect)
        elif tool in ("line", "arrow"):
            if (end - start).manhattanLength() < 4:
                return
            obj = LineObj(tool, start, end, color=st["color"], width=st["width"])
        elif tool == "pen":
            if len(points) < 2:
                return
            obj = InkObj(points, color=st["color"], width=st["width"])
        elif tool == "text":
            text, ok = QInputDialog.getMultiLineText(self, t("Texte", "Text"), t("Texte à ajouter :", "Text to add:"))
            if not ok or not text.strip():
                return
            obj = self.text_obj(start, text)
        elif tool == "image":
            f, _ = QFileDialog.getOpenFileName(self, t("Image", "Image"), str(Path.home()),
                                               "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
            if not f:
                return
            obj = self.image_obj("image", Path(f).read_bytes() if f.lower().endswith((".png", ".jpg", ".jpeg"))
                                 else self._to_png(f), start, 200)
        elif tool == "signature" and self.sig_png:
            obj = self.image_obj("signature", self.sig_png, start, 160)
        if obj is None:
            return
        self.scene.addItem(obj)
        self.scene.clearSelection()
        obj.setSelected(True)
        if tool in ("text", "image", "signature"):
            self.set_tool("select")
        self.record()

    def _to_png(self, f):
        from .signature import png_bytes
        return png_bytes(QImage(f))

    def text_obj(self, pos, text):
        obj = BoxObj("text", QRectF(pos, pos + QPointF(10, 10)), text=text, font=self.font_box.currentData(),
                     size=float(self.size_box.value()), color=self.text_color if self.mode == "sign" else self.color)
        obj.fit_text()
        return obj

    def image_obj(self, kind, png, pos, width):
        pm = QPixmap()
        pm.loadFromData(png)
        if pm.isNull():
            error(self, t("Image illisible", "Unreadable image"))
            return None
        h = width * pm.height() / max(1, pm.width())
        return BoxObj(kind, QRectF(pos.x(), pos.y() - h / 2, width, h), png=png)

    def edit_text(self, obj):
        text, ok = QInputDialog.getMultiLineText(self, t("Texte", "Text"), t("Modifier le texte :", "Edit text:"), obj.props["text"])
        if ok and text.strip():
            obj.props["text"] = text
            obj.fit_text()
            self.record()

    def place_center(self, obj):
        i = self.current_page()
        top, w, h = self.slots[i]
        obj.setPos(max(10, w / 2 - obj.w / 2), top + h * 0.75)
        self.scene.addItem(obj)
        self.scene.clearSelection()
        obj.setSelected(True)
        self.record()

    def stamp_date(self):
        d = datetime.date.today()
        self.place_center(self.text_obj(QPointF(0, 0), d.strftime("%d/%m/%Y") if LANG == "fr" else d.strftime("%B %d, %Y")))

    def stamp_approved(self):
        self.place_center(self.text_obj(QPointF(0, 0), t("Lu et approuvé", "Read and approved")))

    def choose_signature(self, path):
        self.sig_png = Path(path).read_bytes()
        self.tool = "signature"
        for a in self.actions.actions():
            a.setChecked(False)
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.view.viewport().setCursor(Qt.CursorShape.CrossCursor)
        self.status.setText(t("Clique sur la page pour poser la signature", "Click on the page to place the signature"))

    def duplicate_selected(self):
        sel = [it for it in self.scene.selectedItems() if isinstance(it, Obj)]
        if not sel:
            error(self, t("Sélectionne d'abord un objet (ex. ta signature)", "Select an object first (e.g. your signature)"))
            return
        spec, ok = QInputDialog.getText(self, t("Dupliquer", "Duplicate"),
                                        t("Pages (ex. 1-3,5 ; vide = toutes) :", "Pages (e.g. 1-3,5; empty = all):"))
        if not ok:
            return
        try:
            pages = parse_ranges(spec, len(self.slots))
        except OpError as e:
            error(self, e)
            return
        for it in sel:
            src = self.page_of(it)
            for p in pages:
                if p == src:
                    continue
                s = it.state()
                s["y"] += self.slots[p][0] - self.slots[src][0]
                self.scene.addItem(obj_from_state(s))
        self.record()

    def delete_selected(self):
        sel = [it for it in self.scene.selectedItems() if isinstance(it, Obj)]
        for it in sel:
            self.scene.removeItem(it)
        if sel:
            self.record()

    # ── historique ──
    def objects(self):
        return [it for it in self.scene.items(Qt.SortOrder.AscendingOrder) if isinstance(it, Obj)]

    def items_state(self):
        return [o.state() for o in self.objects()]

    def restore(self, states):
        for o in self.objects():
            self.scene.removeItem(o)
        for s in states:
            self.scene.addItem(obj_from_state(s))

    def record(self):
        self.history.push(self.items_state())

    def maybe_record(self):
        if self.items_state() != self.history.current():
            self.record()

    def undo(self):
        s = self.history.undo()
        if s is not None:
            self.restore(s)

    def redo(self):
        s = self.history.redo()
        if s is not None:
            self.restore(s)

    def history_changed(self):
        self.undo_act.setEnabled(self.history.can_undo())
        self.redo_act.setEnabled(self.history.can_redo())

    @property
    def dirty(self):
        return not self.history.is_clean() or self.form_values() != self.form_initial

    # ── formulaire ──
    def build_form(self):
        try:
            fields = annots.form_fields(self.path, self.password)
        except OpError:
            fields = []
        self.fields = {}
        self.highlight = None
        groups = {}
        for f in fields:
            if f["type"] == "radio":
                groups.setdefault(f["name"], []).append(f)
                continue
            if f["type"] == "text":
                w = QLineEdit(str(f["value"] or ""))
                w.textChanged.connect(self.form_changed)
            elif f["type"] == "checkbox":
                w = QCheckBox()
                w.setChecked(bool(f["value"]))
                w.toggled.connect(self.form_changed)
            else:
                w = QComboBox()
                w.addItems([""] + f["choices"])
                w.setCurrentText(str(f["value"] or ""))
                w.currentIndexChanged.connect(self.form_changed)
            self.fields[f["name"]] = (w, f)
            self.form_layout.addRow(f["name"], w)
            w.installEventFilter(self)
        for name, fs in groups.items():
            w = QComboBox()
            w.addItem("", "Off")
            for f in fs:
                w.addItem(f["choices"][0], f["choices"][0])
                if f["value"] not in ("Off", None, False, ""):
                    w.setCurrentIndex(w.count() - 1)
            w.currentIndexChanged.connect(self.form_changed)
            self.fields[name] = (w, fs[0])
            self.form_layout.addRow(name, w)
            w.installEventFilter(self)
        has = bool(self.fields)
        self.form_title.setVisible(has)
        self.form_scroll.setVisible(has)
        self.form_initial = self.form_values()

    def form_values(self):
        out = {}
        for name, (w, f) in getattr(self, "fields", {}).items():
            if isinstance(w, QLineEdit):
                out[name] = w.text()
            elif isinstance(w, QCheckBox):
                out[name] = w.isChecked()
            elif f["type"] == "radio":
                out[name] = w.currentData()
            else:
                out[name] = w.currentText()
        return out

    def form_changed(self):
        self.status.setText("")

    def eventFilter(self, obj, e):
        from PyQt6.QtCore import QEvent
        if e.type() == QEvent.Type.FocusIn:
            for name, (w, f) in self.fields.items():
                if w is obj:
                    self.show_field(f)
        return False

    def show_field(self, f):
        top = self.slots[f["page"]][0]
        x0, y0, x1, y1 = f["rect"]
        r = QRectF(x0, top + y0, x1 - x0, y1 - y0)
        if self.highlight is not None:
            self.scene.removeItem(self.highlight)
        self.highlight = QGraphicsRectItem(r.adjusted(-3, -3, 3, 3))
        self.highlight.setPen(QPen(QColor("#ff4fa3"), 2))
        self.highlight.setZValue(30)
        self.scene.addItem(self.highlight)
        self.view.ensureVisible(r, 60, 60)

    # ── enregistrement ──
    def to_annots(self):
        out = []
        for o in self.objects():
            p = self.page_of(o)
            top = self.slots[p][0]
            s = o.state()
            x, y = s["x"], s["y"] - top
            d = o.props
            match s["kind"]:
                case "text":
                    out.append(annots.TextItem(p, (x, y, x + s["w"], y + s["h"]), d["text"], d["font"], d["size"], tuple(d["color"])))
                case "rect" | "ellipse":
                    out.append(annots.ShapeItem(p, s["kind"], (x, y, x + s["w"], y + s["h"]), color=tuple(d["color"]), width=d["width"]))
                case "highlight":
                    out.append(annots.HighlightItem(p, (x, y, x + s["w"], y + s["h"]), tuple(d["color"])))
                case "whiteout" | "redact":
                    out.append(annots.MaskItem(p, (x, y, x + s["w"], y + s["h"]), redact=s["kind"] == "redact"))
                case "image":
                    out.append(annots.ImageItem(p, (x, y, x + s["w"], y + s["h"]), d["png"]))
                case "signature":
                    out.append(annots.SignatureItem(p, (x, y, x + s["w"], y + s["h"]), d["png"]))
                case "line" | "arrow":
                    out.append(annots.ShapeItem(p, s["kind"], (0, 0, 0, 0), p1=(x, y), p2=(x + s["dx"], y + s["dy"]),
                                                color=tuple(d["color"]), width=d["width"]))
                case "ink":
                    out.append(annots.InkItem(p, [[(x + a, y + b) for a, b in s["pts"]]], tuple(d["color"]), d["width"]))
        return out

    def save(self, ask=False):
        dest = out_path(self.path, "signed" if self.mode == "sign" else "edited")
        if ask:
            f, _ = QFileDialog.getSaveFileName(self, t("Enregistrer sous", "Save as"), str(dest), "PDF (*.pdf)")
            if not f:
                return None
            dest = Path(f) if f.lower().endswith(".pdf") else Path(f + ".pdf")
            if dest.resolve() == self.path:
                error(self, t("Choisis un autre nom que l'original", "Pick a name other than the original"))
                return None
        items = self.to_annots()
        if any(isinstance(i, annots.MaskItem) and i.redact for i in items):
            if QMessageBox.question(self, t("Caviardage", "Redaction"),
                                    t("Le contenu sous les zones noires sera définitivement supprimé du nouveau fichier. Continuer ?",
                                      "Content under the black areas will be permanently removed from the new file. Continue?")) \
                    != QMessageBox.StandardButton.Yes:
                return None
        values = self.form_values()
        form = {k: v for k, v in values.items() if v != self.form_initial.get(k)}
        try:
            out = annots.apply(self.path, items, dest, form=form, flatten=self.flatten.isChecked(), password=self.password)
        except OpError as e:
            error(self, e)
            return None
        except Exception as e:  # noqa: BLE001
            error(self, t(f"Enregistrement impossible : {e}", f"Cannot save: {e}"))
            return None
        self.saved = out
        self.history.set_clean()
        self.form_initial = values
        self.status.setText(t(f"Enregistré : {out}", f"Saved: {out}"))
        notify_done("sign" if self.mode == "sign" else "edit", [out])
        return out

    def open_okular(self):
        out = self.saved if (self.saved and not self.dirty) else self.save()
        if out:
            import subprocess
            subprocess.Popen(["okular", str(out)], start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def add_files(self, _paths):
        pass
