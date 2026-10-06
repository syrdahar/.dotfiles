"""Fenêtre desk pdf : accueil (16 tuiles, favoris, dépôt de fichiers) et outils simples.
L'organiseur (organizer.py) et l'éditeur (editor.py) sont des pages du même QStackedWidget."""
import shutil
import sys
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame,
                             QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMainWindow, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSpinBox,
                             QStackedWidget, QToolButton, QVBoxLayout, QWidget)

from . import tools
from .cli import extensions
from .i18n import STATE, bi, t
from .qtutil import (Worker, ask_password, ensure_app, error, icon, notify_done, open_path, pick_files,
                     show_in_files)

FAVORITES = STATE / "pdf.favorites"
TILE_W, TILE_H = 168, 118

STYLE = """
QToolButton#tile { border: 1px solid palette(mid); border-radius: 10px; padding: 10px 6px 8px 6px; }
QToolButton#tile:hover { border: 1px solid palette(highlight); }
QToolButton#tile:disabled { color: palette(mid); }
QToolButton#star { border: none; background: transparent; font-size: 13pt; color: rgba(255, 255, 255, 0.35); }
QToolButton#star[fav="true"] { color: palette(highlight); }
QToolButton#star:hover { color: palette(highlight); }
QLabel#title { font-size: 15pt; font-weight: 600; }
QLabel#banner { padding: 6px 10px; border-radius: 6px; border: 1px solid palette(highlight); }
QFrame#result { border: 1px solid palette(mid); border-radius: 8px; }
"""


def load_favorites():
    try:
        return [l.strip() for l in FAVORITES.read_text().splitlines() if l.strip()]
    except OSError:
        return []


def save_favorites(favs):
    FAVORITES.parent.mkdir(parents=True, exist_ok=True)
    FAVORITES.write_text("".join(f + "\n" for f in favs))


def accepts_file(tool, path):
    if tool.accepts == "url":
        return path.suffix.lower() in (".html", ".htm")
    return path.suffix.lower() in extensions(tool)


# ── Accueil ──────────────────────────────────────────────────
class Tile(QToolButton):
    """Tuile : icône + libellé sur deux lignes + étoile de favori (coin haut droit)."""

    def __init__(self, tool, fav, on_star):
        super().__init__()
        self.tool = tool
        self.setObjectName("tile")
        self.setToolTip(bi(tool.label))
        self.setFixedSize(TILE_W, TILE_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 14, 8, 8)
        ic = QLabel()
        ic.setPixmap(icon(tool.icon).pixmap(40, 40))
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text = QLabel(bi(tool.label).split(" (")[0])
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        for w in (ic, text):
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            lay.addWidget(w)
        self.text = text
        self.star = QToolButton(self)
        self.star.setObjectName("star")
        self.star.setText("★" if fav else "☆")
        self.star.setProperty("fav", fav)
        self.star.setToolTip(t("Favori (affiché en premier)", "Favorite (shown first)"))
        self.star.setCursor(Qt.CursorShape.PointingHandCursor)
        self.star.clicked.connect(lambda: on_star(tool.id))
        self.star.move(TILE_W - 26, 4)

    def changeEvent(self, e):
        super().changeEvent(e)
        self.text.setEnabled(self.isEnabled())


class HomePage(QWidget):
    open_tool = pyqtSignal(str, list)

    def __init__(self):
        super().__init__()
        self.pending = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        head = QHBoxLayout()
        title = QLabel(t("Boîte à outils PDF", "PDF toolbox"))
        title.setObjectName("title")
        head.addWidget(title)
        head.addStretch()
        lay.addLayout(head)
        sub = QLabel(t("Hors ligne · dépose des fichiers n'importe où · ☆ = favori · rien n'est jamais écrasé",
                       "Offline · drop files anywhere · ☆ = favorite · nothing is ever overwritten"))
        sub.setEnabled(False)
        sub.setWordWrap(True)
        lay.addWidget(sub)
        self.banner = QLabel()
        self.banner.setObjectName("banner")
        self.banner.hide()
        lay.addWidget(self.banner)
        self.grid = QGridLayout()
        self.grid.setSpacing(10)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        lay.addLayout(self.grid)
        lay.addStretch()
        self.tiles = {}
        self.rebuild()

    def rebuild(self):
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.deleteLater()
        favs = load_favorites()
        order = sorted(tools.TOOLS, key=lambda tl: (tl.id not in favs, favs.index(tl.id) if tl.id in favs else 0))
        self.tiles = {}
        self.ordered = []
        for tool in order:
            tile = Tile(tool, tool.id in favs, self.toggle_star)
            tile.clicked.connect(lambda _=False, i=tool.id: self.open_tool.emit(i, list(self.pending)))
            self.tiles[tool.id] = tile
            self.ordered.append(tile)
        self.cols = 0
        self.relayout()
        self.apply_filter()

    def relayout(self):
        cols = max(2, min(8, (self.width() - 36 + 10) // (TILE_W + 10)))
        if cols == self.cols:
            return
        self.cols = cols
        for tile in self.ordered:
            self.grid.removeWidget(tile)
        for k, tile in enumerate(self.ordered):
            self.grid.addWidget(tile, k // cols, k % cols)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.relayout()

    def toggle_star(self, tool_id):
        favs = load_favorites()
        if tool_id in favs:
            favs.remove(tool_id)
        else:
            favs.append(tool_id)
        save_favorites(favs)
        self.rebuild()

    def order(self):
        return [tile.tool.id for tile in self.ordered]

    def add_files(self, files):
        self.pending = list(files)
        self.apply_filter()

    def clear_pending(self):
        self.pending = []
        self.apply_filter()

    def apply_filter(self):
        for tile in self.tiles.values():
            tool = tile.tool
            ok = not self.pending or all(accepts_file(tool, f) for f in self.pending)
            if ok and tool.id == "merge" and self.pending:
                ok = len(self.pending) >= 2
            tile.setEnabled(ok)
        if self.pending:
            names = ", ".join(f.name for f in self.pending[:3]) + (" …" if len(self.pending) > 3 else "")
            self.banner.setText(t(f"{len(self.pending)} fichier(s) : {names} — choisis un outil (Échap pour annuler)",
                                  f"{len(self.pending)} file(s): {names} — pick a tool (Esc to clear)"))
            self.banner.show()
        else:
            self.banner.hide()


# ── Outil simple ─────────────────────────────────────────────
class FileList(QListWidget):
    def __init__(self):
        super().__init__()
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        QShortcut(QKeySequence.StandardKey.Delete, self, self.remove_selected)

    def add(self, paths):
        have = set(self.paths())
        for p in paths:
            if str(p) not in {str(h) for h in have}:
                it = QListWidgetItem(icon("application-pdf" if p.suffix.lower() == ".pdf" else "text-x-generic"), p.name)
                it.setData(Qt.ItemDataRole.UserRole, str(p))
                it.setToolTip(str(p))
                self.addItem(it)

    def paths(self):
        return [Path(self.item(i).data(Qt.ItemDataRole.UserRole)) for i in range(self.count())]

    def remove_selected(self):
        for it in self.selectedItems():
            self.takeItem(self.row(it))


class SimpleToolPage(QWidget):
    open_organizer = pyqtSignal(str, list)

    def __init__(self, tool, files):
        super().__init__()
        self.tool, self.worker, self.results, self.dirty = tool, None, [], False
        self.password, self.tries = None, 0
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        head = QHBoxLayout()
        ic = QLabel()
        ic.setPixmap(icon(tool.icon).pixmap(32, 32))
        head.addWidget(ic)
        title = QLabel(bi(tool.label))
        title.setObjectName("title")
        head.addWidget(title)
        head.addStretch()
        lay.addLayout(head)

        body = QHBoxLayout()
        lay.addLayout(body, 1)
        left = QVBoxLayout()
        body.addLayout(left, 3)
        if tool.accepts == "url":
            left.addWidget(QLabel(t("Adresse de la page (URL ou fichier .html) — le PDF va dans ~/Downloads",
                                    "Page address (URL or .html file) — the PDF goes to ~/Downloads")))
            self.url = QLineEdit()
            self.url.setPlaceholderText("https://…")
            clip = QApplicationClipboard()
            if clip.startswith(("http://", "https://")):
                self.url.setText(clip)
            if files:
                self.url.setText(str(files[0]))
            left.addWidget(self.url)
            left.addStretch()
            self.files = None
        else:
            multi = tool.accepts in ("pdfs", "images")
            left.addWidget(QLabel(t("Fichiers (glisser pour réordonner, Suppr pour retirer)",
                                    "Files (drag to reorder, Del to remove)") if multi or len(files) > 1 else
                                  t("Fichier(s)", "File(s)")))
            self.files = FileList()
            self.files.add(files)
            left.addWidget(self.files, 1)
            row = QHBoxLayout()
            add = QPushButton(icon("list-add"), t("Ajouter…", "Add…"))
            add.clicked.connect(self.add_dialog)
            rem = QPushButton(icon("list-remove"), t("Retirer", "Remove"))
            rem.clicked.connect(self.files.remove_selected)
            row.addWidget(add)
            row.addWidget(rem)
            if tool.id in ("rotate", "remove", "extract"):
                vis = QPushButton(icon("view-grid"), t("Choisir visuellement…", "Pick visually…"))
                vis.setToolTip(t("Ouvrir l'organiseur (miniatures)", "Open the organizer (thumbnails)"))
                vis.clicked.connect(lambda: self.open_organizer.emit(tool.id, self.files.paths()))
                row.addWidget(vis)
            row.addStretch()
            left.addLayout(row)

        right = QVBoxLayout()
        body.addLayout(right, 2)
        self.form = QFormLayout()
        self.widgets, self.rows = {}, {}
        for opt in tool.options:
            w = self.make_widget(opt)
            self.widgets[opt.key] = w
            label = QLabel(bi(opt.label))
            label.setWordWrap(True)
            self.form.addRow(label, w)
            self.rows[opt.key] = (label, w)
            if opt.kind == "password" and opt.confirm:
                c = QLineEdit()
                c.setEchoMode(QLineEdit.EchoMode.Password)
                self.widgets[opt.key + "__confirm"] = c
                self.form.addRow(QLabel(t("Confirmer", "Confirm")), c)
        if not tool.options:
            self.form.addRow(QLabel(t("Aucune option", "No options")))
        right.addLayout(self.form)
        right.addStretch()
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        right.addWidget(self.progress)
        self.run_btn = QPushButton(icon("media-playback-start"), t("Lancer", "Run"))
        self.run_btn.setDefault(True)
        self.run_btn.setMinimumHeight(34)
        self.run_btn.clicked.connect(self.run)
        right.addWidget(self.run_btn)

        self.result = QFrame()
        self.result.setObjectName("result")
        rl = QVBoxLayout(self.result)
        self.result_label = QLabel()
        self.result_label.setWordWrap(True)
        self.result_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        rl.addWidget(self.result_label)
        rb = QHBoxLayout()
        for text_, ic_, fn in ((t("Ouvrir", "Open"), "document-open", lambda: open_path(self.results[0])),
                               (t("Afficher", "Show"), "folder-open", lambda: show_in_files(self.results[0])),
                               (t("Enregistrer sous…", "Save as…"), "document-save-as", self.save_as)):
            b = QPushButton(icon(ic_), text_)
            b.clicked.connect(fn)
            rb.addWidget(b)
        rb.addStretch()
        rl.addLayout(rb)
        self.result.hide()
        lay.addWidget(self.result)
        self.update_visibility()

    def make_widget(self, opt):
        if opt.kind == "choice":
            w = QComboBox()
            for val, label in opt.choices:
                w.addItem(bi(label), val)
            w.setCurrentIndex(max(0, w.findData(opt.default)))
            w.currentIndexChanged.connect(self.update_visibility)
        elif opt.kind == "bool":
            w = QCheckBox()
            w.setChecked(opt.default in ("yes", "true", "1"))
        elif opt.kind == "int":
            w = QSpinBox()
            w.setRange(1, 10000)
            w.setValue(int(opt.default or 1))
        else:
            w = QLineEdit(opt.default)
            if opt.kind == "password":
                w.setEchoMode(QLineEdit.EchoMode.Password)
            if opt.hint:
                w.setPlaceholderText(bi(opt.hint))
        return w

    def values(self):
        out = {}
        for opt in self.tool.options:
            w = self.widgets[opt.key]
            if isinstance(w, QComboBox):
                out[opt.key] = w.currentData()
            elif isinstance(w, QCheckBox):
                out[opt.key] = "yes" if w.isChecked() else "no"
            elif isinstance(w, QSpinBox):
                out[opt.key] = str(w.value())
            else:
                out[opt.key] = w.text()
        return out

    def update_visibility(self):
        vals = self.values()
        for opt in self.tool.options:
            if opt.when:
                show = vals.get(opt.when[0]) == opt.when[1]
                for w in self.rows[opt.key]:
                    w.setVisible(show)

    def add_files(self, paths):
        if self.files is not None:
            self.files.add([p for p in paths if accepts_file(self.tool, p)])
        elif paths:
            self.url.setText(str(paths[0]))

    def add_dialog(self):
        start = self.files.paths()[0].parent if self.files.count() else None
        self.files.add(pick_files(self.tool, True, self, start))

    def inputs(self):
        if self.files is None:
            return [self.url.text().strip()] if self.url.text().strip() else []
        return self.files.paths()

    def run(self):
        files = self.inputs()
        if not files:
            error(self, t("Ajoute au moins un fichier", "Add at least one file") if self.files is not None
                  else t("Indique une adresse", "Enter an address"))
            return
        opts = self.values()
        for opt in self.tool.options:
            if opt.kind == "password" and opt.confirm and opts[opt.key] != self.widgets[opt.key + "__confirm"].text():
                error(self, t("Les mots de passe diffèrent", "Passwords do not match"))
                return
        self.start(files, opts)

    def start(self, files, opts):
        self.result.hide()
        self.run_btn.setEnabled(False)
        self.progress.show()
        self.worker = Worker(self.tool.id, files, opts, self.password)
        self.worker.done.connect(self.finished)
        self.worker.failed.connect(self.failed)
        self.worker.need_password.connect(lambda msg, _w: self.retry_password(msg, files, opts))
        self.worker.start()

    def stop(self):
        self.progress.hide()
        self.run_btn.setEnabled(True)

    def retry_password(self, msg, files, opts):
        self.stop()
        self.tries += 1
        if self.tries > 3:
            self.tries = 0
            error(self, t("Trop d'essais : mot de passe incorrect", "Too many attempts: wrong password"))
            return
        pw = ask_password(self, msg)
        if pw is None:
            self.tries = 0
            return
        self.password = pw
        self.start(files, opts)

    def failed(self, msg):
        self.stop()
        self.tries = 0
        error(self, msg)

    def finished(self, paths, notes):
        self.stop()
        self.tries = 0
        self.results = [Path(p) for p in paths]
        lines = [f"✓ {p}" for p in paths] + notes
        self.result_label.setText("\n".join(lines) or t("Aucun fichier créé", "No file created"))
        for b in self.result.findChildren(QPushButton):
            b.setEnabled(bool(paths))
        self.result.show()
        notify_done(self.tool.id, self.results)

    def save_as(self):
        if not self.results:
            return
        src = self.results[0]
        if src.is_dir():
            d = QFileDialog.getExistingDirectory(self, t("Déplacer le dossier dans…", "Move folder to…"), str(src.parent))
            dest = Path(d) / src.name if d else None
        else:
            f, _ = QFileDialog.getSaveFileName(self, t("Enregistrer sous", "Save as"), str(src), f"*{src.suffix}")
            dest = Path(f) if f else None
        if not dest or dest == src:
            return
        if dest.exists() and QMessageBox.question(self, t("Remplacer ?", "Replace?"),
                                                  t(f"{dest.name} existe déjà. Le remplacer ?",
                                                    f"{dest.name} already exists. Replace it?")) != QMessageBox.StandardButton.Yes:
            return
        if dest.exists():
            shutil.rmtree(dest) if dest.is_dir() else dest.unlink()
        shutil.move(str(src), str(dest))
        self.results[0] = dest
        self.result_label.setText("\n".join(f"✓ {p}" for p in self.results))


def QApplicationClipboard():
    try:
        return (ensure_app().clipboard().text() or "").strip()
    except Exception:  # noqa: BLE001
        return ""


# ── Fenêtre ──────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(t("Boîte à outils PDF", "PDF toolbox"))
        self.setAcceptDrops(True)
        self.resize(1360, 820)
        central = QWidget()
        self.setCentralWidget(central)
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        bar.setContentsMargins(10, 8, 10, 0)
        self.home_btn = QPushButton(icon("go-home"), t("Accueil", "Home"))
        self.home_btn.clicked.connect(self.go_home)
        self.home_btn.setToolTip("Alt+Home")
        bar.addWidget(self.home_btn)
        bar.addStretch()
        lay.addLayout(bar)
        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)
        self.home = HomePage()
        self.home.open_tool.connect(self.open_tool)
        scroll = QScrollArea()
        scroll.setWidget(self.home)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.stack.addWidget(scroll)
        self.page = None
        QShortcut(QKeySequence("Alt+Home"), self, self.go_home)
        QShortcut(QKeySequence("Escape"), self, self.escape)
        self.update_home_btn()

    def update_home_btn(self):
        self.home_btn.setVisible(self.page is not None)

    def escape(self):
        if self.page is None:
            self.home.clear_pending()

    def confirm_discard(self):
        if self.page is not None and getattr(self.page, "dirty", False):
            r = QMessageBox.question(self, t("Modifications non enregistrées", "Unsaved changes"),
                                     t("Abandonner les modifications ?", "Discard changes?"))
            return r == QMessageBox.StandardButton.Yes
        return True

    def go_home(self):
        if self.page is None or not self.confirm_discard():
            return
        self.stack.setCurrentIndex(0)
        self.drop_page()
        self.page = None
        self.home.clear_pending()
        self.setWindowTitle(t("Boîte à outils PDF", "PDF toolbox"))
        self.update_home_btn()

    def drop_page(self):
        if self.page is not None:
            if hasattr(self.page, "shutdown"):
                self.page.shutdown()
            self.stack.removeWidget(self.page)
            self.page.deleteLater()

    def set_page(self, page, title):
        self.drop_page()
        self.page = page
        self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)
        self.setWindowTitle(f"{title} — {t('Boîte à outils PDF', 'PDF toolbox')}")
        self.update_home_btn()

    def open_tool(self, tool_id, files):
        if not self.confirm_discard():
            return
        tool = tools.get(tool_id)
        files = [Path(f) for f in files if tool.accepts == "url" or accepts_file(tool, Path(f))]
        if tool.kind in ("editor", "sign"):
            if not files:
                files = pick_files(tool, False, self)
                if not files:
                    return
            from .editor import EditorPage
            from .errors import OpError
            try:
                page = EditorPage(files[0], mode="sign" if tool.kind == "sign" else "edit")
            except OpError as e:
                if "annul" not in str(e).lower() and "cancel" not in str(e).lower():
                    error(self, e)
                return
        elif tool.kind == "organizer":
            if not files:
                files = pick_files(tool, True, self)
                if not files:
                    return
            from .organizer import OrganizerPage
            page = OrganizerPage(tool_id, files)
        else:
            page = SimpleToolPage(tool, files)
            page.open_organizer.connect(self.open_organizer)
        self.set_page(page, bi(tool.label))

    def open_organizer(self, tool_id, files):
        if not files:
            files = pick_files(tools.get(tool_id), True, self)
            if not files:
                return
        from .organizer import OrganizerPage
        self.set_page(OrganizerPage(tool_id, files), bi(tools.get(tool_id).label))

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [Path(u.toLocalFile()) for u in e.mimeData().urls() if u.isLocalFile()]
        paths = [p for p in paths if p.is_file()]
        if not paths:
            return
        if self.page is None:
            self.home.add_files(paths)
        elif hasattr(self.page, "add_files"):
            self.page.add_files(paths)
        e.acceptProposedAction()

    def closeEvent(self, e):
        if self.confirm_discard():
            if self.page is not None and hasattr(self.page, "shutdown"):
                self.page.shutdown()
            e.accept()
        else:
            e.ignore()


def main(tool_id=None, files=()):
    app = ensure_app()
    app.setStyleSheet(STYLE)
    win = MainWindow()
    files = [Path(f).expanduser().resolve() for f in files]
    if tool_id:
        win.open_tool(tool_id, files)
    elif files:
        win.home.add_files(files)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main(None, sys.argv[1:]))
