"""İşletim sistemine bağlı işler: klasör yerleri, çöp kutusu ve dosya yöneticisi.

Desteklenen ortamlar: Windows, Linux ve Android. Android'de program bir uygulamanın içinde
çalışır; uygulama klasörleri ``ALTYAZI_DATA_DIR`` ve ``ALTYAZI_DOWNLOAD_DIR`` ortam
değişkenleriyle verir, çöp kutusu ve dosya yöneticisi yoktur.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

from . import APP_DIR_NAME


def platform_name() -> str:
    if hasattr(sys, "getandroidapilevel") or os.environ.get("ALTYAZI_PLATFORM") == "android":
        return "android"
    return "windows" if sys.platform == "win32" else "linux"


PLATFORM = platform_name()
# Dosya yöneticisinde gösterme ve çöp kutusu yalnızca masaüstünde vardır.
CAN_REVEAL = PLATFORM != "android"
HAS_TRASH = PLATFORM != "android"


def data_dir() -> Path:
    """Ayarların ve indirilenler listesinin tutulduğu klasör."""
    override = os.environ.get("ALTYAZI_DATA_DIR")
    if override:
        return Path(override)
    if PLATFORM == "windows":
        return Path(os.environ.get("APPDATA") or Path.home()) / APP_DIR_NAME
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / APP_DIR_NAME


def default_download_dir() -> Path:
    override = os.environ.get("ALTYAZI_DOWNLOAD_DIR")
    if override:
        return Path(override)
    downloads = Path.home() / "Downloads"
    if PLATFORM == "linux":
        # İndirilenler klasörünün adı masaüstü diline göre değişir (ör. "İndirilenler").
        try:
            answer = subprocess.run(["xdg-user-dir", "DOWNLOAD"], capture_output=True, text=True, timeout=5).stdout.strip()
            if answer and Path(answer).is_absolute() and Path(answer) != Path.home():
                downloads = Path(answer)
        except (OSError, subprocess.SubprocessError):
            pass
    return downloads / APP_DIR_NAME


def move_to_trash(path: str) -> bool:
    """Dosyayı çöp kutusuna taşır (Android'de kalıcı olarak siler); başarılıysa True döndürür."""
    if PLATFORM == "windows":
        return _trash_windows(path)
    if PLATFORM == "android":
        try:
            os.remove(path)
        except OSError:
            return False
        return True
    return _trash_linux(path)


def _trash_windows(path: str) -> bool:
    import ctypes
    from ctypes import wintypes

    class Operation(ctypes.Structure):  # SHFILEOPSTRUCTW
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

    fo_delete = 3
    flags = 0x0040 | 0x0010 | 0x0004 | 0x0400  # ALLOWUNDO, NOCONFIRMATION, SILENT, NOERRORUI
    operation = Operation(None, fo_delete, path + "\0", None, flags, False, None, None)
    result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(operation))
    return result == 0 and not operation.fAnyOperationsAborted and not os.path.exists(path)


def _trash_linux(path: str) -> bool:
    """Önce masaüstünün kendi aracını dener; yoksa freedesktop.org çöp kutusu kuralını uygular."""
    if shutil.which("gio"):
        try:
            done = subprocess.run(["gio", "trash", "--", path], capture_output=True, timeout=30).returncode == 0
            if done and not os.path.exists(path):
                return True
        except (OSError, subprocess.SubprocessError):
            pass
    return trash_freedesktop(path, Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "Trash")


def trash_freedesktop(path: str, trash: Path) -> bool:
    """Dosyayı ``trash/files`` altına taşır ve geri yükleme bilgisini ``trash/info`` altına yazar.

    Dosya çöp kutusuyla aynı diskte değilse taşınmaz ve False döner; program dosyayı
    hiçbir zaman kalıcı olarak silmez.
    """
    source = Path(path).absolute()
    files, info = trash / "files", trash / "info"
    try:
        files.mkdir(parents=True, exist_ok=True)
        info.mkdir(parents=True, exist_ok=True)
        counter = 0
        while True:
            name = source.name if not counter else f"{source.stem} ({counter}){source.suffix}"
            record = info / f"{name}.trashinfo"
            try:
                # Bilgi dosyası "x" ile açılır; böylece aynı ad iki kez kullanılamaz.
                with open(record, "x", encoding="utf-8") as handle:
                    handle.write("[Trash Info]\n")
                    handle.write(f"Path={quote(str(source))}\n")
                    handle.write(f"DeletionDate={time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
                break
            except FileExistsError:
                counter += 1
        try:
            os.rename(source, files / name)
        except OSError:
            record.unlink(missing_ok=True)
            return False
    except OSError:
        return False
    return not source.exists()


def reveal(path: Path) -> None:
    """Dosyayı dosya yöneticisinde gösterir; klasör verilirse klasörü açar."""
    if not CAN_REVEAL:
        return
    if PLATFORM == "windows":
        if path.is_file():
            subprocess.Popen(["explorer", "/select,", str(path)])
        else:
            path.mkdir(parents=True, exist_ok=True)
            os.startfile(path)  # noqa: S606 - yalnızca uygulamanın indirme klasörü
        return
    folder = path.parent if path.is_file() else path
    folder.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.Popen(["xdg-open", str(folder)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass
