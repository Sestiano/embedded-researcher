"""The web server must expose the interface and graph.json (and graph_alt.json), and nothing else of the project."""

import threading
import urllib.error
import urllib.request
from functools import partial
from http.server import ThreadingHTTPServer

import pytest

from unitn_net import config, serve


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROCESSED", tmp_path)
    (tmp_path / "graph.json").write_text('{"ok": true}', encoding="utf-8")
    (tmp_path / "graph_alt.json").write_text('{"alt": true}', encoding="utf-8")
    (tmp_path / "edges.parquet").write_text("private", encoding="utf-8")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), partial(serve.Handler, directory=str(serve.WEB)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def _status(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def test_serves_the_page_and_the_graph(base):
    assert _status(base + "/") == 200 and _status(base + "/app.js") == 200
    with urllib.request.urlopen(base + "/graph.json", timeout=5) as r:
        assert r.read() == b'{"ok": true}' and r.headers["Cache-Control"] == "no-cache"
    with urllib.request.urlopen(base + "/graph_alt.json", timeout=5) as r:
        assert r.read() == b'{"alt": true}'


@pytest.mark.parametrize("path", ["/config.toml", "/../config.toml", "/%2e%2e/config.toml", "/edges.parquet", "/../data/interim/people.parquet",
                                  "/vendor/", "/data/processed/graph.json", "/README.md", "/reports/audit.csv"])
def test_nothing_else_is_reachable(base, path):
    assert _status(base + path) == 404


def test_unknown_host_header_is_refused_on_loopback(base, monkeypatch):
    port = base.rsplit(":", 1)[1]
    monkeypatch.setattr(serve.Handler, "allowed_hosts", frozenset({f"127.0.0.1:{port}"}))
    assert _status(base + "/graph.json") == 200
    req = urllib.request.Request(base + "/graph.json", headers={"Host": f"evil.example:{port}"})
    try:
        urllib.request.urlopen(req, timeout=5)
        status = 200
    except urllib.error.HTTPError as e:
        status = e.code
    assert status == 403


def test_api_status_and_csrf_protection(base):
    import json
    with urllib.request.urlopen(base + "/api/status", timeout=5) as r:
        assert r.status == 200
        payload = json.loads(r.read().decode("utf-8"))
        assert payload["ok"] is True and payload["has_graph"] is True and payload["has_alt"] is True
    # POST /api/build without X-Unitn-Net: 1 header must be rejected with 403
    req = urllib.request.Request(base + "/api/build", data=b"{}", method="POST")
    try:
        urllib.request.urlopen(req, timeout=5)
        status = 200
    except urllib.error.HTTPError as e:
        status = e.code
    assert status == 403
