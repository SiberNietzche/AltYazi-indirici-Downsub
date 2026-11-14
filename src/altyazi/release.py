"""Programın yeni sürümünü bildirme.

Program açıldıktan kısa bir süre sonra, günde en fazla bir kez, GitHub'daki son yayımlanan sürüme
(releases/latest; taslak ve ön sürümler hariç) bakılır. Daha yeniyse arayüz bir bildirim gösterir;
indirme ve kurulumu kullanıcı yapar. Windows ve Android'de kurulum dosyası doğrudan, Linux'ta
(deb ya da AppImage seçimi kullanıcıya kalır) sürüm sayfası açılır.

Altyazı motorunun (yt-dlp) kendiliğinden güncellenmesi ayrıdır: bkz. updater.
"""

from __future__ import annotations

import json
import re
import threading
import time
import webbrowser
from urllib.parse import urlsplit

from . import __version__, system, updater

REPO = "SiberNietzche/AltYazi-indirici-Downsub"
LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
CHECK_EVERY = 24 * 60 * 60
FIRST_CHECK_DELAY = 10  # Açılışı yavaşlatmasın diye ilk denetim biraz bekler (saniye)
ASSET_SUFFIX = {"windows": "_windows.exe", "android": "_android.apk"}
_VERSION = re.compile(r"^v?(\d+(?:\.\d+){0,3})$")

_lock = threading.Lock()
_status = {"state": "idle"}


def _path():
    return system.data_dir() / "app-update.json"


def parse_version(text: str) -> tuple[int, ...] | None:
    match = _VERSION.match(str(text or "").strip())
    if not match:
        return None
    parts = [int(part) for part in match.group(1).split(".")]
    return tuple(parts + [0] * (3 - len(parts)))


def newer(candidate: str, current: str) -> bool:
    a, b = parse_version(candidate), parse_version(current)
    return a is not None and b is not None and a > b


def _load() -> dict:
    try:
        state = json.loads(_path().read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def _save(state: dict) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2), "utf-8")
    temporary.replace(path)


def _github_url(url: object) -> str | None:
    """Yalnızca https://github.com/<REPO>/... adresleri kabul edilir."""
    if not isinstance(url, str):
        return None
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != "github.com" or not parts.path.startswith(f"/{REPO}/"):
        return None
    return url


def read_release(data: dict, platform: str) -> dict:
    """GitHub yanıtından sürümü, sürüm sayfasını ve bu sisteme uygun indirme adresini çıkarır."""
    version = str(data.get("tag_name") or "").strip()
    if parse_version(version) is None or data.get("draft") or data.get("prerelease"):
        raise updater.UpdateError("geçersiz sürüm")
    page = _github_url(data.get("html_url")) or f"https://github.com/{REPO}/releases/latest"
    download = None
    suffix = ASSET_SUFFIX.get(platform)
    if suffix:
        for asset in data.get("assets") or []:
            if isinstance(asset, dict) and str(asset.get("name", "")).endswith(suffix):
                download = _github_url(asset.get("browser_download_url"))
                if download:
                    break
    return {"latest": version.lstrip("v"), "page": page, "download": download or page}


def status(enabled: bool) -> dict:
    state = _load()
    latest = state.get("latest") or ""
    available = newer(latest, __version__)
    return {
        "enabled": enabled,
        "current": __version__,
        "latest": latest,
        "available": available,
        "dismissed": available and state.get("dismissed") == latest,
        "page": state.get("page"),
        "download": state.get("download"),
        "state": _status["state"],
        "checked": state.get("checked"),
    }


def check(enabled: bool, force: bool = False) -> dict:
    """GitHub'daki son sürüme bakar. Aynı anda yalnızca bir denetim çalışır."""
    if not enabled and not force:
        return status(enabled)
    if not _lock.acquire(blocking=False):
        return status(enabled)
    try:
        state = _load()
        if not force and time.time() - float(state.get("checked") or 0) < CHECK_EVERY:
            return status(enabled)
        _status["state"] = "checking"
        try:
            release = read_release(updater._get_json(LATEST), system.PLATFORM)
        except Exception:  # Ağ yoksa ya da GitHub yanıt vermiyorsa program etkilenmez
            _status["state"] = "error"
            return status(enabled)
        state = _load()
        state.update(release, checked=time.time())
        _save(state)
        _status["state"] = "done"
        return status(enabled)
    finally:
        _lock.release()


def dismiss(version: str) -> None:
    """Bu sürüm için bildirim bir daha gösterilmez; daha yeni bir sürüm çıkınca yeniden gösterilir."""
    state = _load()
    state["dismissed"] = str(version)
    _save(state)


def open_download() -> str | None:
    """İndirme adresini sistemin tarayıcısında açar (masaüstü). Android'de arayüz kendisi açar."""
    state = _load()
    url = _github_url(state.get("download")) or _github_url(state.get("page"))
    if url and system.PLATFORM != "android":
        webbrowser.open(url)
    return url


def check_later(enabled) -> None:
    """Açılıştan kısa bir süre sonra arka planda denetler; ``enabled`` ayarı okuyan bir işlevdir."""
    def run() -> None:
        time.sleep(FIRST_CHECK_DELAY)
        check(bool(enabled()))

    threading.Thread(target=run, name="altyazi-release", daemon=True).start()
