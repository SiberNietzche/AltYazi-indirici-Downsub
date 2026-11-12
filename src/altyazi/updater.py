"""Altyazı motorunun (yt-dlp) kendiliğinden güncellenmesi.

Kaynak siteler sık değiştiği için programa gömülü yt-dlp zamanla eskir. Program açıldıktan kısa
bir süre sonra, günde en fazla bir kez, PyPI'de daha yeni bir yt-dlp olup olmadığına bakılır.
Varsa paket (ve yt-dlp'nin YouTube için istediği yt-dlp-ejs sürümü) indirilir, PyPI'nin verdiği
SHA-256 özetiyle doğrulanır ve ayar klasörüne açılır. Yeni sürüm bir sonraki açılışta, motor
yüklenmeden önce ``activate`` ile devreye girer.

Güvenlik ağı: indirilen sürüm açılışta yüklenip denenir; yüklenemezse gömülü sürüme dönülür ve o
sürüm bir daha indirilmez. Program güncellenip gömülü sürüm indirilenden yeni olursa indirilen
sürüm silinir. Bu modül yt-dlp'yi kendisi içe aktarmaz; yalnızca ``activate`` aktarır.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import ssl
import sys
import threading
import time
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from . import __version__, system

PYPI = "https://pypi.org/pypi/{name}/json"
PYPI_VERSION = "https://pypi.org/pypi/{name}/{version}/json"
FILES_HOST = "files.pythonhosted.org"
PACKAGES = ("yt_dlp", "yt_dlp_ejs")  # Birlikte yüklenen ve birlikte değiştirilen paketler
CHECK_EVERY = 24 * 60 * 60
FIRST_CHECK_DELAY = 8  # Açılışı yavaşlatmasın diye ilk denetim biraz bekler (saniye)
MAX_DOWNLOAD = 40 * 1024 * 1024
TIMEOUT = 30
_VERSION = re.compile(r"^(\d+(?:\.\d+)*)(?:\.post(\d+))?$")
_EJS_REQUIREMENT = re.compile(r"^Requires-Dist:\s*yt-dlp-ejs\s*==\s*([0-9][\w.]*)", re.MULTILINE)

_lock = threading.Lock()
_active = {"version": "", "source": "bundled"}
_status = {"state": "idle", "pending": None, "error": None}


class UpdateError(Exception):
    pass


def root() -> Path:
    return system.data_dir() / "yt-dlp"


def parse_version(text: str) -> tuple[int, ...] | None:
    """yt-dlp sürümleri tarih biçimindedir: 2026.10.26, 2026.10.26.1 ya da 2026.10.26.post1.

    Ön sürümler (.dev) kabul edilmez. Ek sürüm (.postN) kendi sürümünden yeni, bir sonraki
    sürümden eskidir.
    """
    match = _VERSION.match(str(text or "").strip())
    if not match:
        return None
    base = tuple(int(part) for part in match.group(1).split("."))
    return base + (0, int(match.group(2))) if match.group(2) else base


def newer(candidate: str, current: str) -> bool:
    a, b = parse_version(candidate), parse_version(current)
    return a is not None and (b is None or a > b)


def _load_state() -> dict:
    try:
        state = json.loads((root() / "state.json").read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def _save_state(state: dict) -> None:
    folder = root()
    folder.mkdir(parents=True, exist_ok=True)
    temporary = folder / "state.json.tmp"
    temporary.write_text(json.dumps(state, indent=2), "utf-8")
    temporary.replace(folder / "state.json")


def _purge_modules() -> None:
    for name in list(sys.modules):
        if any(name == package or name.startswith(package + ".") for package in PACKAGES):
            del sys.modules[name]
    import importlib

    importlib.invalidate_caches()


def _bundled_version() -> str:
    """Gömülü yt-dlp'nin sürümünü okur ve modülleri yeniden yüklenebilir bırakır."""
    try:
        from yt_dlp.version import __version__ as version
    except Exception:
        return ""
    finally:
        _purge_modules()
    return version


def _try_import(folder: Path, expected: str) -> None:
    """Klasördeki yt-dlp'yi yükler ve motorun kullandığı parçaları dener; olmazsa hata verir."""
    sys.path.insert(0, str(folder))
    try:
        import yt_dlp
        from yt_dlp.networking import Request as _Request  # noqa: F401 - motor bunu kullanır
        from yt_dlp.version import __version__ as version

        # PyPI'deki ek sürümün (.postN) içindeki sürüm numarası ek almadan yazılır.
        if version not in (expected, expected.split(".post")[0]):
            raise UpdateError(f"beklenen {expected}, yüklenen {version}")
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}):
            pass
    except BaseException:
        _purge_modules()
        sys.path.remove(str(folder))
        raise


def _remove_other_versions(keep: str | None) -> None:
    try:
        entries = list(root().iterdir())
    except OSError:
        return
    for entry in entries:
        if entry.is_dir() and entry.name != keep:
            shutil.rmtree(entry, ignore_errors=True)


def activate() -> dict:
    """İndirilmiş daha yeni bir yt-dlp varsa onu devreye alır. Motor yüklenmeden önce çağrılmalıdır."""
    state = _load_state()
    version = state.get("version")
    folder = root() / str(version) if parse_version(version) else None
    if folder is not None and folder.is_dir():
        bundled = _bundled_version()
        if newer(version, bundled):
            try:
                _try_import(folder, version)
            except BaseException:
                # Bu sürüm bu sistemde çalışmıyor: bir daha indirilmez, gömülü sürüme dönülür.
                state["bad"] = sorted(set(state.get("bad", [])) | {version})
                state.pop("version", None)
                _save_state(state)
                shutil.rmtree(folder, ignore_errors=True)
            else:
                _active.update(version=version, source="update")
                _remove_other_versions(version)
                return dict(_active)
        else:
            # Program güncellenmiş ve gömülü sürüm daha yeni (ya da aynı): indirilen gereksiz.
            state.pop("version", None)
            _save_state(state)
            shutil.rmtree(folder, ignore_errors=True)
    _remove_other_versions(None)
    try:
        from yt_dlp.version import __version__ as bundled
    except Exception:
        bundled = ""
    _active.update(version=bundled, source="bundled")
    return dict(_active)


def status(enabled: bool) -> dict:
    state = _load_state()
    return {
        "enabled": enabled,
        "version": _active["version"],
        "source": _active["source"],
        "pending": _status["pending"],
        "state": _status["state"],
        "error": _status["error"],
        "checked": state.get("checked"),
    }


# Ağ ------------------------------------------------------------------------
def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _fetch(url: str, limit: int) -> bytes:
    request = Request(url, headers={"User-Agent": f"AltyaziIndirici/{__version__}"})
    with urlopen(request, timeout=TIMEOUT, context=_ssl_context()) as response:  # noqa: S310 - yalnızca https
        data = response.read(limit + 1)
    if len(data) > limit:
        raise UpdateError("dosya çok büyük")
    return data


def _get_json(url: str) -> dict:
    data = json.loads(_fetch(url, 4 * 1024 * 1024))
    if not isinstance(data, dict):
        raise UpdateError("geçersiz yanıt")
    return data


def _wheel(meta: dict) -> tuple[str, str]:
    """Sürümün saf Python paketinin (py3-none-any) adresini ve SHA-256 özetini döndürür."""
    for entry in meta.get("urls", []):
        name = str(entry.get("filename", ""))
        if entry.get("packagetype") == "bdist_wheel" and name.endswith("-py3-none-any.whl"):
            url, digest = str(entry.get("url", "")), str(entry.get("digests", {}).get("sha256", ""))
            parts = urlsplit(url)
            if parts.scheme != "https" or parts.hostname != FILES_HOST:
                raise UpdateError("beklenmeyen indirme adresi")
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise UpdateError("özet yok")
            return url, digest
    raise UpdateError("uygun paket yok")


def _download(url: str, digest: str) -> bytes:
    data = _fetch(url, MAX_DOWNLOAD)
    if hashlib.sha256(data).hexdigest() != digest:
        raise UpdateError("özet tutmuyor")
    return data


def _extract(data: bytes, target: Path) -> str:
    """Paketin yalnızca PACKAGES klasörlerini açar; paketin METADATA metnini döndürür."""
    metadata = ""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for member in archive.infolist():
            path = PurePosixPath(member.filename)
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise UpdateError("geçersiz dosya adı")
            if path.parts[0].endswith(".dist-info") and path.name == "METADATA":
                metadata = archive.read(member).decode("utf-8", "replace")
            if path.parts[0] not in PACKAGES or member.is_dir():
                continue
            destination = target.joinpath(*path.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(member))
    return metadata


def check(enabled: bool, force: bool = False) -> dict:
    """Yeni sürümü denetler ve varsa indirir. Aynı anda yalnızca bir denetim çalışır."""
    if not enabled and not force:
        return status(enabled)
    if not _lock.acquire(blocking=False):
        return status(enabled)
    try:
        state = _load_state()
        if not force and time.time() - float(state.get("checked") or 0) < CHECK_EVERY:
            return status(enabled)
        _status.update(state="checking", error=None)
        try:
            meta = _get_json(PYPI.format(name="yt-dlp"))
            latest = str(meta.get("info", {}).get("version", ""))
            state["checked"] = time.time()
            _save_state(state)
            current = state.get("version") or _active["version"]
            if not newer(latest, current) or latest in state.get("bad", []):
                _status.update(state="downloaded" if _status["pending"] else "uptodate")
                return status(enabled)
            main = _download(*_wheel(meta))
            temporary = root() / f".tmp-{latest}"
            shutil.rmtree(temporary, ignore_errors=True)
            temporary.mkdir(parents=True)
            try:
                requirement = _EJS_REQUIREMENT.search(_extract(main, temporary))
                if requirement:
                    ejs = _get_json(PYPI_VERSION.format(name="yt-dlp-ejs", version=requirement.group(1)))
                    _extract(_download(*_wheel(ejs)), temporary)
                if not (temporary / "yt_dlp" / "__init__.py").is_file():
                    raise UpdateError("paket eksik")
                final = root() / latest
                shutil.rmtree(final, ignore_errors=True)
                temporary.rename(final)
            except BaseException:
                shutil.rmtree(temporary, ignore_errors=True)
                raise
            state = _load_state()
            state["version"] = latest
            _save_state(state)
            _status.update(state="downloaded", pending=latest)
        except Exception as exc:  # Ağ yoksa ya da PyPI yanıt vermiyorsa program etkilenmez
            _status.update(state="error", error=type(exc).__name__)
        return status(enabled)
    finally:
        _lock.release()


def check_later(enabled) -> None:
    """Açılıştan kısa bir süre sonra arka planda denetler; ``enabled`` ayarı okuyan bir işlevdir."""
    def run() -> None:
        time.sleep(FIRST_CHECK_DELAY)
        check(bool(enabled()))

    threading.Thread(target=run, name="altyazi-update", daemon=True).start()
