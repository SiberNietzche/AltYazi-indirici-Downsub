"""Altyazı biçimlerini ayrıştırma ve dönüştürme. Ağ erişimi yapmaz."""

from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass


class SubtitleParseError(ValueError):
    """Altyazı verisi bilinen bir biçimde çözülemedi."""


@dataclass
class Cue:
    start: int  # milisaniye
    end: int  # milisaniye
    text: str


_TIMING = re.compile(
    r"(?P<start>(?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3})\s*-->\s*(?P<end>(?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3})"
)
_TAG = re.compile(r"<[^>]+>")
_ASS_OVERRIDE = re.compile(r"\{[^}]*\}")


def _clock_to_ms(value: str) -> int:
    value = value.replace(",", ".")
    clock, _, fraction = value.partition(".")
    parts = [int(p) for p in clock.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    hours, minutes, seconds = parts
    millis = int((fraction + "000")[:3]) if fraction else 0
    return (hours * 3600 + minutes * 60 + seconds) * 1000 + millis


def _clean_text(text: str) -> str:
    text = html.unescape(_TAG.sub("", text)).replace("​", "")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def parse_timed_text(data: str) -> list[Cue]:
    """WebVTT ve SRT verisini çözer; art arda eklenmiş VTT parçalarını da kabul eder."""
    cues: list[Cue] = []
    blocks = re.split(r"\n[ \t]*\n", data.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n"))
    for block in blocks:
        lines = block.split("\n")
        for index, line in enumerate(lines):
            match = _TIMING.search(line)
            if match:
                text = _clean_text("\n".join(lines[index + 1 :]))
                if text:
                    cues.append(Cue(_clock_to_ms(match["start"]), _clock_to_ms(match["end"]), text))
                break
    return cues


def parse_json3(data: str) -> list[Cue]:
    """YouTube json3 biçimini çözer."""
    try:
        events = json.loads(data).get("events", [])
    except (ValueError, AttributeError) as exc:
        raise SubtitleParseError("json3 çözülemedi") from exc
    cues: list[Cue] = []
    for event in events:
        segments = event.get("segs")
        if not segments:
            continue
        text = _clean_text("".join(seg.get("utf8", "") for seg in segments))
        if not text:
            continue
        start = int(event.get("tStartMs", 0))
        cues.append(Cue(start, start + int(event.get("dDurationMs", 0)), text))
    for current, following in zip(cues, cues[1:]):
        if current.end > following.start:
            current.end = following.start
    return cues


def _xml_time(value: str | None) -> int | None:
    if not value:
        return None
    value = value.strip()
    if ":" in value:
        parts = value.split(":")
        if len(parts) == 4:  # SS:DD:SS:KARE biçiminde kare bilgisi atılır
            value = ":".join(parts[:3])
        return _clock_to_ms(value)
    for suffix, factor in (("ms", 1), ("s", 1000), ("m", 60000), ("h", 3600000)):
        if value.endswith(suffix):
            return int(float(value[: -len(suffix)]) * factor)
    return None


def _element_text(element: ET.Element) -> str:
    parts = [element.text or ""]
    for child in element:
        if child.tag.rsplit("}", 1)[-1] == "br":
            parts.append("\n")
        else:
            parts.append(_element_text(child))
        parts.append(child.tail or "")
    return "".join(parts)


def parse_xml(data: str) -> list[Cue]:
    """TTML/DFXP ile YouTube srv1, srv2, srv3 biçimlerini çözer."""
    try:
        root = ET.fromstring(data.lstrip("﻿"))
    except ET.ParseError as exc:
        raise SubtitleParseError("XML altyazı çözülemedi") from exc
    cues: list[Cue] = []
    for element in root.iter():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag == "text":  # srv1: saniye cinsinden start ve dur
            start = int(float(element.get("start", "0")) * 1000)
            end = start + int(float(element.get("dur", "0")) * 1000)
        elif tag == "p" and element.get("t") is not None:  # srv3: milisaniye
            start = int(element.get("t", "0"))
            end = start + int(element.get("d", "0"))
        elif tag == "p":  # TTML
            begin = _xml_time(element.get("begin"))
            if begin is None:
                continue
            start = begin
            finish = _xml_time(element.get("end"))
            duration = _xml_time(element.get("dur"))
            end = finish if finish is not None else start + (duration or 0)
        else:
            continue
        text = _clean_text(_element_text(element))
        if text:
            cues.append(Cue(start, end, text))
    return cues


def parse_ass(data: str) -> list[Cue]:
    """ASS/SSA içindeki Dialogue satırlarını çözer."""
    cues: list[Cue] = []
    for line in data.lstrip("﻿").splitlines():
        if not line.startswith("Dialogue:"):
            continue
        fields = line.split(":", 1)[1].split(",", 9)
        if len(fields) < 10:
            continue
        text = _clean_text(_ASS_OVERRIDE.sub("", fields[9]).replace("\\N", "\n").replace("\\n", "\n"))
        if text:
            cues.append(Cue(_clock_to_ms(fields[1].strip()), _clock_to_ms(fields[2].strip()), text))
    return cues


def parse(data: str, ext: str) -> list[Cue]:
    """Uzantıya göre altyazıyı çözer. Sonuç yoksa SubtitleParseError yükseltir."""
    ext = (ext or "").lower()
    if ext == "json3":
        cues = parse_json3(data)
    elif ext in {"ttml", "dfxp", "xml", "srv1", "srv2", "srv3"}:
        cues = parse_xml(data)
    elif ext in {"ass", "ssa"}:
        cues = parse_ass(data)
    elif ext in {"vtt", "srt", "webvtt"}:
        cues = parse_timed_text(data)
    else:
        raise SubtitleParseError(f"Desteklenmeyen altyazı biçimi: {ext}")
    if not cues:
        raise SubtitleParseError("Altyazıda metin bulunamadı")
    return cues


def collapse_rolling(cues: list[Cue]) -> list[Cue]:
    """Otomatik altyazılarda kayarak tekrar eden satırları temizler."""
    result: list[Cue] = []
    previous_lines: list[str] = []
    for cue in cues:
        lines = cue.text.split("\n")
        while lines and lines[0] in previous_lines:
            lines.pop(0)
        if lines:
            result.append(Cue(cue.start, cue.end, "\n".join(lines)))
            previous_lines = cue.text.split("\n")
        elif result:
            result[-1].end = max(result[-1].end, cue.end)
    return result


def _clock(ms: int, separator: str) -> str:
    seconds, millis = divmod(max(ms, 0), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}{separator}{millis:03}"


def to_srt(cues: list[Cue]) -> str:
    blocks = [
        f"{number}\n{_clock(cue.start, ',')} --> {_clock(cue.end, ',')}\n{cue.text}"
        for number, cue in enumerate(cues, 1)
    ]
    return "\n\n".join(blocks) + "\n"


def to_vtt(cues: list[Cue]) -> str:
    blocks = [f"{_clock(cue.start, '.')} --> {_clock(cue.end, '.')}\n{cue.text}" for cue in cues]
    return "WEBVTT\n\n" + "\n\n".join(blocks) + "\n"


def to_txt(cues: list[Cue]) -> str:
    lines: list[str] = []
    for cue in cues:
        for line in cue.text.split("\n"):
            if not lines or lines[-1] != line:
                lines.append(line)
    return "\n".join(lines) + "\n"


def to_timed_txt(cues: list[Cue]) -> str:
    lines = []
    for cue in cues:
        stamp = _clock(cue.start, ".")[:8]
        lines.append(f"[{stamp}] " + cue.text.replace("\n", " "))
    return "\n".join(lines) + "\n"


WRITERS = {
    "srt": (to_srt, "srt"),
    "vtt": (to_vtt, "vtt"),
    "txt": (to_txt, "txt"),
    "timed": (to_timed_txt, "txt"),
}


def merge_dual(primary: list[Cue], secondary: list[Cue]) -> list[Cue]:
    """Her ana satırın altına, zamanı en çok çakışan ikinci dil metnini ekler."""
    merged: list[Cue] = []
    for cue in primary:
        overlapping = [
            other.text
            for other in secondary
            if min(cue.end, other.end) - max(cue.start, other.start) > 0
        ]
        unique = list(dict.fromkeys(overlapping))
        text = cue.text + ("\n" + " ".join(line.replace("\n", " ") for line in unique) if unique else "")
        merged.append(Cue(cue.start, cue.end, text))
    return merged


_INVALID_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}


def safe_filename(name: str, fallback: str = "altyazi", limit: int = 150) -> str:
    """Windows'ta geçerli bir dosya adı parçası üretir."""
    cleaned = _INVALID_NAME.sub(" ", name or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")[:limit].strip(" .")
    if not cleaned or cleaned.split(".")[0].upper() in _RESERVED:
        return fallback
    return cleaned
