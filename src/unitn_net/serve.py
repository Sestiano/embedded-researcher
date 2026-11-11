"""Step `serve`: a small read-only web server for the interface, plus a local-only 1-click build trigger.

Serves ONLY the files of `web/` and `data/processed/graph.json` (plus `graph_alt.json` when present): raw downloads,
interim tables and reports are never reachable, unlike with `python -m http.server` run from the project root.
Binds to 127.0.0.1 unless `--host` says otherwise.
"""

from __future__ import annotations

import importlib
import json
import logging
import threading
import types
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from . import config

log = logging.getLogger(__name__)
WEB = config.ROOT / "web"

_build_lock = threading.Lock()
_build_state: dict = {
    "building": False,
    "current_step": "",
    "step_index": 0,
    "total_steps": 0,
    "logs": [],
    "error": None,
}


class _RingLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        with _build_lock:
            _build_state["logs"].append(msg)
            if len(_build_state["logs"]) > 40:
                _build_state["logs"] = _build_state["logs"][-40:]


def _run_pipeline_bg(include_alt: bool) -> None:
    from .__main__ import STEPS, build_plan

    ring = _RingLogHandler()
    ring.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S"))
    root_log = logging.getLogger("unitn_net")
    root_log.addHandler(ring)
    try:
        cfg = config.load()
        plan = build_plan(cfg, include_alt=include_alt)
        with _build_lock:
            _build_state.update(building=True, current_step="init", step_index=0, total_steps=len(plan), logs=[], error=None)
        for idx, (step, is_alt) in enumerate(plan, 1):
            label = f"{step} (--alt)" if is_alt else step
            with _build_lock:
                _build_state.update(current_step=label, step_index=idx)
            root_log.info("=== [%d/%d] %s", idx, len(plan), label)
            module = importlib.import_module(f"unitn_net.{STEPS[step]}")
            module.run(cfg, types.SimpleNamespace(alt=is_alt))
        with _build_lock:
            _build_state.update(building=False, current_step="done")
    except BaseException as exc:
        log.exception("pipeline build failed")
        with _build_lock:
            _build_state.update(building=False, error=str(exc))
    finally:
        root_log.removeHandler(ring)


class Handler(SimpleHTTPRequestHandler):
    # Set by run() when listening on loopback: requests naming any other host are refused. Without it, a web page opened in the
    # same browser could point its own domain at 127.0.0.1 ("DNS rebinding") and read graph.json, i.e. names of real people.
    allowed_hosts: frozenset[str] | None = None

    def _is_loopback_client(self) -> bool:
        return self.client_address[0] in ("127.0.0.1", "::1", "::ffff:127.0.0.1")

    def _send_json(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def parse_request(self) -> bool:
        if not super().parse_request():
            return False
        if self.allowed_hosts is not None and (self.headers.get("Host") or "").lower() not in self.allowed_hosts:
            self.send_error(403, "unexpected Host header")
            return False
        return True

    def do_GET(self) -> None:
        clean = self.path.split("?", 1)[0].split("#", 1)[0]
        if clean == "/api/status":
            if not self._is_loopback_client():
                self.send_error(403)
                return
            with _build_lock:
                st = dict(_build_state, ok=True, logs=list(_build_state["logs"]))
            st["has_graph"] = (config.PROCESSED / "graph.json").exists()
            st["has_alt"] = (config.PROCESSED / "graph_alt.json").exists()
            self._send_json(200, st)
            return
        super().do_GET()

    def do_POST(self) -> None:
        clean = self.path.split("?", 1)[0].split("#", 1)[0]
        if clean != "/api/build":
            self.send_error(404)
            return
        if not self._is_loopback_client() or self.headers.get("X-Unitn-Net") != "1":
            self.send_error(403, "local build requires loopback and X-Unitn-Net header")
            return
        length = min(int(self.headers.get("Content-Length") or 0), 4096)
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}
        include_alt = bool(body.get("alt", False))
        with _build_lock:
            if _build_state["building"]:
                self._send_json(409, {"error": "build already running"})
                return
            _build_state["building"] = True
        threading.Thread(target=_run_pipeline_bg, args=(include_alt,), daemon=True).start()
        self._send_json(202, {"started": True, "alt": include_alt})

    def translate_path(self, path: str) -> str:
        clean = path.split("?", 1)[0].split("#", 1)[0]
        if clean == "/graph.json":
            return str(config.PROCESSED / "graph.json")
        if clean == "/graph_alt.json":
            return str(config.PROCESSED / "graph_alt.json")
        if clean == "/logoER.jpg":
            return str(config.ROOT / "logoER.jpg")
        return super().translate_path(path)          # resolved inside `directory` (web/); ".." is stripped by the base class

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache")     # a new `export` shows up on reload
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def list_directory(self, path):                        # no directory listings
        self.send_error(404)
        return None

    def log_message(self, fmt: str, *args) -> None:
        log.debug("%s %s", self.address_string(), fmt % args)


def run(cfg: dict, args=None) -> None:
    host, port = getattr(args, "host", None) or "127.0.0.1", getattr(args, "port", None) or 8000
    if not (config.PROCESSED / "graph.json").exists():
        log.warning("data/processed/graph.json is missing: run the pipeline up to `export` first")
    if host in ("127.0.0.1", "localhost", "::1"):
        Handler.allowed_hosts = frozenset(f"{h}:{port}" for h in ("127.0.0.1", "localhost", "[::1]"))
    else:
        log.warning("listening on %s: the page (names and inferred affinities of real people) is reachable from other machines", host)
    with ThreadingHTTPServer((host, port), partial(Handler, directory=str(WEB))) as httpd:
        log.info("serving the interface at http://%s:%d/  (Ctrl+C to stop)", host, port)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
