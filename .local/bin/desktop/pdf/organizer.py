"""Organiseur : miniatures de pages (un ou plusieurs PDF) à réordonner, pivoter, supprimer, extraire.
Rien n'est écrit avant « Enregistrer » ; construction finale par ops.build (sans perte)."""
from pathlib import Path

import pymupdf as fitz
from PyQt6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QImage, QKeySequence, QPainter, QPixmap, QShortcut, QTransform
from PyQt6.QtWidgets import (QAbstractItemView, QFileDialog, QHBoxLayout, QLabel, QListView, QListWidget,
                             QListWidgetItem, QPushButton, QSlider, QVBoxLayout, QWidget)

from . import ops, tools
from .errors import OpError
from .history import History
from .i18n import bi, t
from .naming import out_path
from .qtutil import error, icon, notify_done, pick_files, run_with_password

REF = Qt.ItemDataRole.UserRole          # ops.PageRef
COLORS = ["#ff4fa3", "#35d0ff", "#ffd23f", "#7dff8a", "#b18cff", "#ff8a3d"]
SUFFIX = {"merge": "merged", "rearrange": "reordered", "rotate": "rotated", "remove": "removed", "extract": "extract"}


class _Signals(QObject):
    ready = pyqtSignal(str, int, QImage)


class ThumbJob(QRunnable):
    """Rend une page en miniature dans un fil du QThreadPool."""

    def __init__(self, path, index, password, size, signals):
        super().__init__()
        self.path, self.index, self.password, self.size, self.signals = path, index, password, size, signals

    def run(self):
        try:
            doc = fitz.open(self.path)
            if doc.needs_pass:
                doc.authenticate(self.password or "")
            page = doc[self.index]
            zoom = self.size / max(page.rect.width, page.rect.height)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
            doc.close()
            self.signals.ready.emit(str(self.path), self.index, img)
        except Exception:  # noqa: BLE001 — une miniature ratée ne doit rien bloquer
            pass


class PageList(QListWidget):
    moved = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setMovement(QListView.Movement.Snap)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setWrapping(True)
        self.setSpacing(10)
        self.setUniformItemSizes(True)
        self.setWordWrap(True)

    def dropEvent(self, e):
        if e.source() is self:
            super().dropEvent(e)
            self.moved.emit()
        else:
            e.ignore()


class OrganizerPage(QWidget):
    def __init__(self, tool_id, files):
        super().__init__()
        self.tool_id = tool_id
        self.tool = tools.get(tool_id)
        self.sources, self.passwords, self.colors = [], {}, {}
        self.thumbs = {}                        # (chemin, index) → QImage
        self.size = 150
        self.history = None
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(max(2, QThreadPool.globalInstance().maxThreadCount() // 2))
        self.signals = _Signals(self)
        self.signals.ready.connect(self.thumb_ready)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 8, 14, 10)
        head = QHBoxLayout()
        title = QLabel(bi(self.tool.label))
        title.setObjectName("title")
        head.addWidget(title)
        self.info = QLabel()
        self.info.setEnabled(False)
        head.addWidget(self.info)
        head.addStretch()
        lay.addLayout(head)

        bar = QHBoxLayout()
        def btn(ic, text, fn, tip=""):
            b = QPushButton(icon(ic), text)
            b.clicked.connect(fn)
            if tip:
                b.setToolTip(tip)
            bar.addWidget(b)
            return b
        btn("list-add", t("Ajouter", "Add"), self.add_dialog, t("Ajouter un PDF…", "Add a PDF…"))
        btn("object-rotate-left", "", lambda: self.rotate_selected(-90), t("Pivoter à gauche (Ctrl+←)", "Rotate left (Ctrl+←)"))
        btn("object-rotate-right", "", lambda: self.rotate_selected(90), t("Pivoter à droite (Ctrl+→)", "Rotate right (Ctrl+→)"))
        btn("edit-delete", t("Supprimer", "Delete"), self.delete_selected, t("Suppr", "Del"))
        btn("view-sort-descending", t("Inverser", "Reverse"), self.reverse_all)
        self.undo_btn = btn("edit-undo", "", self.undo, "Ctrl+Z")
        self.redo_btn = btn("edit-redo", "", self.redo, "Ctrl+Shift+Z")
        bar.addStretch()
        bar.addWidget(QLabel(t("Taille", "Size")))
        zoom = QSlider(Qt.Orientation.Horizontal)
        zoom.setRange(80, 300)
        zoom.setValue(self.size)
        zoom.setFixedWidth(140)
        zoom.valueChanged.connect(self.set_size)
        bar.addWidget(zoom)
        lay.addLayout(bar)

        self.list = PageList()
        self.list.moved.connect(self.after_move)
        self.list.itemSelectionChanged.connect(self.update_info)
        lay.addWidget(self.list, 1)

        foot = QHBoxLayout()
        self.legend = QLabel()
        foot.addWidget(self.legend, 1)
        btn_extract = QPushButton(icon("extract-archive"), t("Extraire", "Extract"))
        btn_extract.setToolTip(t("Extraire les pages sélectionnées dans un nouveau PDF", "Extract the selected pages to a new PDF"))
        btn_extract.clicked.connect(self.extract_selected)
        foot.addWidget(btn_extract)
        save_as = QPushButton(icon("document-save-as"), "")
        save_as.setToolTip(t("Enregistrer sous…", "Save as…"))
        save_as.clicked.connect(lambda: self.save(ask=True))
        foot.addWidget(save_as)
        save = QPushButton(icon("document-save"), t("Enregistrer", "Save"))
        save.setToolTip("Ctrl+S")
        save.setDefault(True)
        save.clicked.connect(lambda: self.save())
        foot.addWidget(save)
        lay.addLayout(foot)

        for seq, fn in (("Ctrl+Z", self.undo), ("Ctrl+Shift+Z", self.redo), ("Ctrl+Y", self.redo), ("Delete", self.delete_selected),
                        ("Ctrl+Left", lambda: self.rotate_selected(-90)), ("Ctrl+Right", lambda: self.rotate_selected(90)),
                        ("Ctrl+S", self.save), ("Ctrl+A", self.list.selectAll)):
            QShortcut(QKeySequence(seq), self, fn)

        for f in files:
            self.add_file(Path(f), record=False)
        self.set_size(self.size)
        self.history = History(self.page_refs(), self.history_changed)
        self.history_changed()

    def shutdown(self):
        """À appeler avant de détruire la page : plus aucune miniature en vol."""
        self.pool.clear()
        self.pool.waitForDone(3000)

    # ── état ──
    def page_refs(self):
        return [ops.PageRef(**vars(self.list.item(i).data(REF))) for i in range(self.list.count())]

    @property
    def dirty(self):
        return self.history is not None and not self.history.is_clean()

    def history_changed(self):
        self.undo_btn.setEnabled(self.history.can_undo())
        self.redo_btn.setEnabled(self.history.can_redo())
        self.update_info()

    def restore(self, refs):
        self.list.clear()
        for r in refs:
            self._append(r)
        self.update_info()

    def record(self, _text=""):
        self.history.push(self.page_refs())

    def undo(self):
        refs = self.history.undo()
        if refs is not None:
            self.restore(refs)

    def redo(self):
        refs = self.history.redo()
        if refs is not None:
            self.restore(refs)

    # ── fichiers ──
    def add_dialog(self):
        for f in pick_files(tools.get("merge"), True, self):
            self.add_file(f)

    def add_files(self, paths):   # dépôt sur la fenêtre
        for p in paths:
            if p.suffix.lower() == ".pdf":
                self.add_file(p)

    def add_file(self, path, record=True):
        path = Path(path).resolve()
        try:
            doc = run_with_password(self, self._open, path)
        except OpError as e:
            error(self, e)
            return
        if doc is None:
            return
        n = len(doc)
        doc.close()
        if path not in self.colors:
            self.colors[path] = COLORS[len(self.colors) % len(COLORS)]
            self.sources.append(path)
        for i in range(n):
            self._append(ops.PageRef(path, i, 0))
        self.update_legend()
        if record and self.history is not None:
            self.record()

    def _open(self, path, password=None):
        doc = ops.open_doc(path, password)
        if password:
            self.passwords[path] = password
        return doc

    def _append(self, ref):
        it = QListWidgetItem()
        it.setData(REF, ref)
        it.setFlags(it.flags() | Qt.ItemFlag.ItemIsDragEnabled)
        it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)
        self.list.addItem(it)
        self._paint(it)
        key = (str(ref.src), ref.index)
        if key not in self.thumbs:
            self.thumbs[key] = None
            self.pool.start(ThumbJob(ref.src, ref.index, self.passwords.get(Path(ref.src)), 300, self.signals))

    def thumb_ready(self, path, index, img):
        self.thumbs[(path, index)] = img
        for i in range(self.list.count()):
            it = self.list.item(i)
            r = it.data(REF)
            if str(r.src) == path and r.index == index:
                self._paint(it)

    def _paint(self, it):
        """Miniature (tournée) + pastille de couleur du fichier d'origine + numéro de page."""
        r = it.data(REF)
        s = self.size
        canvas = QPixmap(s, s)
        canvas.fill(Qt.GlobalColor.transparent)
        p = QPainter(canvas)
        img = self.thumbs.get((str(r.src), r.index))
        if img is not None:
            pm = QPixmap.fromImage(img).transformed(QTransform().rotate(r.rotate % 360))
            pm = pm.scaled(s - 8, s - 8, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap((s - pm.width()) // 2, (s - pm.height()) // 2, pm)
        else:
            p.fillRect(s // 4, s // 8, s // 2, s * 3 // 4, QColor(255, 255, 255, 40))
        if len(self.sources) > 1:
            p.setBrush(QColor(self.colors.get(Path(r.src), "#888")))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(4, 4, 14, 14)
        p.end()
        it.setIcon(QIcon(canvas))
        label = f"{r.index + 1}"
        if len(self.sources) > 1:
            label = f"{Path(r.src).stem[:14]} · {label}"
        if r.rotate % 360:
            label += f"  ↻{r.rotate % 360}°"
        it.setText(label)

    def set_size(self, s):
        self.size = s
        self.list.setIconSize(QSize(s, s))
        self.list.setGridSize(QSize(s + 24, s + 40))
        for i in range(self.list.count()):
            self._paint(self.list.item(i))

    def update_legend(self):
        if len(self.sources) > 1:
            self.legend.setText("   ".join(f"<span style='color:{self.colors[s]}'>●</span> {s.name}" for s in self.sources))
        else:
            self.legend.setText(self.sources[0].name if self.sources else "")

    def update_info(self):
        n, sel = self.list.count(), len(self.list.selectedItems())
        self.info.setText(t(f"{n} pages", f"{n} pages") + (t(f" · {sel} sélectionnée(s)", f" · {sel} selected") if sel else ""))

    # ── actions ──
    def selected(self):
        return sorted(self.list.selectedItems(), key=self.list.row)

    def rotate_selected(self, delta):
        items = self.selected()
        if not items:
            return
        for it in items:
            r = it.data(REF)
            r.rotate = (r.rotate + delta) % 360
            it.setData(REF, r)
            self._paint(it)
        self.record(t("Pivoter", "Rotate"))

    def delete_selected(self):
        items = self.selected()
        if not items:
            return
        if len(items) == self.list.count():
            error(self, t("Impossible de supprimer toutes les pages", "Cannot delete every page"))
            return
        for it in items:
            self.list.takeItem(self.list.row(it))
        self.record(t("Supprimer", "Delete"))

    def reverse_all(self):
        self.restore(self.page_refs()[::-1])
        self.record()

    def after_move(self):
        if [vars(r) for r in self.page_refs()] != [vars(r) for r in self.history.current()]:
            self.record()

    def default_dest(self):
        first = self.sources[0] if self.sources else Path.home() / "document.pdf"
        return out_path(first, SUFFIX.get(self.tool_id, "reordered"))

    def _build(self, refs, dest):
        try:
            out = ops.build(refs, dest, self.passwords)
        except OpError as e:
            error(self, e)
            return None
        notify_done(self.tool_id, [out])
        return out

    def extract_selected(self):
        items = self.selected()
        if not items:
            error(self, t("Sélectionne d'abord des pages", "Select pages first"))
            return None
        refs = [it.data(REF) for it in items]
        return self._build(refs, out_path(self.sources[0], "extract"))

    def save(self, ask=False):
        dest = self.default_dest()
        if ask:
            f, _ = QFileDialog.getSaveFileName(self, t("Enregistrer sous", "Save as"), str(dest), "PDF (*.pdf)")
            if not f:
                return None
            dest = Path(f)
            if dest.suffix.lower() != ".pdf":
                dest = dest.with_suffix(".pdf")
        out = self._build(self.page_refs(), dest)
        if out:
            self.history.set_clean()
            self.info.setText(t(f"Enregistré : {out}", f"Saved: {out}"))
        return out
