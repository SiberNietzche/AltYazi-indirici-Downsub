"""İndirme klasöründeki altyazı dosyalarını listeleme, gizleme ve Geri Dönüşüm Kutusu'na taşıma."""

from __future__ import annotations

import ctypes
import json
import os
import threading
from ctypes import wintypes
from pathlib import Path
from typing import Callable

from .engine import EngineError

# Yalnızca altyazıya özgü uzantılar otomatik listelenir. TXT gibi genel uzantılı dosyalar,
# ancak bu program yazdıysa listeye girer; böylece kullanıcının başka dosyaları etkilenmez.
SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".json3", ".ttml", ".dfxp", ".srv1", ".srv2", ".srv3", ".ass", ".ssa"}
MAX_FILES = 2000


class _SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", wintypes.WORD),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", wintypes.LPVOID),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


def move_to_trash(path: str) -> bool:
    """Dosyayı Geri Dönüşüm Kutusu'na taşır; başarılıysa True döndürür."""
    fo_delete = 3
    flags = 0x0040 | 0x0010 | 0x0004 | 0x0400  # ALLOWUNDO, NOCONFIRMATION, SILENT, NOERRORUI
    operation = _SHFILEOPSTRUCTW(None, fo_delete, path + "\0", None, flags, False, None, None)
    result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(operation))
    return result == 0 and not operation.fAnyOperationsAborted and not os.path.exists(path)


def _key(path: str | Path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


class Library:
    def __init__(self, state_path: Path, trash: Callable[[str], bool] = move_to_trash) -> None:
        self._state_path = state_path
        self._trash = trash
        self._lock = threading.RLock()
        self._written: set[str] = set()
        self._hidden: set[str] = set()
        try:
            state = json.loads(state_path.read_text("utf-8"))
            self._written = {_key(p) for p in state.get("written", []) if isinstance(p, str)}
            self._hidden = {_key(p) for p in state.get("hidden", []) if isinstance(p, str)}
        except (OSError, ValueError, AttributeError):
            pass

    def _save(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"written": sorted(self._written), "hidden": sorted(self._hidden)}
        self._state_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")

    def record_written(self, path: str | Path) -> None:
        with self._lock:
            key = _key(path)
            self._written.add(key)
            self._hidden.discard(key)
            self._save()

    def _scan(self, directory: Path) -> list[Path]:
        """Klasörü ve oynatma listesi alt klasörlerini (bir seviye) tarar. Bağlantıları izlemez."""
        found: list[Path] = []
        folders = [directory]
        try:
            with os.scandir(directory) as entries:
                folders += [Path(e.path) for e in entries if e.is_dir(follow_symlinks=False)]
        except OSError:
            return []
        for folder in folders:
            try:
                with os.scandir(folder) as entries:
                    for entry in entries:
                        if len(found) >= MAX_FILES:
                            return found
                        if not entry.is_file(follow_symlinks=False):
                            continue
                        known = Path(entry.name).suffix.lower() in SUBTITLE_EXTENSIONS
                        if known or _key(entry.path) in self._written:
                            found.append(Path(entry.path))
            except OSError:
                continue
        return found

    def listing(self, directory: Path) -> dict:
        with self._lock:
            scanned = self._scan(directory)
            items = []
            hidden_count = 0
            for path in scanned:
                if _key(path) in self._hidden:
                    hidden_count += 1
                    continue
                try:
                    info = path.stat()
                except OSError:
                    continue
                folder = "" if path.parent == directory else path.parent.name
                items.append({"path": str(path), "name": path.name, "folder": folder, "size": info.st_size, "modified": info.st_mtime})
            items.sort(key=lambda item: item["modified"], reverse=True)
            return {"files": items, "hidden": hidden_count}

    def _resolve(self, directory: Path, paths: list) -> list[Path]:
        """İstemciden gelen yolları yalnızca taramada bulunan dosyalarla eşleştirir."""
        available = {_key(path): path for path in self._scan(directory)}
        resolved = []
        for raw in paths:
            path = available.get(_key(raw)) if isinstance(raw, str) else None
            if path is None:
                raise EngineError("not_listed")
            resolved.append(path)
        return resolved

    def contains(self, directory: Path, raw: str) -> bool:
        with self._lock:
            return any(_key(path) == _key(raw) for path in self._scan(directory))

    def hide(self, directory: Path, paths: list) -> int:
        with self._lock:
            resolved = self._resolve(directory, paths)
            self._hidden.update(_key(path) for path in resolved)
            self._save()
            return len(resolved)

    def restore(self, directory: Path) -> None:
        with self._lock:
            visible_root = {_key(path) for path in self._scan(directory)}
            self._hidden -= visible_root
            self._save()

    def delete(self, directory: Path, paths: list) -> dict:
        with self._lock:
            resolved = self._resolve(directory, paths)
            deleted = 0
            failed = []
            for path in resolved:
                if self._trash(str(path)):
                    deleted += 1
                    self._written.discard(_key(path))
                    self._hidden.discard(_key(path))
                    if path.parent != directory:
                        try:
                            path.parent.rmdir()  # Yalnızca boşalmış liste klasörü kaldırılır
                        except OSError:
                            pass
                else:
                    failed.append(path.name)
            self._save()
            return {"deleted": deleted, "failed": failed}
