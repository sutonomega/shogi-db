"""
Minimal HTTP API server.

This uses only the Python standard library so the current project can expose
the MVP endpoints without introducing framework setup yet.
"""

import json
import mimetypes
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .api import ApiError, ShogiDbApi
from .kif_encoding import KifEncodingError
from .game_repository import GameRepository


class ShogiDbRequestHandler(BaseHTTPRequestHandler):
    api: ShogiDbApi
    import_jobs: "DirectoryImportJobStore"
    static_root: Path

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in ("/api/games/import", "/api/games/import-directory"):
            self._send_json({"error": "Not found"}, 404)
            return

        try:
            parts = path.strip("/").split("/")
            if (
                len(parts) == 6
                and parts[0] == "api"
                and parts[1] == "games"
                and parts[2] == "import-directory"
                and parts[3] == "jobs"
                and parts[5] == "cancel"
            ):
                self._send_json(self.import_jobs.cancel(parts[4]), 200)
                return

            if path == "/api/games/import-directory":
                payload, status_code = self._import_directory_from_request()
                self._send_json(payload, status_code)
            else:
                self._send_json(self._import_game_from_request(), 201)
        except ApiError as exc:
            self._send_json({"error": exc.message}, exc.status_code)
        except KifEncodingError as exc:
            self._send_json({"error": str(exc)}, 400)
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

            if path == "/api/stats/blunders":
                self._send_json(self.api.get_blunders(), 200)
                return

            parts = path.strip("/").split("/")
            if (
                len(parts) == 5
                and parts[0] == "api"
                and parts[1] == "games"
                and parts[2] == "import-directory"
                and parts[3] == "jobs"
            ):
                self._send_json(self.import_jobs.get(parts[4]), 200)
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

    def _import_game_from_request(self) -> dict:
        raw_body = self._read_body()
        content_type = self.headers.get("Content-Type", "")
        return import_game_payload(self.api, content_type, raw_body)

    def _import_directory_from_request(self) -> tuple[dict, int]:
        raw_body = self._read_body()
        payload = _decode_json_payload(raw_body)
        async_import = payload.get("async", False)
        if not isinstance(async_import, bool):
            raise ApiError("Request body field async must be boolean", 400)
        if async_import:
            return start_import_directory_payload(self.import_jobs, payload), 202
        return import_directory_payload(self.api, payload), 201

    def _read_body(self) -> bytes:
        content_length = int(self.headers.get("Content-Length", "0"))
        return self.rfile.read(content_length)

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
    Handler.import_jobs = DirectoryImportJobStore(api)
    Handler.static_root = root
    return ThreadingHTTPServer((host, port), Handler)


def import_game_payload(api: ShogiDbApi, content_type: str, raw_body: bytes) -> dict:
    if content_type.startswith("application/json"):
        try:
            payload = _decode_json_payload(raw_body)
        except UnicodeDecodeError:
            return api.import_game_bytes(raw_body)
        kif_text = payload.get("kif")
        if not isinstance(kif_text, str):
            raise ApiError("Request body must contain string field: kif", 400)
        return api.import_game(kif_text)
    return api.import_game_bytes(raw_body)


class DirectoryImportJobStore:
    def __init__(self, api: ShogiDbApi) -> None:
        self.api = api
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()

    def start(self, directory_path: str, recursive: bool) -> dict:
        job_id = uuid.uuid4().hex
        job = {
            "id": job_id,
            "status": "queued",
            "path": directory_path,
            "recursive": recursive,
            "total": 0,
            "processed": 0,
            "imported": 0,
            "failed": 0,
            "errors": [],
            "cancel_requested": False,
            "done": False,
        }
        with self._lock:
            self._jobs[job_id] = job
        thread = threading.Thread(
            target=self._run,
            args=(job_id, directory_path, recursive),
            daemon=True,
        )
        thread.start()
        return self.get(job_id)

    def get(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise ApiError(f"Import job not found: {job_id}", 404)
            return dict(job)

    def cancel(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise ApiError(f"Import job not found: {job_id}", 404)
            if not job["done"]:
                job["cancel_requested"] = True
                job["status"] = "canceling"
            return dict(job)

    def _update(self, job_id: str, **changes) -> None:
        with self._lock:
            self._jobs[job_id].update(changes)

    def _run(self, job_id: str, directory_path: str, recursive: bool) -> None:
        self._update(job_id, status="scanning")

        def update_progress(processed: int, total: int) -> None:
            if self._is_cancel_requested(job_id):
                status = "canceling"
            else:
                status = "running"
            self._update(
                job_id,
                status=status,
                processed=processed,
                total=total,
            )

        try:
            result = self.api.import_games_from_directory(
                directory_path,
                recursive=recursive,
                progress_callback=update_progress,
                should_cancel=lambda: self._is_cancel_requested(job_id),
            )
        except Exception as exc:
            self._update(
                job_id,
                status="failed",
                errors=[{"path": directory_path, "error": str(exc)}],
                failed=1,
                done=True,
            )
            return

        if self._is_cancel_requested(job_id):
            self._update(
                job_id,
                status="canceled",
                total=result["total"],
                imported=result["imported"],
                failed=result["failed"],
                errors=result["errors"],
                done=True,
            )
        else:
            self._update(
                job_id,
                status="completed",
                total=result["total"],
                processed=result["total"],
                imported=result["imported"],
                failed=result["failed"],
                errors=result["errors"],
                done=True,
            )

    def _is_cancel_requested(self, job_id: str) -> bool:
        with self._lock:
            return bool(self._jobs[job_id]["cancel_requested"])


def import_directory_payload(api: ShogiDbApi, payload: dict) -> dict:
    directory_path = payload.get("path")
    recursive = payload.get("recursive", False)
    if not isinstance(directory_path, str):
        raise ApiError("Request body must contain string field: path", 400)
    if not isinstance(recursive, bool):
        raise ApiError("Request body field recursive must be boolean", 400)
    return api.import_games_from_directory(
        directory_path,
        recursive=recursive,
    )


def start_import_directory_payload(
    import_jobs: DirectoryImportJobStore,
    payload: dict,
) -> dict:
    directory_path = payload.get("path")
    recursive = payload.get("recursive", False)
    if not isinstance(directory_path, str):
        raise ApiError("Request body must contain string field: path", 400)
    if not isinstance(recursive, bool):
        raise ApiError("Request body field recursive must be boolean", 400)
    return import_jobs.start(directory_path, recursive)


def _decode_json_payload(raw_body: bytes) -> dict:
    raw_text = raw_body.decode("utf-8")
    if not raw_text:
        return {}
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ApiError("Invalid JSON body", 400) from exc
    if not isinstance(payload, dict):
        raise ApiError("JSON body must be an object", 400)
    return payload


if __name__ == "__main__":
    server = create_server()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
