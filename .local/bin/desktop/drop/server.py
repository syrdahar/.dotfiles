#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────────
#  desk drop — serveur de partage texte / fichiers sur le réseau local
#   python3 server.py            écoute sur 0.0.0.0:$DESK_DROP_PORT (8765)
#   python3 server.py --url      affiche l'URL à ouvrir depuis les autres appareils
#
#  Bibliothèque standard uniquement. Les autres appareils ouvrent l'URL dans un
#  navigateur (index.html, même dossier). Fichiers reçus : $DESK_DROP_DIR (~/Drop),
#  fil (textes + fichiers) : $XDG_STATE_HOME/desk/drop.json.
#  Un élément envoyé par un AUTRE appareil déclenche une notification à boutons
#  (texte → Copier ; fichier → Ouvrir · Dossier).
#
#  API : GET /api/items · GET /api/events (SSE) · POST /api/text {"text"}
#        POST /api/upload (corps brut, en-tête X-Filename encodé URL)
#        GET /f/<id>[?dl=1] · DELETE /api/items/<id> · POST /api/clear
# ──────────────────────────────────────────────────────────────
import ipaddress
import json
import mimetypes
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote_plus, urlparse, parse_qs

HERE = Path(__file__).resolve().parent
PORT = int(os.environ.get("DESK_DROP_PORT", "8765"))
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "desk"
VIRTUAL_IFACES = re.compile(r"^(lo|nordlynx|tun|tap|wg|docker|br-|virbr|veth|tailscale|zt)")
CHUNK = 1 << 20


# ── Réseau ───────────────────────────────────────────────────

def lan_ips():
    """IPv4 privées des interfaces physiques (pas le VPN, docker, libvirt…)."""
    try:
        out = subprocess.run(["ip", "-j", "-4", "addr"], capture_output=True, text=True, timeout=3).stdout
        ifaces = json.loads(out or "[]")
    except (OSError, subprocess.SubprocessError, ValueError):
        return []
    ips = []
    for iface in ifaces:
        if VIRTUAL_IFACES.match(iface.get("ifname", "")) or "UP" not in iface.get("flags", []):
            continue
        for a in iface.get("addr_info", []):
            ip = a.get("local", "")
            if ip and ipaddress.ip_address(ip).is_private:
                ips.append(ip)
    return ips


def url(port=PORT):
    ips = lan_ips()
    return f"http://{ips[0] if ips else socket.gethostname()}:{port}"


def device_name(ua):
    """Nom lisible d'un appareil d'après son User-Agent."""
    ua = ua or ""
    for pat, name in (("iPhone", "iPhone"), ("iPad", "iPad"), ("Android", "Android"),
                      ("Windows", "Windows"), ("Macintosh", "Mac"), ("CrOS", "ChromeOS"),
                      ("Linux", "Linux"), ("curl", "curl")):
        if pat in ua:
            return name
    return "?"


# ── Fil des éléments ─────────────────────────────────────────

def safe_name(name):
    name = unquote_plus(name or "").replace("\\", "/").split("/")[-1]
    name = re.sub(r"[\x00-\x1f]", "", name).strip().lstrip(".")
    return name[:200] or "fichier"


class Store:
    """Fil partagé (textes + fichiers), persisté en JSON ; `version` réveille les clients SSE."""

    def __init__(self, files_dir, state_file):
        self.dir = Path(files_dir)
        self.state = Path(state_file)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state.parent.mkdir(parents=True, exist_ok=True)
        self.cond = threading.Condition()
        self.version = 0
        try:
            self.items = json.loads(self.state.read_text())
        except (OSError, ValueError):
            self.items = []
        self._prune()

    def _prune(self):
        self.items = [i for i in self.items if i["type"] == "text" or (self.dir / i["file"]).is_file()]

    def _changed(self):
        tmp = self.state.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.items, ensure_ascii=False))
        tmp.replace(self.state)
        self.version += 1
        self.cond.notify_all()

    def snapshot(self):
        with self.cond:
            self._prune()
            return self.version, list(self.items)

    def wait(self, version, timeout):
        with self.cond:
            self.cond.wait_for(lambda: self.version != version, timeout)
            return self.version

    def add_text(self, text, origin):
        item = {"id": uuid.uuid4().hex[:12], "type": "text", "text": text, "ts": time.time(), **origin}
        with self.cond:
            self.items.insert(0, item)
            self._changed()
        return item

    def free_path(self, name):
        """~/Drop/nom, ou « nom (2).ext », « nom (3).ext »… si déjà pris."""
        p = self.dir / name
        stem, suffix = p.stem, p.suffix
        n = 2
        while p.exists():
            p = self.dir / f"{stem} ({n}){suffix}"
            n += 1
        return p

    def add_file(self, name, stream, length, origin):
        dest = self.free_path(safe_name(name))
        part = dest.with_name(f".{dest.name}.part")
        left = length
        try:
            with open(part, "wb") as f:
                while left > 0:
                    chunk = stream.read(min(CHUNK, left))
                    if not chunk:
                        raise ConnectionError("upload interrompu")
                    f.write(chunk)
                    left -= len(chunk)
            with self.cond:                   # nom définitif choisi sous verrou : pas de collision
                dest = self.free_path(dest.name)
                part.rename(dest)
                item = {"id": uuid.uuid4().hex[:12], "type": "file", "file": dest.name,
                        "size": length, "ts": time.time(), **origin}
                self.items.insert(0, item)
                self._changed()
            return item
        finally:
            part.unlink(missing_ok=True)

    def get(self, item_id):
        with self.cond:
            return next((i for i in self.items if i["id"] == item_id), None)

    def delete(self, item_id):
        with self.cond:
            item = next((i for i in self.items if i["id"] == item_id), None)
            if not item:
                return False
            self.items.remove(item)
            if item["type"] == "file":
                (self.dir / item["file"]).unlink(missing_ok=True)
            self._changed()
            return True

    def clear(self):
        with self.cond:
            for i in self.items:
                if i["type"] == "file":
                    (self.dir / i["file"]).unlink(missing_ok=True)
            self.items = []
            self._changed()


# ── Notifications (uniquement pour ce qui vient d'un autre appareil) ──

def lang():
    try:
        return (STATE_DIR / "lang").read_text().strip()
    except OSError:
        return os.environ.get("DESK_LANG", "en")


def notify_received(item, path=None):
    if os.environ.get("DESK_DROP_NOTIFY", "1") == "0" or not shutil.which("notify-send"):
        return
    fr = lang() == "fr"
    who = f'{item["device"]} · {item["ip"]}'
    if item["type"] == "text":
        title = f'{"Texte reçu de" if fr else "Text from"} {who}'
        body = item["text"][:300]
        acts = [("copy", "Copier" if fr else "Copy")]
        icon = "edit-paste-symbolic"
    else:
        title = f'{"Fichier reçu de" if fr else "File from"} {who}'
        body = item["file"]
        acts = [("open", "Ouvrir" if fr else "Open"), ("folder", "Dossier" if fr else "Folder")]
        icon = str(path) if path and path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif") else "document-save-symbolic"

    def run():
        cmd = ["notify-send", "-a", "desk", "-i", icon]
        for a, label in acts:
            cmd += ["-A", f"{a}={label}"]
        try:
            choice = subprocess.run(cmd + [title, body], capture_output=True, text=True, timeout=3600).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return
        if choice == "copy":
            subprocess.run(["wl-copy"], input=item["text"], text=True)
        elif choice == "open":
            subprocess.Popen(["xdg-open", str(path)], start_new_session=True)
        elif choice == "folder":
            subprocess.Popen(["xdg-open", str(path.parent)], start_new_session=True)

    threading.Thread(target=run, daemon=True).start()


# ── HTTP ─────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    server_version = "desk-drop"
    protocol_version = "HTTP/1.1"
    store: Store = None
    local_ips: set = set()

    def log_message(self, fmt, *args):
        if os.environ.get("DESK_DROP_QUIET") != "1":
            sys.stderr.write(f"{self.client_address[0]} {fmt % args}\n")

    # réponses
    def send_json(self, obj, status=HTTPStatus.OK):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def error(self, status, msg):
        self.send_json({"error": msg}, status)

    def origin(self):
        ip = self.client_address[0]
        local = ip in self.local_ips or ipaddress.ip_address(ip).is_loopback
        return {"ip": ip, "device": "Ce PC" if local and lang() == "fr" else "This PC" if local
                else device_name(self.headers.get("User-Agent")), "local": local}

    def body_length(self):
        try:
            n = int(self.headers.get("Content-Length", ""))
        except ValueError:
            n = -1
        if n < 0:
            self.error(HTTPStatus.LENGTH_REQUIRED, "Content-Length requis")
        return n

    # routes
    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            body = (HERE / "index.html").read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        elif u.path == "/api/items":
            _, items = self.store.snapshot()
            self.send_json({"items": items, "url": url(self.server.server_port), "lang": lang()})
        elif u.path == "/api/events":
            self.events()
        elif u.path.startswith("/f/"):
            self.download(u.path[3:].split("/")[0], "dl" in parse_qs(u.query))
        else:
            self.error(HTTPStatus.NOT_FOUND, "introuvable")

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/text":
            n = self.body_length()
            if n < 0:
                return
            try:
                text = json.loads(self.rfile.read(n))["text"]
            except (ValueError, KeyError, TypeError):
                return self.error(HTTPStatus.BAD_REQUEST, "JSON {\"text\": …} attendu")
            if not isinstance(text, str) or not text.strip():
                return self.error(HTTPStatus.BAD_REQUEST, "texte vide")
            item = self.store.add_text(text, self.origin())
            self.send_json(item, HTTPStatus.CREATED)
            if not item["local"]:
                notify_received(item)
        elif path == "/api/upload":
            n = self.body_length()
            if n < 0:
                return
            name = self.headers.get("X-Filename", "")
            try:
                item = self.store.add_file(name, self.rfile, n, self.origin())
            except ConnectionError:
                self.close_connection = True
                return
            self.send_json(item, HTTPStatus.CREATED)
            if not item["local"]:
                notify_received(item, self.store.dir / item["file"])
        elif path == "/api/clear":
            self.store.clear()
            self.send_json({"ok": True})
        else:
            self.error(HTTPStatus.NOT_FOUND, "introuvable")

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith("/api/items/") and self.store.delete(path.rsplit("/", 1)[1]):
            self.send_json({"ok": True})
        else:
            self.error(HTTPStatus.NOT_FOUND, "introuvable")

    def download(self, item_id, attachment):
        item = self.store.get(item_id)
        if not item or item["type"] != "file":
            return self.error(HTTPStatus.NOT_FOUND, "introuvable")
        p = self.store.dir / item["file"]
        try:
            f = open(p, "rb")
        except OSError:
            return self.error(HTTPStatus.NOT_FOUND, "fichier supprimé")
        with f:
            ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            disp = "attachment" if attachment else "inline"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(os.fstat(f.fileno()).st_size))
            self.send_header("Content-Disposition", f"{disp}; filename*=UTF-8''{quote(p.name)}")
            self.send_header("X-Content-Type-Options", "nosniff")
            if ctype in ("text/html", "image/svg+xml", "application/xhtml+xml"):
                self.send_header("Content-Security-Policy", "sandbox")   # pas de script depuis un fichier reçu
            self.end_headers()
            shutil.copyfileobj(f, self.wfile, CHUNK)

    def events(self):
        """Server-Sent Events : un événement « items » à chaque changement du fil."""
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        version = -1
        try:
            while True:
                v, items = self.store.snapshot()
                if v != version:
                    version = v
                    self.wfile.write(f"event: items\ndata: {json.dumps(items, ensure_ascii=False)}\n\n".encode())
                else:
                    self.wfile.write(b": ping\n\n")
                self.wfile.flush()
                self.store.wait(version, 15)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass


def make_server(port=PORT, files_dir=None, state_file=None, host="0.0.0.0"):
    files_dir = files_dir or os.environ.get("DESK_DROP_DIR", str(Path.home() / "Drop"))
    state_file = state_file or STATE_DIR / "drop.json"

    class H(Handler):
        pass

    H.store = Store(files_dir, state_file)
    H.local_ips = set(lan_ips())
    srv = ThreadingHTTPServer((host, port), H)
    srv.daemon_threads = True
    return srv


def main():
    if "--url" in sys.argv:
        print(url())
        return
    srv = make_server()
    print(f"desk drop · {url()} · {srv.RequestHandlerClass.store.dir}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
