"""Utilitaires Qt partagés par la fenêtre : application, icônes, sélecteur, fil d'exécution, mots de passe."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QFileDialog, QInputDialog, QLineEdit, QMessageBox

from . import tools
from .errors import OpError, PasswordError
from .i18n import bi, t

DESK = Path(__file__).resolve().parent.parent / "desk"


_APP = None   # référence gardée : sinon Python détruit la QApplication


def ensure_app():
    global _APP
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
        app.setApplicationName("desk-pdf")
        app.setApplicationDisplayName(t("Boîte à outils PDF", "PDF toolbox"))
        app.setDesktopFileName("desk-pdf")
        app.setWindowIcon(QIcon.fromTheme("application-pdf"))
    _APP = app
    return app


def icon(name, fallback="application-pdf"):
    return QIcon.fromTheme(name, QIcon.fromTheme(fallback))


def name_filter(tool):
    from .cli import extensions
    exts = extensions(tool) if tool else [".pdf"]
    pats = " ".join(f"*{e} *{e.upper()}" for e in exts)
    return f"{bi(tool.label) if tool else 'PDF'} ({pats});;{t('Tous les fichiers', 'All files')} (*)"


def pick_files(tool=None, multi=False, parent=None, start=None):
    ensure_app()
    start = str(start or Path.home())
    caption = bi(tool.label) if tool else t("Choisir un PDF", "Choose a PDF")
    if multi:
        files, _ = QFileDialog.getOpenFileNames(parent, caption, start, name_filter(tool))
    else:
        f, _ = QFileDialog.getOpenFileName(parent, caption, start, name_filter(tool))
        files = [f] if f else []
    return [Path(f) for f in files]


def ask_password(parent, message, title=None):
    pw, ok = QInputDialog.getText(parent, title or t("Mot de passe", "Password"), message,
                                  QLineEdit.EchoMode.Password)
    return pw if ok else None


def run_with_password(parent, fn, *args, **kw):
    """Appelle fn(*args, password=…, **kw) ; redemande le mot de passe (3 essais) si besoin.
    → résultat, ou None si l'utilisateur annule."""
    password, tries = kw.pop("password", None), 0
    while True:
        try:
            return fn(*args, password=password, **kw)
        except PasswordError as e:
            tries += 1
            if tries > 3:
                raise OpError(t("Trop d'essais : mot de passe incorrect", "Too many attempts: wrong password")) from None
            password = ask_password(parent, str(e))
            if password is None:
                return None


def error(parent, err):
    QMessageBox.warning(parent, t("Erreur", "Error"), str(err))


def open_path(p):
    subprocess.Popen(["xdg-open", str(p)], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def show_in_files(p):
    cmd = ["dolphin", "--select", str(p)] if shutil.which("dolphin") else ["xdg-open", str(Path(p).parent)]
    subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def notify_done(tool_id, paths):
    """Même notification que rofi / Dolphin (boutons Ouvrir, Afficher, → Drive)."""
    if not paths or os.environ.get("DESK_PDF_NO_NOTIFY"):
        return
    subprocess.Popen([str(DESK), "pdf", "notify-done", tool_id, *map(str, paths)], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class Worker(QThread):
    """Lance tools.run dans un fil séparé (l'interface reste fluide)."""
    done = pyqtSignal(list, list)          # chemins créés, avertissements/infos
    failed = pyqtSignal(str)
    need_password = pyqtSignal(str, bool)  # message, mot de passe faux ?

    def __init__(self, tool_id, files, opts, password=None):
        super().__init__()
        self.tool_id, self.files, self.opts, self.password = tool_id, files, opts, password

    def run(self):
        from . import ops
        try:
            out = tools.run(self.tool_id, self.files, self.opts, self.password)
        except PasswordError as e:
            self.need_password.emit(str(e), e.wrong)
            return
        except OpError as e:
            self.failed.emit(str(e))
            return
        except Exception as e:  # noqa: BLE001
            import traceback
            from .cli import log
            log(f"gui {self.tool_id} crash: {traceback.format_exc()}")
            self.failed.emit(t(f"Erreur inattendue : {e}", f"Unexpected error: {e}"))
            return
        notes = list(ops.WARNINGS)
        if self.tool_id == "compress" and ops.LAST_GAIN:
            from .cli import human
            b, a = ops.LAST_GAIN
            notes.append(f"{human(b)} → {human(a)} (−{100 - a * 100 // b} %)" if out else
                         t(f"Déjà optimisé ({human(b)}) : aucun fichier créé", f"Already optimal ({human(b)}): no file created"))
        self.done.emit([str(p) for p in out], notes)
