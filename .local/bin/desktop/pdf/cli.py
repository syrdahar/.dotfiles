"""CLI du moteur (utilisé par desk-pdf, le clic droit Dolphin et les tests).

    python3 -m pdf.cli tools                      id, libellé, type, entrées, icône (TSV)
    python3 -m pdf.cli options <outil>            options de l'outil (JSON)
    python3 -m pdf.cli exts <outil>               extensions acceptées (une par ligne)
    python3 -m pdf.cli run <outil> [--opt clé=valeur]… [--password-stdin] fichiers…
    python3 -m pdf.cli gui [--tool <outil>] [fichiers…]
    python3 -m pdf.cli pick [--multi] [--tool <outil>]   sélecteur de fichiers Qt → chemins

run : chemins créés sur stdout (un par ligne) ; « warning: … » et « info: … » sur stderr.
  --password-stdin : ligne 1 = mot de passe du fichier d'entrée (vide si aucun),
                     ligne 2 = nouveau mot de passe (protect).
Codes : 0 OK · 1 erreur (message sur stderr) · 2 usage · 3 mot de passe requis ou incorrect.
Journal : ~/.local/state/desk/pdf.log (DESK_PDF_LOG), sans jamais de mot de passe.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from . import ops, tools
from .errors import OpError, PasswordError
from .i18n import STATE, t

SECRET_KEYS = {"new_password", "password"}


def human(n):
    for unit in ("o", "Ko", "Mo", "Go"):
        if n < 1024 or unit == "Go":
            return f"{n:.0f} {unit}" if unit == "o" else f"{n:.1f} {unit}".replace(".", ",")
        n /= 1024
    return str(n)


def log(line):
    path = Path(os.environ.get("DESK_PDF_LOG") or STATE / "pdf.log")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")
    except OSError:
        pass


def extensions(tool):
    return {"pdf": [".pdf"], "pdfs": [".pdf"], "images": sorted(ops.IMAGE_EXT),
            "convertible": sorted(ops.CONVERTIBLE_EXT), "url": [".html", ".htm"]}[tool.accepts]


def cmd_run(a):
    try:
        tool = tools.get(a.tool)
    except KeyError:
        print(t(f"Outil inconnu : {a.tool}", f"Unknown tool: {a.tool}"), file=sys.stderr)
        return 2
    opts = {}
    for kv in a.opt:
        k, sep, v = kv.partition("=")
        if not sep or k not in {o.key for o in tool.options}:
            print(t(f"Option invalide pour {a.tool} : {kv}", f"Invalid option for {a.tool}: {kv}"), file=sys.stderr)
            return 2
        opts[k] = v
    password = None
    if a.password_stdin:
        lines = sys.stdin.read().split("\n")
        password = lines[0] or None
        if a.tool == "protect" and "new_password" not in opts and len(lines) > 1:
            opts["new_password"] = lines[1]
    safe = {k: v for k, v in opts.items() if k not in SECRET_KEYS}
    try:
        out = tools.run(a.tool, a.files, opts, password)
    except PasswordError as e:
        log(f"{a.tool} {a.files} {safe} → password ({'wrong' if e.wrong else 'required'})")
        print(e, file=sys.stderr)
        return 3
    except OpError as e:
        log(f"{a.tool} {a.files} {safe} → error: {e}")
        print(e, file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001 — bug : message court, détail dans le journal
        import traceback
        log(f"{a.tool} {a.files} {safe} → crash: {traceback.format_exc()}")
        print(t(f"Erreur inattendue : {e} (voir {STATE / 'pdf.log'})",
                f"Unexpected error: {e} (see {STATE / 'pdf.log'})"), file=sys.stderr)
        return 1
    for w in ops.WARNINGS:
        print(f"warning: {w}", file=sys.stderr)
    if a.tool == "compress" and ops.LAST_GAIN:
        before, after = ops.LAST_GAIN
        if out:
            print(f"info: {human(before)} → {human(after)} (−{100 - after * 100 // before} %)", file=sys.stderr)
        else:
            print("info: " + t(f"déjà optimisé ({human(before)}) : aucun fichier créé",
                               f"already optimal ({human(before)}): no file created"), file=sys.stderr)
    log(f"{a.tool} {a.files} {safe} → {[str(p) for p in out]}")
    for p in out:
        print(p)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="desk pdf cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tools")
    sub.add_parser("options").add_argument("tool")
    sub.add_parser("exts").add_argument("tool")
    r = sub.add_parser("run")
    r.add_argument("tool")
    r.add_argument("--opt", action="append", default=[])
    r.add_argument("--password-stdin", action="store_true")
    r.add_argument("files", nargs="*")
    g = sub.add_parser("gui")
    g.add_argument("--tool")
    g.add_argument("files", nargs="*")
    pk = sub.add_parser("pick")
    pk.add_argument("--multi", action="store_true")
    pk.add_argument("--tool")
    a = ap.parse_args(argv)

    if a.cmd == "tools":
        for tl in tools.TOOLS:
            print("\t".join([tl.id, tl.label, tl.kind, tl.accepts, tl.icon]))
        return 0
    if a.cmd in ("options", "exts"):
        try:
            tool = tools.get(a.tool)
        except KeyError:
            print(f"unknown tool: {a.tool}", file=sys.stderr)
            return 2
        if a.cmd == "options":
            print(json.dumps(tools.options_json(a.tool), ensure_ascii=False))
        else:
            print("\n".join(extensions(tool)))
        return 0
    if a.cmd == "run":
        return cmd_run(a)
    if a.cmd == "gui":
        from . import app
        return app.main(a.tool, [Path(f) for f in a.files])
    if a.cmd == "pick":
        from . import qtutil
        paths = qtutil.pick_files(tools.get(a.tool) if a.tool else None, a.multi)
        print("\n".join(str(p) for p in paths))
        return 0 if paths else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
