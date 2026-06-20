"""
Minimal HTTP API server.

This uses only the Python standard library so the current project can expose
the MVP endpoints without introducing framework setup yet.
"""

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .api import ApiError, ShogiDbApi
from .game_repository import GameRepository


class ShogiDbRequestHandler(BaseHTTPRequestHandler):
    api: ShogiDbApi
    static_root: Path

    def do_POST(self) -> None:
        if self.path != "/api/games/import":
            self._send_json({"error": "Not found"}, 404)
            return

        try:
            payload = self._read_json()
            kif_text = payload.get("kif")
            if not isinstance(kif_text, str):
                raise ApiError("Request body must contain string field: kif", 400)
            self._send_json(self.api.import_game(kif_text), 201)
        except ApiError as exc:
            self._send_json({"error": exc.message}, exc.status_code)
        except Exception as exc:
            self._send_json({"error": str(exc)}, 500)

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        try:
            if path == "/" or path.startswith("/assets/") or self._is_frontend_route(path):
                self._send_static(path)
                return

            if path == "/api/games":
                self._send_json(self.api.list_games(), 200)
                return

            if path == "/api/stats/strategies":
                self._send_json(self.api.get_strategy_stats(), 200)
                return

            if path == "/api/stats/enclosures":
                self._send_json(self.api.get_enclosure_stats(), 200)
                return

            parts = path.strip("/").split("/")
            if (
                len(parts) == 4
                and parts[0] == "api"
                and parts[1] == "games"
                and parts[3] == "positions"
            ):
                self._send_json(self.api.get_positions(int(parts[2])), 200)
                return

            self._send_json({"error": "Not found"}, 404)
        except ValueError:
            self._send_json({"error": "Invalid game id"}, 400)
        except ApiError as exc:
            self._send_json({"error": exc.message}, exc.status_code)
        except Exception as exc:
            self._send_json({"error": str(exc)}, 500)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")
        if not raw_body:
            return {}
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise ApiError("Invalid JSON body", 400) from exc
        if not isinstance(payload, dict):
            raise ApiError("JSON body must be an object", 400)
        return payload

    def _send_json(self, payload: dict, status_code: int) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, path: str) -> None:
        relative_path = "index.html" if path == "/" or self._is_frontend_route(path) else path.removeprefix("/")
        file_path = (self.static_root / relative_path).resolve()
        static_root = self.static_root.resolve()

        if not file_path.is_file() or static_root not in file_path.parents:
            self._send_json({"error": "Not found"}, 404)
            return

        content = file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _is_frontend_route(self, path: str) -> bool:
        parts = path.strip("/").split("/")
        return len(parts) == 2 and parts[0] == "games" and parts[1].isdigit()


def create_server(
    db_path: str | Path = "shogi.db",
    host: str = "127.0.0.1",
    port: int = 8000,
    static_root: str | Path | None = None,
) -> ThreadingHTTPServer:
    repository = GameRepository(db_path)
    api = ShogiDbApi(repository)
    root = Path(static_root) if static_root is not None else Path(__file__).resolve().parent.parent / "frontend"

    class Handler(ShogiDbRequestHandler):
        pass

    Handler.api = api
    Handler.static_root = root
    return ThreadingHTTPServer((host, port), Handler)


if __name__ == "__main__":
    server = create_server()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
