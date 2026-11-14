"""YouTube makine çevirisini vermediğinde özgün altyazıyı Google Çeviri ile çevirir.

Yöntem, Gythiro/yt-dual-subs eklentisinin (MIT) anahtarsız Google yedeğinden uyarlanmıştır:
otomatik altyazılar cümle değil zaman dilimidir, tek tek çevrilince anlamsızlaşır. Bu yüzden
satırlar önce cümlelere birleştirilir, cümleler çevrilir, çeviri sonra satırlara oranlı olarak
geri dağıtılır; böylece zamanlama ve satır uzunlukları özgün altyazıdaki gibi kalır.

Uyarlanan sürüm: yt-dual-subs 3.7.0, commit 5657c8a (2026-09-12). Karşılık gelen yerler:
background.js içindeki gtxFetch ve content.js içindeki computeSentenceGroups. Kaynak
güncellendiğinde bu iki yerdeki değişiklikler buraya aktarılmalıdır.
"""

from __future__ import annotations

import json
import re
import ssl
import time
import urllib.request
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlencode

from .subtitles import Cue

ENDPOINT = "https://translate.googleapis.com/translate_a/single"
PAUSE_BREAK_MS = 600  # Bu kadar sessizlik cümleyi bitirir
MAX_GROUP_WORDS = 32
MAX_GROUP_CHARS = 280
MAX_BATCH_CHARS = 3500  # Tek istekte gönderilen en fazla metin
REQUEST_GAP = 1.0  # İstekler arası bekleme (saniye)
LIMIT_DELAYS = (5, 15)  # Google 429/503 verirse bekleme süreleri
_SENTENCE_END = re.compile(r"[.!?…。！？][\"'”’」』》】)）\]]?\s*$")
_NO_SPACE = re.compile(r"[぀-ヿ㐀-鿿가-힯฀-๿]")
# YouTube dil kodlarından Google Çeviri kodlarına
_CODES = {"zh-Hans": "zh-CN", "zh-Hant": "zh-TW", "zh": "zh-CN", "fil": "tl", "he": "iw", "jv": "jw"}

Post = Callable[[str, bytes, dict], bytes]


class TranslateError(Exception):
    """Google Çeviri yanıt vermedi ya da sınırladı."""


def _ssl_context() -> ssl.SSLContext:
    try:  # Paketlenmiş sürümlerde sistem sertifikaları bulunmayabilir; yt-dlp certifi'yi getirir
        import certifi

        context = ssl.create_default_context(cafile=certifi.where())
    except (ImportError, OSError):
        context = ssl.create_default_context()
    # Google bu uç noktada TLS el sıkışmasında post_handshake_auth uzantısı olmayan istemcileri
    # 429 ile geri çeviriyor (yt-dlp'nin bağlantıları da bu yüzden reddediliyor). http.client'ın
    # kendi bağlamında yaptığı ayarlar burada da yapılır.
    context.set_alpn_protocols(["http/1.1"])
    if context.post_handshake_auth is not None:
        context.post_handshake_auth = True
    return context


def http_post(url: str, body: bytes, headers: dict) -> bytes:
    """İsteği yt-dlp'den bağımsız olarak standart kütüphaneyle gönderir (bkz. _ssl_context)."""
    request = urllib.request.Request(url, data=body, headers={"User-Agent": "Mozilla/5.0", **headers})
    with urllib.request.urlopen(request, timeout=30, context=_ssl_context()) as response:
        return response.read()


@dataclass
class Group:
    start: int  # ilk satırın sırası
    end: int  # son satırın sırası (dahil)
    text: str


def google_code(lang: str) -> str:
    lang = lang.removesuffix("-orig")
    return _CODES.get(lang, _CODES.get(lang.split("-")[0], lang))


def _words(text: str) -> int:
    return len(text.split())


def sentence_groups(cues: list[Cue]) -> list[Group]:
    """Satırları cümlelere birleştirir: sessizlik, cümle sonu işareti ya da uzunluk sınırı keser."""
    groups: list[Group] = []
    texts = [" ".join(cue.text.split()) for cue in cues]
    start, words, chars, best_pause, best_at = 0, 0, 0, -1, -1
    i = 0
    while i < len(cues):
        words += _words(texts[i])
        chars += len(texts[i]) + 1
        last = i == len(cues) - 1
        pause = float("inf") if last else cues[i + 1].start - cues[i].end
        if last or pause > PAUSE_BREAK_MS or _SENTENCE_END.search(texts[i]):
            cut = i
        else:
            if pause > best_pause:
                best_pause, best_at = pause, i
            following = texts[i + 1]
            if words + _words(following) <= MAX_GROUP_WORDS and chars + len(following) <= MAX_GROUP_CHARS:
                i += 1
                continue
            cut = best_at if best_at >= start else i  # Grubun içindeki en uzun duraktan keser
        groups.append(Group(start, cut, " ".join(texts[start : cut + 1])))
        start, words, chars, best_pause, best_at = cut + 1, 0, 0, -1, -1
        i = cut + 1
    return groups


def split_proportionally(text: str, weights: list[int]) -> list[str]:
    """Çeviriyi, özgün satırların uzunluklarıyla orantılı parçalara sözcük sınırından böler."""
    if len(weights) == 1:
        return [text]
    spaced = not _NO_SPACE.search(text)
    units = text.split() if spaced else list(text)
    joiner = " " if spaced else ""
    total = sum(max(w, 1) for w in weights)
    parts, used, running = [], 0, 0
    for index, weight in enumerate(weights):
        running += max(weight, 1)
        remaining = len(weights) - index - 1
        if not remaining:
            take = len(units)
        else:
            # Her satıra en az bir birim düşmesi ve sonrakilere de birer birim kalması gözetilir
            limit = max(min(used + 1, len(units)), len(units) - remaining)
            take = min(max(round(len(units) * running / total), used + 1), limit)
        parts.append(joiner.join(units[used:take]).strip())
        used = take
    return parts


def _parse_gtx(raw: bytes) -> str:
    data = json.loads(raw.decode("utf-8"))
    return "".join(seg[0] for seg in data[0] if seg and isinstance(seg[0], str))


def _parse_dict(raw: bytes) -> str:
    data = json.loads(raw.decode("utf-8"))  # [["çeviri", "algılanan dil"]] ya da ["çeviri"]
    first = data[0]
    return first[0] if isinstance(first, list) else first


# Uç noktalar sırayla denenir. Google, çok istek gelen adresi translate.googleapis.com'da bir süre
# 429 ile sınırlıyor; Chrome sözlük eklentisinin kullandığı clients5 uç noktası o sırada yanıt
# vermeye devam ediyor. İkisi de anahtarsız ve aynı biçimde (q alanı) metin alır.
ENDPOINTS = (
    (ENDPOINT, {"client": "gtx", "dt": "t"}, _parse_gtx),
    ("https://clients5.google.com/translate_a/t", {"client": "dict-chrome-ex"}, _parse_dict),
)


def _limited(exc: Exception) -> bool:
    return any(code in str(exc) for code in ("429", "503", "403"))


class Translator:
    def __init__(self, post: Post | None = None, sleep: Callable[[float], None] | None = None) -> None:
        self._post = post or http_post
        self._sleep = sleep or (lambda seconds: time.sleep(seconds))
        self._last = 0.0
        self._endpoint = 0  # Sınırlanan uç noktaya bu çeviri boyunca dönülmez

    def _send(self, index: int, text: str, target: str) -> str:
        base, params, parse = ENDPOINTS[index]
        url = f"{base}?" + urlencode({**params, "sl": "auto", "tl": target})
        body = urlencode({"q": text}).encode("utf-8")
        wait = REQUEST_GAP - (time.monotonic() - self._last)
        if wait > 0:
            self._sleep(wait)
        self._last = time.monotonic()
        raw = self._post(url, body, {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"})
        try:
            result = parse(raw)
        except (ValueError, TypeError, IndexError, KeyError, AttributeError) as exc:
            raise TranslateError("unreadable response") from exc
        if not isinstance(result, str):
            raise TranslateError("unreadable response")
        return result

    def _request(self, text: str, target: str) -> str:
        for delay in (*LIMIT_DELAYS, None):
            limited = False
            error: Exception | None = None
            for index in range(self._endpoint, len(ENDPOINTS)):
                try:
                    result = self._send(index, text, target)
                    self._endpoint = index
                    return result
                except TranslateError as exc:
                    error = exc  # Okunamayan yanıtta sıradaki uç nokta denenir
                except Exception as exc:
                    error = exc
                    limited = limited or _limited(exc)
            if not limited or delay is None:
                break
            self._endpoint = 0  # Beklemeden sonra hepsi baştan denenir
            self._sleep(delay)
        message = str(error)[:200] if error else ""
        raise TranslateError(message or "rate limited") from error

    def _batch(self, texts: list[str], target: str) -> list[str]:
        lines = self._request("\n".join(texts), target).split("\n")
        if len(lines) == len(texts):
            return [line.strip() for line in lines]
        if len(texts) == 1:
            return [" ".join(lines).strip()]
        middle = len(texts) // 2  # Satır sayısı tutmazsa ikiye bölüp yeniden dener
        return self._batch(texts[:middle], target) + self._batch(texts[middle:], target)

    def translate_texts(self, texts: list[str], target: str) -> list[str]:
        result: list[str] = []
        batch: list[str] = []
        size = 0
        for text in texts:
            if batch and size + len(text) + 1 > MAX_BATCH_CHARS:
                result += self._batch(batch, target)
                batch, size = [], 0
            batch.append(text)
            size += len(text) + 1
        if batch:
            result += self._batch(batch, target)
        return result

    def translate_cues(self, cues: list[Cue], target_lang: str) -> list[Cue]:
        groups = sentence_groups(cues)
        translated = self.translate_texts([group.text for group in groups], google_code(target_lang))
        result: list[Cue] = []
        for group, text in zip(groups, translated):
            members = cues[group.start : group.end + 1]
            pieces = split_proportionally(text, [len(cue.text) for cue in members])
            for cue, piece in zip(members, pieces):
                if piece:
                    result.append(Cue(cue.start, cue.end, piece))
                elif result and result[-1].end <= cue.end:
                    result[-1].end = cue.end  # Boş kalan satırın süresi öncekine eklenir
        return result
