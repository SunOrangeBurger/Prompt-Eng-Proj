"""Loopback-only HTTP dashboard; no framework or build step."""
import json
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .demo import DEMO_LOCK, PROJECT, DemoController, reset_demo, view
from .model import SYSTEM_PROMPT

ASSETS = Path(__file__).parent / "frontend"


def make_server(controller: DemoController, port: int) -> ThreadingHTTPServer:
    token = secrets.token_urlsafe(24)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

        def local(self) -> bool:
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            return self.headers.get("Host") in allowed

        def send(self, status: int, data: bytes, mime: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def json(self, status: int, data: Any) -> None:
            self.send(status, json.dumps(data).encode(), "application/json; charset=utf-8")

        def do_GET(self) -> None:
            if not self.local():
                self.json(403, {"error": "Loopback host required"})
                return
            if self.path == "/api/state":
                self.json(200, {**controller.snapshot(), "token": token, "system_prompt": SYSTEM_PROMPT})
                return
            assets = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
                      "/style.css": ("style.css", "text/css")}
            if self.path not in assets:
                self.json(404, {"error": "Not found"})
                return
            name, mime = assets[self.path]
            self.send(200, (ASSETS / name).read_bytes(), mime + "; charset=utf-8")

        def do_POST(self) -> None:
            origin = self.headers.get("Origin")
            valid_origins = {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}
            if not self.local() or self.headers.get("X-Demo-Token") != token or (origin and origin not in valid_origins):
                self.json(403, {"error": "Invalid local request"})
                return
            if self.path == "/api/run":
                self.json(202 if controller.start() else 409, {"status": controller.snapshot()["status"]})
            elif self.path == "/api/reset":
                if not DEMO_LOCK.acquire(blocking=False):
                    self.json(409, {"error": "A demo is already running"})
                    return
                try:
                    root = reset_demo(controller.project)
                    with controller.lock:
                        controller.state.update({"status": "ready", "events": [], **view(root)})
                        controller.state.pop("summary", None)
                    self.json(200, {"status": "ready"})
                finally:
                    DEMO_LOCK.release()
            else:
                self.json(404, {"error": "Not found"})
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(model: str, attempts: int, port: int, open_browser: bool, autostart: bool) -> None:
    if not 1 <= attempts <= 3:
        raise ValueError("Attempts must be between 1 and 3")
    # Bind before resetting: a second launcher must not reset an active demo.
    controller = DemoController(model, attempts)
    server = make_server(controller, port)
    try:
        with DEMO_LOCK:
            reset_demo()
            with controller.lock:
                controller.state.update(view(PROJECT / "demo"))
        url = f"http://127.0.0.1:{server.server_port}"
        print(f"Demo reset. Dashboard: {url}\nModel: {model}\nCtrl+C to stop.", flush=True)
        if open_browser:
            webbrowser.open(url)
        if autostart:
            controller.start()
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        server.server_close()
