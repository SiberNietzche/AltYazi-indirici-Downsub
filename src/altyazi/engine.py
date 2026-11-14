"""yt-dlp üzerinden video bilgisi ve altyazı alma."""

from __future__ import annotations

import re
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urljoin, urlsplit

import yt_dlp
from yt_dlp.networking import Request

from . import subtitles as subs
from . import translate

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_EXT_PRIORITY = ["json3", "vtt", "srt", "ttml", "dfxp", "srv3", "srv2", "srv1", "ass", "ssa"]
_MAX_PLAYLIST_ITEMS = 500
_CACHE_SIZE = 30
_FIRST_TRY_DELAYS = (5, 15, None)  # 429 yanıtında bekleme süreleri (saniye)
_AFTER_REFRESH_DELAYS = (5, None)


class EngineError(Exception):
    """Arayüzün kullanıcının dilinde gösterdiği hata; metin değil kod taşır.

    retryable: dil listesi tazelendiğinde düzelebilecek bir indirme hatası.
    """

    def __init__(self, code: str, retryable: bool = False, **params) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.params = params

    def payload(self) -> dict:
        return {"error": self.code, "code": self.code, "params": self.params}


class _SilentLogger:
    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


def _options(**extra) -> dict:
    options = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "skip_download": True,
        "ignore_no_formats_error": True,
        "noplaylist": True,
        "extract_flat": "in_playlist",
        "playlistend": _MAX_PLAYLIST_ITEMS,
        "socket_timeout": 30,
        "logger": _SilentLogger(),
        "js_runtimes": {"deno": {}, "node": {}},
    }
    options.update(extra)
    return options


def _friendly_error(exc: Exception) -> EngineError:
    message = _ANSI.sub("", str(exc)).strip()
    message = re.sub(r"^ERROR:\s*", "", message)
    if "DRM" in message:
        return EngineError("drm")
    if "429" in message:
        return EngineError("rate_limited", retryable=True)
    if "Unsupported URL" in message:
        return EngineError("unsupported_url")
    if "HTTP Error 404" in message:
        return EngineError("not_found", retryable=True)
    if "Sign in" in message or "login" in message.lower():
        return EngineError("login_required")
    return EngineError("source_error", retryable=True, detail=message[:400] or type(exc).__name__)


def playlist_link(url: str) -> str | None:
    """Listeden açılan bir YouTube izleme bağlantısının (watch?v=…&list=…) liste adresini verir."""
    parts = urlsplit(url)
    host = parts.netloc.lower().removeprefix("www.").removeprefix("m.").removeprefix("music.")
    if host not in {"youtube.com", "youtu.be"}:
        return None
    playlist = (parse_qs(parts.query).get("list") or [""])[0]
    if not re.fullmatch(r"[A-Za-z0-9_-]{2,64}", playlist):
        return None
    return f"https://www.youtube.com/playlist?list={playlist}"


def validate_url(url: str) -> str:
    url = (url or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or "." not in parts.netloc:
        raise EngineError("invalid_url")
    return url


@dataclass
class Session:
    """Çözülmüş bir bağlantı ve onu üreten yt-dlp oturumu."""

    id: str
    url: str
    info: dict
    ydl: yt_dlp.YoutubeDL
    tracks: dict[str, dict] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)


def _build_tracks(info: dict) -> dict[str, dict]:
    tracks: dict[str, dict] = {}
    for lang, formats in (info.get("subtitles") or {}).items():
        if lang == "live_chat" or not formats:
            continue
        tracks[f"manual:{lang}"] = {
            "key": f"manual:{lang}",
            "lang": lang,
            "name": formats[0].get("name") or lang,
            "kind": "manual",
            "formats": formats,
        }
    automatic = info.get("automatic_captions") or {}
    originals = {lang for lang in automatic if lang.endswith("-orig")}
    for lang, formats in automatic.items():
        if not formats:
            continue
        translated = bool(originals) and lang not in originals and f"{lang}-orig" not in originals
        tracks[f"auto:{lang}"] = {
            "key": f"auto:{lang}",
            "lang": lang,
            "name": formats[0].get("name") or lang,
            "kind": "translated" if translated else "auto",
            "formats": formats,
        }
    return tracks


def _pick_format(formats: list[dict]) -> dict:
    def rank(fmt: dict) -> int:
        ext = (fmt.get("ext") or "").lower()
        return _EXT_PRIORITY.index(ext) if ext in _EXT_PRIORITY else len(_EXT_PRIORITY)

    direct = [fmt for fmt in formats if "m3u8" not in (fmt.get("protocol") or "")]
    return min(direct or formats, key=rank)


class Engine:
    def __init__(self) -> None:
        self._sessions: OrderedDict[str, Session] = OrderedDict()
        self._lock = threading.Lock()

    # Bilgi alma ---------------------------------------------------------
    def _extract(self, url: str) -> tuple[yt_dlp.YoutubeDL, dict]:
        ydl = yt_dlp.YoutubeDL(_options())
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as exc:  # yt-dlp birçok özel hata türü yükseltir
            ydl.close()
            raise _friendly_error(exc) from exc
        if not info:
            ydl.close()
            raise EngineError("no_info")
        return ydl, info

    def open(self, url: str) -> dict:
        url = validate_url(url)
        ydl, info = self._extract(url)
        session = Session(uuid.uuid4().hex, url, info, ydl, _build_tracks(info))
        with self._lock:
            self._sessions[session.id] = session
            while len(self._sessions) > _CACHE_SIZE:
                _, old = self._sessions.popitem(last=False)
                old.ydl.close()
        return self._describe(session)

    def refresh(self, session_id: str) -> dict:
        """Dil listesini ve altyazı adreslerini kaynak siteden yeniden alır; oturum kimliği değişmez."""
        session = self._session(session_id)
        ydl, info = self._extract(session.url)
        with session.lock:
            old = session.ydl
            session.ydl, session.info, session.tracks = ydl, info, _build_tracks(info)
            old.close()
        return self._describe(session)

    def _describe(self, session: Session) -> dict:
        info = session.info
        result = {
            "id": session.id,
            "title": info.get("title") or "",
            "uploader": info.get("uploader") or info.get("channel") or "",
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail") or "",
            "site": info.get("extractor_key") or "",
            "webpage_url": info.get("webpage_url") or "",
            "is_playlist": info.get("_type") in {"playlist", "multi_video"},
            "tracks": [
                {k: track[k] for k in ("key", "lang", "name", "kind")}
                for track in session.tracks.values()
            ],
            "entries": [],
            "playlist_url": None,
        }
        if not result["is_playlist"]:
            result["playlist_url"] = playlist_link(session.url)
        if result["is_playlist"]:
            for entry in info.get("entries") or []:
                if not entry:
                    continue
                link = entry.get("webpage_url") or entry.get("url")
                if link:
                    result["entries"].append(
                        {"title": entry.get("title") or link, "url": link, "duration": entry.get("duration")}
                    )
        return result

    def _session(self, session_id: str) -> Session:
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            raise EngineError("session_missing")
        return session

    # Altyazı alma -------------------------------------------------------
    def _fetch_bytes(self, ydl: yt_dlp.YoutubeDL, url: str, headers: dict | None, delays=_FIRST_TRY_DELAYS) -> bytes:
        # YouTube makine çevirisi isteklerini (tlang) ilk istekte bile 429 ile geri çevirebiliyor;
        # özgün altyazı aynı anda sorunsuz gelir. Bu sık istekten olmadığı için beklemek de tazelemek
        # de işe yaramaz: hemen durulur ve kullanıcıya özgün dil önerilir.
        translation = "tlang" in parse_qs(urlsplit(url).query)
        for delay in delays:
            try:
                with ydl.urlopen(Request(url, headers=headers or {})) as response:
                    return response.read()
            except Exception as exc:
                if "429" in str(exc) and translation:
                    raise EngineError("translation_blocked") from exc
                if "429" in str(exc) and delay is not None:
                    time.sleep(delay)
                    continue
                raise _friendly_error(exc) from exc
        raise EngineError("source_error", retryable=True, detail="no response")

    def _fetch_track(self, session: Session, key: str, delays=_FIRST_TRY_DELAYS) -> tuple[bytes, str]:
        track = session.tracks.get(key)
        if track is None:
            raise EngineError("track_missing")
        try:
            return self._fetch_format(session, _pick_format(track["formats"]), delays)
        except EngineError as exc:
            if exc.code == "translation_blocked":
                exc.params.update(lang=track["lang"], name=track["name"], **self._source_of(session, track))
            raise

    @staticmethod
    def _source_of(session: Session, track: dict) -> dict:
        """Çevirinin yapıldığı özgün altyazıyı bulur: arayüz onu indirmeyi önerir."""
        query = parse_qs(urlsplit(_pick_format(track["formats"]).get("url") or "").query)
        lang = (query.get("lang") or [""])[0]
        if (query.get("kind") or [""])[0] == "asr":
            candidates = [f"auto:{lang}-orig", f"auto:{lang}"]
        else:
            candidates = [f"manual:{lang}"]
        candidates += [key for key in session.tracks if key.startswith("auto:") and key.endswith("-orig")]
        for key in candidates:
            if key in session.tracks and key != track["key"]:
                source = session.tracks[key]
                return {"source": key, "source_lang": source["lang"], "source_name": source["name"]}
        return {}

    def _fetch_format(self, session: Session, fmt: dict, delays) -> tuple[bytes, str]:
        ext = (fmt.get("ext") or "vtt").lower()
        if fmt.get("data") is not None:
            data = fmt["data"]
            return (data.encode("utf-8") if isinstance(data, str) else data), ext
        headers = fmt.get("http_headers")
        with session.lock:
            if "m3u8" in (fmt.get("protocol") or ""):
                playlist = self._fetch_bytes(session.ydl, fmt["url"], headers, delays).decode("utf-8", "replace")
                parts = [
                    self._fetch_bytes(session.ydl, urljoin(fmt["url"], line.strip()), headers, delays)
                    for line in playlist.splitlines()
                    if line.strip() and not line.startswith("#")
                ]
                return b"\n\n".join(parts), "vtt"
            return self._fetch_bytes(session.ydl, fmt["url"], headers, delays), ext

    def _cues(self, session: Session, key: str, delays=_FIRST_TRY_DELAYS) -> list[subs.Cue]:
        raw, ext = self._fetch_track(session, key, delays)
        try:
            cues = subs.parse(raw.decode("utf-8-sig", "replace"), ext)
        except subs.SubtitleParseError as exc:
            raise EngineError("parse_failed", retryable=True) from exc
        return subs.collapse_rolling(cues) if key.startswith("auto:") else cues

    def _with_refresh(self, session: Session, action: Callable):
        """İndirme başarısız olursa dil listesini tazeleyip bir kez daha dener."""
        try:
            return action(_FIRST_TRY_DELAYS)
        except EngineError as first:
            if not first.retryable:
                raise
            try:
                self.refresh(session.id)
            except EngineError:
                raise first from None  # Tazeleme de olmazsa asıl hata gösterilir
            return action(_AFTER_REFRESH_DELAYS)

    def _track_cues(self, session: Session, key: str) -> tuple[list[subs.Cue], bool]:
        """Satırları ve Google Çeviri'ye başvurulup başvurulmadığını döndürür.

        YouTube makine çevirisini 429 ile engellerse çevirinin yapıldığı özgün altyazı indirilir ve
        Google Çeviri ile çevrilir. Google da olmazsa asıl engel hatası (özgün dil önerisiyle) kalır.
        """
        try:
            return self._with_refresh(session, lambda delays: self._cues(session, key, delays)), False
        except EngineError as blocked:
            source = blocked.params.get("source")
            if blocked.code != "translation_blocked" or not source:
                raise
            original = self._with_refresh(session, lambda delays: self._cues(session, source, delays))
            try:
                cues = translate.Translator().translate_cues(original, session.tracks[key]["lang"])
            except translate.TranslateError:
                raise blocked from None
            if not cues:
                raise blocked
            return cues, True

    def render(self, session_id: str, key: str, fmt: str, second_key: str | None = None) -> tuple[bytes, str, str, bool]:
        """(içerik, uzantı, dosya adı kökü, Google Çeviri kullanıldı mı) döndürür."""
        session = self._session(session_id)
        track = session.tracks.get(key)
        if track is None:
            raise EngineError("track_missing")
        stem = subs.safe_filename(session.info.get("title") or "")
        lang = subs.safe_filename(track["lang"], "dil", 30)
        if fmt == "raw":
            if second_key:
                raise EngineError("dual_raw")
            data, ext = self._with_refresh(session, lambda delays: self._fetch_track(session, key, delays))
            return data, subs.safe_filename(ext, "txt", 10), f"{stem}.{lang}", False
        if fmt not in subs.WRITERS:
            raise EngineError("unknown_format")
        if second_key and second_key not in session.tracks:
            raise EngineError("track_missing")
        cues, google = self._track_cues(session, key)
        if second_key:
            second_lang = subs.safe_filename(session.tracks[second_key]["lang"], "dil", 30)
            second_cues, second_google = self._track_cues(session, second_key)
            cues = subs.merge_dual(cues, second_cues)
            lang = f"{lang}+{second_lang}"
            google = google or second_google
        writer, ext = subs.WRITERS[fmt]
        return writer(cues).encode("utf-8"), ext, f"{stem}.{lang}", google

    def download(
        self, session_id: str, key: str, fmt: str, directory: Path, second_key: str | None = None
    ) -> tuple[Path, bool]:
        """Dosyayı yazar; (yol, Google Çeviri kullanıldı mı) döndürür."""
        data, ext, stem, google = self.render(session_id, key, fmt, second_key)
        return write_unique(directory, stem, ext, data), google

    def pick_track(self, session_id: str, lang: str, allow_auto: bool) -> str | None:
        """İstenen dil için önce gerçek altyazıyı, izin varsa sonra otomatik olanı seçer."""
        session = self._session(session_id)
        kinds = ["manual"] + (["auto"] if allow_auto else [])
        base = lang.split("-")[0].lower()
        for prefix in kinds:
            for candidate in (lang, f"{lang}-orig"):
                if f"{prefix}:{candidate}" in session.tracks:
                    return f"{prefix}:{candidate}"
            for key, track in session.tracks.items():
                if key.startswith(prefix + ":") and track["lang"].split("-")[0].lower() == base:
                    return key
        return None


def write_unique(directory: Path, stem: str, ext: str, data: bytes) -> Path:
    """Var olan dosyanın üzerine yazmadan yeni bir dosya oluşturur."""
    directory.mkdir(parents=True, exist_ok=True)
    counter = 0
    while True:
        suffix = f" ({counter})" if counter else ""
        path = directory / f"{stem}{suffix}.{ext}"
        try:
            with open(path, "xb") as handle:
                handle.write(data)
            return path
        except FileExistsError:
            counter += 1


class JobManager:
    """Oynatma listesi indirmelerini arka planda yürütür."""

    def __init__(self, engine: Engine, on_saved: Callable[[Path], None] | None = None) -> None:
        self._engine = engine
        self._on_saved = on_saved
        self._jobs: dict[str, dict] = {}
        self._cancel: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def start(
        self, title: str, urls: list[str], lang: str, fmt: str, allow_auto: bool, directory: Path,
        second_lang: str | None = None,
    ) -> str:
        """second_lang verilirse her video için iki dil tek dosyada birleştirilir (çift dil)."""
        job_id = uuid.uuid4().hex
        target = directory / subs.safe_filename(title, "oynatma-listesi", 100)
        job = {
            "id": job_id, "total": len(urls), "done": 0, "saved": 0, "state": "running",
            "current": "", "failures": [], "directory": str(target),
        }
        with self._lock:
            self._jobs[job_id] = job
            self._cancel[job_id] = threading.Event()
        args = (job, self._cancel[job_id], urls, lang, fmt, allow_auto, target, second_lang)
        threading.Thread(target=self._run, args=args, daemon=True).start()
        return job_id

    def _run(self, job, cancel, urls, lang, fmt, allow_auto, target, second_lang=None) -> None:
        for url in urls:
            if cancel.is_set():
                job["state"] = "cancelled"
                return
            job["current"] = url
            try:
                info = self._engine.open(url)
                job["current"] = info["title"] or url
                key = self._engine.pick_track(info["id"], lang, allow_auto)
                if key is None:
                    raise EngineError("no_language", lang=lang)
                second_key = None
                if second_lang:
                    second_key = self._engine.pick_track(info["id"], second_lang, allow_auto)
                    if second_key is None:
                        raise EngineError("no_language", lang=second_lang)
                path, _ = self._engine.download(info["id"], key, fmt, target, second_key)
                if self._on_saved:
                    self._on_saved(path)
                job["saved"] += 1
            except EngineError as exc:
                job["failures"].append({"item": job["current"], "code": exc.code, "params": exc.params})
            except Exception as exc:  # Bir videonun hatası listenin kalanını durdurmamalı
                friendly = _friendly_error(exc)
                job["failures"].append({"item": job["current"], "code": friendly.code, "params": friendly.params})
            job["done"] += 1
            time.sleep(1)  # Kaynak siteye ardışık istekleri yavaşlatır
        job["state"] = "finished"

    def status(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise EngineError("job_missing")
        return dict(job, failures=list(job["failures"]))

    def cancel(self, job_id: str) -> None:
        event = self._cancel.get(job_id)
        if event is None:
            raise EngineError("job_missing")
        event.set()
