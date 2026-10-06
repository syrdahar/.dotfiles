"""Signatures : bibliothèque (~/.local/share/desk/pdf/signatures), zone de dessin, import d'image."""
import os
import time
from pathlib import Path

import numpy as np
from PyQt6.QtCore import QBuffer, QIODevice, QPointF, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QImage, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (QButtonGroup, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QListWidget,
                             QListWidgetItem, QPushButton, QRadioButton, QSlider, QVBoxLayout, QWidget)

from .i18n import t
from .qtutil import icon

SIG_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "desk/pdf/signatures"
INK = {"blue": "#1a3d8f", "black": "#111111"}


def library():
    """Signatures enregistrées, les plus récentes d'abord."""
    if not SIG_DIR.is_dir():
        return []
    return sorted(SIG_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)


def save_png(img):
    SIG_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(SIG_DIR, 0o700)
    path = SIG_DIR / f"signature-{time.strftime('%Y%m%d-%H%M%S')}.png"
    k = 2
    while path.exists():
        path = SIG_DIR / f"signature-{time.strftime('%Y%m%d-%H%M%S')}-{k}.png"
        k += 1
    img.save(str(path), "PNG")
    os.chmod(path, 0o600)
    return path


def png_bytes(img):
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


def _to_array(img):
    img = img.convertToFormat(QImage.Format.Format_RGBA8888)
    ptr = img.constBits()
    ptr.setsize(img.sizeInBytes())
    a = np.frombuffer(ptr, np.uint8).reshape(img.height(), img.bytesPerLine() // 4, 4)[:, : img.width()]
    return a.copy()


def _from_array(a):
    a = np.ascontiguousarray(a)
    h, w = a.shape[:2]
    return QImage(a.data, w, h, 4 * w, QImage.Format.Format_RGBA8888).copy()


def crop_alpha(img, margin=4):
    """Recadre sur la zone non transparente (+ marge)."""
    a = _to_array(img)
    ys, xs = np.nonzero(a[:, :, 3] > 8)
    if not len(xs):
        return img
    x0, x1 = max(0, xs.min() - margin), min(a.shape[1], xs.max() + 1 + margin)
    y0, y1 = max(0, ys.min() - margin), min(a.shape[0], ys.max() + 1 + margin)
    return _from_array(a[y0:y1, x0:x1])


def import_image(path, max_side=1600):
    """Photo ou scan d'une signature → fond clair transparent, recadré."""
    img = QImage(str(path))
    if img.isNull():
        raise ValueError(t(f"Image illisible : {Path(path).name}", f"Unreadable image: {Path(path).name}"))
    if max(img.width(), img.height()) > max_side:
        img = img.scaled(max_side, max_side, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    a = _to_array(img).astype(np.float32)
    lum = 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]
    # fond clair → transparent, trait sombre → opaque, transition douce entre 170 et 200
    alpha = np.clip((200 - lum) / 30, 0, 1) * (a[:, :, 3] / 255)
    a[:, :, 3] = alpha * 255
    return crop_alpha(_from_array(a.astype(np.uint8)))


class Pad(QWidget):
    """Zone de dessin : souris ou tablette (épaisseur selon la pression), trait lissé."""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(560, 220)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.strokes = []          # [(QPainterPath, épaisseur)]
        self.points = []
        self.color = QColor(INK["blue"])
        self.pen_width = 3.0
        self.pressure = 1.0
        self.setAttribute(Qt.WidgetAttribute.WA_StaticContents)

    def clear(self):
        self.strokes, self.points = [], []
        self.update()

    def _path(self, pts):
        path = QPainterPath(pts[0])
        if len(pts) < 3:
            for p in pts[1:]:
                path.lineTo(p)
            return path
        for i in range(1, len(pts) - 1):   # courbes quadratiques entre les milieux : trait lisse
            mid = (pts[i] + pts[i + 1]) / 2
            path.quadTo(pts[i], mid)
        path.lineTo(pts[-1])
        return path

    def _press(self, pos):
        self.points = [QPointF(pos)]

    def _move(self, pos):
        if self.points:
            self.points.append(QPointF(pos))
            self.update()

    def _release(self):
        if len(self.points) == 1:
            self.points.append(self.points[0] + QPointF(0.5, 0.5))
        if self.points:
            self.strokes.append((self._path(self.points), self.pen_width * (0.6 + 0.8 * self.pressure)))
        self.points = []
        self.update()

    def mousePressEvent(self, e):
        self.pressure = 1.0
        self._press(e.position())

    def mouseMoveEvent(self, e):
        self._move(e.position())

    def mouseReleaseEvent(self, e):
        self._release()

    def tabletEvent(self, e):
        self.pressure = max(0.1, e.pressure())
        match e.type():
            case e.Type.TabletPress:
                self._press(e.position())
            case e.Type.TabletMove:
                self._move(e.position())
            case e.Type.TabletRelease:
                self._release()
        e.accept()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("white"))
        p.setPen(QPen(QColor(200, 200, 200), 1, Qt.PenStyle.DashLine))
        y = int(self.height() * 0.72)
        p.drawLine(24, y, self.width() - 24, y)
        self._draw(p)

    def _draw(self, p):
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for path, w in self.strokes + ([(self._path(self.points), self.pen_width)] if len(self.points) > 1 else []):
            p.setPen(QPen(self.color, w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawPath(path)

    def image(self, scale=3):
        """Signature en haute définition, fond transparent, recadrée (None si vide)."""
        if not self.strokes:
            return None
        img = QImage(QSize(self.width() * scale, self.height() * scale), QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.scale(scale, scale)
        self._draw(p)
        p.end()
        return crop_alpha(img, margin=6)


class DrawDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("Nouvelle signature", "New signature"))
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(t("Signe dans le cadre (souris ou tablette graphique)",
                               "Sign inside the box (mouse or drawing tablet)")))
        self.pad = Pad()
        lay.addWidget(self.pad, 1)
        row = QHBoxLayout()
        group = QButtonGroup(self)
        for key, label in (("blue", t("Bleu encre", "Ink blue")), ("black", t("Noir", "Black"))):
            rb = QRadioButton(label)
            rb.setChecked(key == "blue")
            rb.toggled.connect(lambda on, k=key: on and self.set_color(k))
            group.addButton(rb)
            row.addWidget(rb)
        row.addSpacing(16)
        row.addWidget(QLabel(t("Épaisseur", "Width")))
        sl = QSlider(Qt.Orientation.Horizontal)
        sl.setRange(10, 80)
        sl.setValue(30)
        sl.setFixedWidth(120)
        sl.valueChanged.connect(lambda v: setattr(self.pad, "pen_width", v / 10))
        row.addWidget(sl)
        row.addStretch()
        clear = QPushButton(icon("edit-clear"), t("Effacer", "Clear"))
        clear.clicked.connect(self.pad.clear)
        row.addWidget(clear)
        lay.addLayout(row)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def set_color(self, key):
        self.pad.color = QColor(INK[key])
        self.pad.update()


class SignaturePanel(QWidget):
    """Liste des signatures ; un clic choisit celle à poser (signal chosen(chemin))."""
    chosen = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        head = QLabel(t("Mes signatures", "My signatures"))
        head.setStyleSheet("font-weight: 600")
        lay.addWidget(head)
        self.list = QListWidget()
        self.list.setIconSize(QSize(180, 64))
        self.list.setSpacing(4)
        self.list.itemClicked.connect(lambda it: self.chosen.emit(it.data(Qt.ItemDataRole.UserRole)))
        lay.addWidget(self.list, 1)
        row = QHBoxLayout()
        for ic, text_, fn in (("draw-freehand", t("Dessiner", "Draw"), self.draw),
                              ("document-import", t("Importer", "Import"), self.import_file),
                              ("edit-delete", "", self.delete)):
            b = QPushButton(icon(ic), text_)
            if not text_:
                b.setToolTip(t("Supprimer la signature sélectionnée", "Delete the selected signature"))
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addLayout(row)
        self.refresh()

    def refresh(self, select=None):
        self.list.clear()
        for p in library():
            pm = QPixmap(str(p))
            canvas = QPixmap(180, 64)
            canvas.fill(QColor("white"))
            painter = QPainter(canvas)
            s = pm.scaled(172, 58, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(QRect((180 - s.width()) // 2, (64 - s.height()) // 2, s.width(), s.height()), s)
            painter.end()
            it = QListWidgetItem(QIcon(canvas), "")
            it.setData(Qt.ItemDataRole.UserRole, str(p))
            it.setToolTip(p.name)
            self.list.addItem(it)
            if select and str(p) == str(select):
                self.list.setCurrentItem(it)
        if not self.list.count():
            it = QListWidgetItem(t("Aucune signature :\n« Dessiner » ou « Importer »",
                                   "No signature yet:\n“Draw” or “Import”"))
            it.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(it)

    def draw(self):
        dlg = DrawDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            img = dlg.pad.image()
            if img is not None:
                p = save_png(img)
                self.refresh(select=p)
                self.chosen.emit(str(p))

    def import_file(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        f, _ = QFileDialog.getOpenFileName(self, t("Importer une signature (photo, scan)", "Import a signature (photo, scan)"),
                                           str(Path.home()), "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)")
        if not f:
            return
        try:
            p = save_png(import_image(f))
        except ValueError as e:
            QMessageBox.warning(self, t("Erreur", "Error"), str(e))
            return
        self.refresh(select=p)
        self.chosen.emit(str(p))

    def delete(self):
        it = self.list.currentItem()
        path = it.data(Qt.ItemDataRole.UserRole) if it else None
        if not path:
            return
        from PyQt6.QtWidgets import QMessageBox
        if QMessageBox.question(self, t("Supprimer", "Delete"), t("Supprimer cette signature ?", "Delete this signature?")) \
                == QMessageBox.StandardButton.Yes:
            Path(path).unlink(missing_ok=True)
            self.refresh()
