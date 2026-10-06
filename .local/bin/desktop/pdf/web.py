"""Rendu HTML → PDF avec Qt WebEngine (Chromium de Qt), sans fenêtre.

    python3 -m pdf.web <source> <sortie.pdf> [délai_s]
source : URL (http, https, file), fichier .html, .md/.markdown (python-markdown) ou .txt.
Écrit le PDF (A4, fonds imprimés) et affiche le titre de la page sur stdout ;
code 1 et message sur stderr en cas d'échec. Lancé dans un sous-processus par
ops.webpage / ops.convert pour ne jamais imbriquer deux boucles Qt.
"""
import html
import os
import sys
from pathlib import Path

CSS = """<style>
body { font-family: "Noto Sans", "DejaVu Sans", sans-serif; font-size: 11pt; line-height: 1.45; margin: 0; }
pre, code { font-family: "JetBrains Mono", "DejaVu Sans Mono", monospace; font-size: 9.5pt; }
pre { white-space: pre-wrap; background: #f4f4f4; padding: 8px; }
table { border-collapse: collapse; } td, th { border: 1px solid #aaa; padding: 3px 6px; }
img { max-width: 100%; }
</style>"""


def page_html(path):
    """→ (html, titre) pour .md / .txt ; None pour le reste (chargé comme URL)."""
    ext = path.suffix.lower()
    if ext in (".md", ".markdown"):
        import markdown
        body = markdown.markdown(path.read_text(errors="replace"),
                                 extensions=["extra", "sane_lists", "toc"])
    elif ext == ".txt":
        body = f"<pre>{html.escape(path.read_text(errors='replace'))}</pre>"
    else:
        return None
    title = html.escape(path.stem)
    return f"<!doctype html><meta charset='utf-8'><title>{title}</title>{CSS}{body}", path.stem


def render(source, out, timeout=30):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --disable-logging")
    os.environ.setdefault("QT_LOGGING_RULES", "*=false")
    from PyQt6.QtCore import QMarginsF, QTimer, QUrl
    from PyQt6.QtGui import QPageLayout, QPageSize
    from PyQt6.QtWebEngineCore import QWebEnginePage
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([sys.argv[0]])
    page = QWebEnginePage()
    state = {"err": None, "title": ""}

    def fail(msg):
        if state["err"] is None:
            state["err"] = msg
        app.quit()

    def printed(_path, ok):
        if not ok:
            fail("impression PDF impossible / PDF printing failed")
        else:
            app.quit()

    def loaded(ok):
        if not ok:
            fail(f"page injoignable / page unreachable: {source}")
            return
        state["title"] = page.title()
        layout = QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait,
                             QMarginsF(12, 12, 12, 12), QPageLayout.Unit.Millimeter)
        QTimer.singleShot(1000, lambda: page.printToPdf(str(out), layout))

    page.pdfPrintingFinished.connect(printed)
    page.loadFinished.connect(loaded)
    QTimer.singleShot(timeout * 1000, lambda: fail(f"délai dépassé / timed out ({timeout} s)"))

    p = Path(source).expanduser()
    local = p.exists() and "://" not in source
    doc = page_html(p) if local else None
    if doc:
        page.setHtml(doc[0], QUrl.fromLocalFile(str(p.resolve().parent) + "/"))
    elif local:
        page.load(QUrl.fromLocalFile(str(p.resolve())))
    else:
        page.load(QUrl.fromUserInput(source))
    app.exec()
    page.deleteLater()
    if state["err"]:
        raise RuntimeError(state["err"])
    title = state["title"]
    if doc and (not title or title == p.name):
        title = doc[1]
    return title


if __name__ == "__main__":
    try:
        print(render(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 30))
    except Exception as e:  # noqa: BLE001
        print(e, file=sys.stderr)
        sys.exit(1)
