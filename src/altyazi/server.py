"""Arayüze yalnızca yerel makineden hizmet veren HTTP sunucusu."""

from __future__ import annotations

import json
import mimetypes
import os
import secrets
import socketserver
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from . import __version__
from . import release, system, updater
from .engine import Engine, EngineError, JobManager
from .library import Library

MAX_BODY = 5 * 1024 * 1024
ALLOWED_FORMATS = {"srt", "vtt", "txt", "timed", "raw"}
THEMES = {"ocean", "emerald", "amethyst", "rose", "amber", "graphite", "midnight", "forest", "wine"}
LOCALES = {"tr", "ku", "en"}


def web_root() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "altyazi" / "web"


def app_data_dir() -> Path:
    return system.data_dir()


class Settings:
    def __init__(self) -> None:
        self._path = app_data_dir() / "settings.json"
        self._lock = threading.Lock()
        self.data = {
            "download_dir": str(system.default_download_dir()), "theme": "ocean", "locale": "tr",
            "auto_update": True, "update_notice": True,
        }
        try:
            saved = json.loads(self._path.read_text("utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(saved, dict):
            return
        if isinstance(saved.get("download_dir"), str):
            self.data["download_dir"] = saved["download_dir"]
        if saved.get("locale") in LOCALES:
            self.data["locale"] = saved["locale"]
        if saved.get("theme") in THEMES:
            self.data["theme"] = saved["theme"]
        elif saved.get("dark"):  # Eski sürümün koyu tema tercihi korunur
            self.data["theme"] = "graphite"
        for key in ("auto_update", "update_notice"):
            if isinstance(saved.get(key), bool):
                self.data[key] = saved[key]

    def update(self, values: dict) -> dict:
        with self._lock:
            if "download_dir" in values:
                directory = Path(str(values["download_dir"]))
                if not directory.is_absolute():
                    raise EngineError("relative_folder")
                self.data["download_dir"] = str(directory)
            if "theme" in values:
                if values["theme"] not in THEMES:
                    raise EngineError("unknown_theme")
                self.data["theme"] = values["theme"]
            if "locale" in values:
                if values["locale"] not in LOCALES:
                    raise EngineError("unknown_locale")
                self.data["locale"] = values["locale"]
            for key in ("auto_update", "update_notice"):
                if key in values:
                    if not isinstance(values[key], bool):
                        raise EngineError("invalid_request")
                    self.data[key] = values[key]
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), "utf-8")
            return dict(self.data)

    @property
    def directory(self) -> Path:
        return Path(self.data["download_dir"])


class AppContext:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or secrets.token_urlsafe(32)
        self.engine = Engine()
        self.library = Library(app_data_dir() / "files.json")
        self.jobs = JobManager(self.engine, on_saved=self.library.record_written)
        self.settings = Settings()


class Handler(BaseHTTPRequestHandler):
    server_version = "AltyaziIndirici"
    sys_version = ""
    context: AppContext

    def log_message(self, *args) -> None:
        pass

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload, status: int = 200) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _host_ok(self) -> bool:
        host = self.headers.get("Host", "")
        return host == f"127.0.0.1:{self.server.server_address[1]}"

    def _authorized(self) -> bool:
        return secrets.compare_digest(self.headers.get("X-App-Token", ""), self.context.token)

    def do_GET(self) -> None:
        if not self._host_ok():
            return self._json({"error": "forbidden"}, 403)
        path = urlsplit(self.path).path
        if path.startswith("/api/"):
            return self._api("GET", path, {})
        self._static(path)

    def do_POST(self) -> None:
        if not self._host_ok():
            return self._json({"error": "forbidden"}, 403)
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._json({"error": "bad length"}, 400)
        if not 0 <= length <= MAX_BODY:
            return self._json({"error": "too large"}, 413)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError
        except ValueError:
            return self._json(EngineError("invalid_request").payload(), 400)
        self._api("POST", urlsplit(self.path).path, body)

    def _static(self, path: str) -> None:
        root = web_root().resolve()
        relative = "index.html" if path == "/" else path.lstrip("/")
        target = (root / relative).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            return self._json({"error": "not found"}, 404)
        kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if kind.startswith("text/") or kind.endswith("javascript"):
            kind += "; charset=utf-8"
        self._send(200, target.read_bytes(), kind)

    def _api(self, method: str, path: str, body: dict) -> None:
        if not self._authorized():
            return self._json({"error": "unauthorized"}, 401)
        route = self._ROUTES.get((method, path))
        try:
            if route:
                return self._json(route(self, body))
            if method == "GET" and path.startswith("/api/jobs/"):
                return self._json(self.context.jobs.status(path.rsplit("/", 1)[-1]))
            self._json({"error": "not found"}, 404)
        except EngineError as exc:
            self._json(exc.payload(), 400)
        except OSError as exc:
            self._json(EngineError("file_error", detail=exc.strerror or str(exc)).payload(), 500)
        except Exception as exc:  # Beklenmeyen hata arayüzde görünmeli, sunucuyu düşürmemeli
            self._json(EngineError("unexpected", detail=type(exc).__name__).payload(), 500)

    # Uç noktalar --------------------------------------------------------
    def _settings_get(self, _body: dict) -> dict:
        return {**self.context.settings.data, "version": __version__, "platform": system.PLATFORM}

    def _settings_set(self, body: dict) -> dict:
        return self.context.settings.update(body)

    def _update_status(self, _body: dict) -> dict:
        return updater.status(self.context.settings.data["auto_update"])

    def _update_check(self, _body: dict) -> dict:
        return updater.check(self.context.settings.data["auto_update"], force=True)

    def _app_update(self, _body: dict) -> dict:
        return release.status(self.context.settings.data["update_notice"])

    def _app_update_check(self, _body: dict) -> dict:
        return release.check(self.context.settings.data["update_notice"], force=True)

    def _app_update_dismiss(self, body: dict) -> dict:
        release.dismiss(str(body.get("version", "")))
        return self._app_update(body)

    def _app_update_open(self, _body: dict) -> dict:
        return {"url": release.open_download()}

    def _info(self, body: dict) -> dict:
        return self.context.engine.open(str(body.get("url", "")))

    def _refresh(self, body: dict) -> dict:
        return self.context.engine.refresh(str(body.get("id", "")))

    def _download(self, body: dict) -> dict:
        fmt = str(body.get("format", "srt"))
        if fmt not in ALLOWED_FORMATS:
            raise EngineError("unknown_format")
        path, google = self.context.engine.download(
            str(body.get("id", "")), str(body.get("track", "")), fmt,
            self.context.settings.directory, body.get("second_track") or None,
        )
        self.context.library.record_written(path)
        return {"path": str(path), "name": path.name, "size": path.stat().st_size, "google": google}

    def _playlist(self, body: dict) -> dict:
        urls = body.get("urls")
        fmt = str(body.get("format", "srt"))
        lang = str(body.get("lang", "")).strip()
        second_lang = str(body.get("second_lang") or "").strip() or None
        if not isinstance(urls, list) or not urls or not all(isinstance(u, str) for u in urls):
            raise EngineError("select_video")
        if not lang:
            raise EngineError("need_lang")
        if fmt not in ALLOWED_FORMATS or (second_lang and fmt == "raw"):
            raise EngineError("unknown_format")
        if second_lang and second_lang.lower() == lang.lower():
            raise EngineError("same_language")
        job = self.context.jobs.start(
            str(body.get("title", "")), urls, lang, fmt, bool(body.get("allow_auto", True)),
            self.context.settings.directory, second_lang,
        )
        return {"job": job}

    def _cancel(self, body: dict) -> dict:
        self.context.jobs.cancel(str(body.get("job", "")))
        return {"ok": True}

    def _reveal(self, body: dict) -> dict:
        requested = body.get("path")
        directory = self.context.settings.directory
        if isinstance(requested, str) and self.context.library.contains(directory, requested):
            system.reveal(Path(requested))
        else:
            system.reveal(directory)
        return {"ok": True}

    def _files(self, _body: dict) -> dict:
        return self.context.library.listing(self.context.settings.directory)

    def _paths(self, body: dict) -> list:
        paths = body.get("paths")
        if not isinstance(paths, list) or not paths:
            raise EngineError("invalid_request")
        return paths

    def _files_hide(self, body: dict) -> dict:
        directory = self.context.settings.directory
        return {"hidden": self.context.library.hide(directory, self._paths(body))}

    def _files_restore(self, _body: dict) -> dict:
        self.context.library.restore(self.context.settings.directory)
        return {"ok": True}

    def _files_delete(self, body: dict) -> dict:
        return self.context.library.delete(self.context.settings.directory, self._paths(body))

    _ROUTES = {
        ("GET", "/api/settings"): _settings_get,
        ("POST", "/api/settings"): _settings_set,
        ("GET", "/api/update"): _update_status,
        ("POST", "/api/update/check"): _update_check,
        ("GET", "/api/app-update"): _app_update,
        ("POST", "/api/app-update/check"): _app_update_check,
        ("POST", "/api/app-update/dismiss"): _app_update_dismiss,
        ("POST", "/api/app-update/open"): _app_update_open,
        ("POST", "/api/info"): _info,
        ("POST", "/api/refresh"): _refresh,
        ("POST", "/api/download"): _download,
        ("POST", "/api/playlist"): _playlist,
        ("POST", "/api/cancel"): _cancel,
        ("POST", "/api/reveal"): _reveal,
        ("GET", "/api/files"): _files,
        ("POST", "/api/files/hide"): _files_hide,
        ("POST", "/api/files/restore"): _files_restore,
        ("POST", "/api/files/delete"): _files_delete,
    }


class LocalServer(ThreadingHTTPServer):
    """Yalnızca 127.0.0.1'de dinleyen sunucu.

    ``HTTPServer.server_bind`` adresin tam adını ``socket.getfqdn`` ile sorar. macOS 26'da bu
    sorgu 35-70 saniye sürebiliyor ve sunucu o süre boyunca dinlemeye başlamıyor; kabuk da
    motorun açılmadığını sanıyor. Ad hiçbir yerde kullanılmadığı için sorgu atlanır.
    """

    def server_bind(self) -> None:
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = host
        self.server_port = port


def create_server(context: AppContext, port: int = 0) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"context": context})
    server = LocalServer(("127.0.0.1", port), handler)
    server.daemon_threads = True
    return server
