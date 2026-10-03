"""Loopback-only HTTP server; no additional Python dependencies."""

import json
import secrets
import threading
import webbrowser
from functools import partial
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, TypedDict

from domino_game.game.rules import RuleError
from domino_game.patio.session import MoveError, PatioSession

WEB_ROOT = Path(__file__).with_name("web")


class SessionConfig(TypedDict):
    target_score: int
    game_mode: str
    autoplay: bool


class PatioServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port: int, config: SessionConfig):
        super().__init__(("127.0.0.1", port), partial(PatioHandler, directory=str(WEB_ROOT)))
        self.config = config
        self.sessions: dict[str, PatioSession] = {}
        self.lock = threading.Lock()


class PatioHandler(SimpleHTTPRequestHandler):
    server: PatioServer
    # The base class types this as an instance attribute, so a ClassVar would conflict.
    extensions_map: dict[str, str] = {  # noqa: RUF012
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".glb": "model/gltf-binary",
    }

    def _local_request(self) -> bool:
        port = self.server.server_port
        return self.headers.get("Host") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def _json(self, payload: dict[str, Any], status: int = 200, cookie: str = "") -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", f"patio={cookie}; HttpOnly; SameSite=Strict; Path=/")
        self.end_headers()
        self.wfile.write(data)

    def _session(self) -> tuple[PatioSession, str]:
        cookies = SimpleCookie()
        cookies.load(self.headers.get("Cookie", ""))
        token = cookies["patio"].value if "patio" in cookies else ""
        if token in self.server.sessions:
            return self.server.sessions[token], ""
        if len(self.server.sessions) >= 128:
            raise MoveError("Session limit reached. Restart the local server to start another game.")
        token = secrets.token_urlsafe(32)
        session = PatioSession(**self.server.config)
        self.server.sessions[token] = session
        return session, token

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        super().end_headers()

    def do_GET(self) -> None:
        if not self._local_request():
            self._json({"error": "Use the localhost URL printed by the game server."}, 403)
            return
        if self.path == "/api/state":
            with self.server.lock:
                try:
                    session, cookie = self._session()
                    self._json(session.snapshot(), cookie=cookie)
                except MoveError as error:
                    self._json({"error": str(error)}, 400)
        elif self.path.startswith("/api/"):
            self._json({"error": "Unknown game endpoint."}, 404)
        else:
            super().do_GET()

    def do_POST(self) -> None:
        origin = self.headers.get("Origin")
        if not self._local_request() or (origin and origin != f"http://{self.headers.get('Host')}"):
            self._json({"error": "Game actions must originate from the local game page."}, 403)
            return
        if self.headers.get("Content-Type") != "application/json":
            self._json({"error": "Game actions require application/json."}, 415)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 4096:
                raise MoveError("Game action must be a JSON object smaller than 4096 bytes.")
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise MoveError("Game action must be a JSON object.")
        except (ValueError, UnicodeDecodeError) as error:
            self._json({"error": f"Invalid game action: {error}"}, 400)
            return
        with self.server.lock:
            try:
                session, cookie = self._session()
                if self.path == "/api/game":
                    replacement = PatioSession(
                        target_score=payload.get("target", 200),
                        game_mode=payload.get("mode", "target_score"),
                        autoplay=payload.get("autoplay", False),
                    )
                    replacement.revision = session.revision + 1
                    session.__dict__.update(replacement.__dict__)
                else:
                    if type(payload.get("revision")) is not int or payload["revision"] != session.revision:
                        self._json(
                            {"error": "The board changed. Your game has been refreshed.", "state": session.snapshot()}, 409
                        )
                        return
                    if self.path == "/api/move":
                        session.play(payload.get("tile"), payload.get("position"))
                    elif self.path == "/api/pass":
                        session.pass_turn()
                    elif self.path == "/api/step":
                        session.step_cpu()
                    elif self.path == "/api/next":
                        session.next_round()
                    elif self.path == "/api/autoplay":
                        session.set_autoplay(payload.get("enabled"))
                    else:
                        self._json({"error": "Unknown game endpoint."}, 404)
                        return
                self._json(session.snapshot(), cookie=cookie)
            except RuleError as error:
                self._json({"error": str(error)}, 400)

    def log_message(self, format: str, *args: Any) -> None:
        if args and str(args[1]) != "200":
            super().log_message(format, *args)


def serve(
    *,
    port: int = 8000,
    target_score: int = 200,
    game_mode: str = "target_score",
    autoplay: bool = False,
    open_browser: bool = True,
) -> None:
    config = SessionConfig(target_score=target_score, game_mode=game_mode, autoplay=autoplay)
    PatioSession(**config)
    try:
        server = PatioServer(port, config)
    except OSError as error:
        raise MoveError(f"Cannot open the patio on port {port}: {error}. Try --port with another port.") from error
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"El Patio: {url}\nPress Ctrl+C to stop. Games stay in memory until the server stops.", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nPatio closed.")
    finally:
        server.server_close()
