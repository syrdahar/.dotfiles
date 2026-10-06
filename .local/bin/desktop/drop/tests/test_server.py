# Tests du serveur desk drop : cd ~/.local/bin/desktop && python3 -m pytest drop/tests -q
import http.client
import json
import os
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DESK_DROP_NOTIFY"] = "0"
os.environ["DESK_DROP_QUIET"] = "1"
import server  # noqa: E402


@pytest.fixture
def srv(tmp_path):
    s = server.make_server(port=0, files_dir=tmp_path / "Drop", state_file=tmp_path / "drop.json", host="127.0.0.1")
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield s
    s.shutdown()
    s.server_close()


def req(srv, method, path, body=None, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=5)
    c.request(method, path, body=body, headers=headers or {})
    r = c.getresponse()
    data = r.read()
    c.close()
    return r, data


def items(srv):
    return json.loads(req(srv, "GET", "/api/items")[1])["items"]


def test_index_served(srv):
    r, data = req(srv, "GET", "/")
    assert r.status == 200 and b"<title>Drop</title>" in data


def test_text_roundtrip(srv):
    r, data = req(srv, "POST", "/api/text", json.dumps({"text": "héllo\nmonde"}), {"Content-Type": "application/json"})
    assert r.status == 201
    it = items(srv)
    assert len(it) == 1 and it[0]["text"] == "héllo\nmonde" and it[0]["local"] is True


def test_empty_text_rejected(srv):
    assert req(srv, "POST", "/api/text", json.dumps({"text": "  "}))[0].status == 400
    assert req(srv, "POST", "/api/text", "pas du json")[0].status == 400


def test_upload_download_delete(srv, tmp_path):
    payload = os.urandom(3 * 1024 * 1024 + 17)
    r, data = req(srv, "POST", "/api/upload", payload, {"X-Filename": "photo%20%C3%A9t%C3%A9.jpg"})
    assert r.status == 201
    item = json.loads(data)
    assert item["file"] == "photo été.jpg" and item["size"] == len(payload)
    assert (tmp_path / "Drop" / "photo été.jpg").read_bytes() == payload

    r, data = req(srv, "GET", f"/f/{item['id']}?dl=1")
    assert r.status == 200 and data == payload
    assert r.getheader("Content-Disposition").startswith("attachment;")

    assert req(srv, "DELETE", f"/api/items/{item['id']}")[0].status == 200
    assert not (tmp_path / "Drop" / "photo été.jpg").exists()
    assert items(srv) == []


def test_name_collision_and_traversal(srv, tmp_path):
    for _ in range(2):
        req(srv, "POST", "/api/upload", b"x", {"X-Filename": "..%2F..%2Fetc%2Fpasswd"})
    names = sorted(p.name for p in (tmp_path / "Drop").iterdir())
    assert names == ["passwd", "passwd (2)"]
    assert not (tmp_path / "etc").exists()


def test_html_file_is_sandboxed(srv):
    item = json.loads(req(srv, "POST", "/api/upload", b"<script>alert(1)</script>", {"X-Filename": "x.html"})[1])
    r, _ = req(srv, "GET", f"/f/{item['id']}")
    assert r.getheader("Content-Security-Policy") == "sandbox"


def test_clear(srv, tmp_path):
    req(srv, "POST", "/api/text", json.dumps({"text": "a"}))
    req(srv, "POST", "/api/upload", b"b", {"X-Filename": "b.txt"})
    assert req(srv, "POST", "/api/clear")[0].status == 200
    assert items(srv) == [] and list((tmp_path / "Drop").iterdir()) == []


def test_unknown_routes(srv):
    assert req(srv, "GET", "/f/nope")[0].status == 404
    assert req(srv, "DELETE", "/api/items/nope")[0].status == 404


def test_events_push_changes(srv):
    c = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=5)
    c.request("GET", "/api/events")
    r = c.getresponse()

    def next_event():
        lines = []
        while (line := r.fp.readline().decode()) != "\n":
            lines.append(line)
        return lines

    assert next_event()[0] == "event: items\n"           # état initial
    req(srv, "POST", "/api/text", json.dumps({"text": "live"}))
    ev = next_event()
    assert json.loads(ev[1][len("data: "):])[0]["text"] == "live"
    c.close()


def test_state_persists(tmp_path):
    s1 = server.Store(tmp_path / "Drop", tmp_path / "drop.json")
    s1.add_text("reste là", {"ip": "1.2.3.4", "device": "Android", "local": False})
    s2 = server.Store(tmp_path / "Drop", tmp_path / "drop.json")
    assert s2.snapshot()[1][0]["text"] == "reste là"


def test_device_name():
    assert server.device_name("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)") == "iPhone"
    assert server.device_name("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") == "Windows"
    assert server.device_name("Mozilla/5.0 (Linux; Android 14)") == "Android"


def test_lan_ips_skip_vpn():
    ips = server.lan_ips()
    assert "10.5.0.2" not in ips and "127.0.0.1" not in ips
