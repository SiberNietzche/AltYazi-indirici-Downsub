import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from altyazi import subtitles as s  # noqa: E402
from altyazi.engine import EngineError, _build_tracks, _pick_format, validate_url, write_unique  # noqa: E402


VTT = """\ufeffWEBVTT
Kind: captions

NOTE yorum satırı

00:00:01.000 --> 00:00:02.500 align:start
Merhaba <c.yellow>dünya</c> &amp; herkes

cue-2
01:00:03.000 --> 01:00:04.000
İkinci
satır
"""


class ParseTests(unittest.TestCase):
    def test_vtt(self):
        cues = s.parse(VTT, "vtt")
        self.assertEqual(len(cues), 2)
        self.assertEqual((cues[0].start, cues[0].end), (1000, 2500))
        self.assertEqual(cues[0].text, "Merhaba dünya & herkes")
        self.assertEqual(cues[1].start, 3603000)
        self.assertEqual(cues[1].text, "İkinci\nsatır")

    def test_srt_with_crlf(self):
        cues = s.parse("1\r\n00:00:01,000 --> 00:00:02,000\r\nA\r\n\r\n2\r\n00:00:03,000 --> 00:00:04,000\r\nB\r\n", "srt")
        self.assertEqual([c.text for c in cues], ["A", "B"])

    def test_vtt_short_clock(self):
        self.assertEqual(s.parse("WEBVTT\n\n00:05.250 --> 00:06.000\nX\n", "vtt")[0].start, 5250)

    def test_json3_clips_overlap_and_skips_blank(self):
        data = json.dumps({"events": [
            {"tStartMs": 0, "dDurationMs": 5000, "segs": [{"utf8": "bir "}, {"utf8": "iki"}]},
            {"tStartMs": 1000, "dDurationMs": 100, "segs": [{"utf8": "\n"}]},
            {"tStartMs": 2000, "dDurationMs": 1000, "segs": [{"utf8": "üç"}]},
            {"tStartMs": 9000},
        ]})
        cues = s.parse(data, "json3")
        self.assertEqual([c.text for c in cues], ["bir iki", "üç"])
        self.assertEqual(cues[0].end, 2000)

    def test_ttml_with_namespace(self):
        data = ('<tt xmlns="http://www.w3.org/ns/ttml"><body><div>'
                '<p begin="00:00:01.000" end="00:00:02.000">a<br/>b</p>'
                '<p begin="3s" dur="1s"><span>c</span></p></div></body></tt>')
        cues = s.parse(data, "ttml")
        self.assertEqual([c.text for c in cues], ["a\nb", "c"])
        self.assertEqual((cues[1].start, cues[1].end), (3000, 4000))

    def test_srv1_and_srv3(self):
        self.assertEqual(s.parse('<transcript><text start="1.5" dur="2">x &amp;amp; y</text></transcript>', "srv1")[0].start, 1500)
        cue = s.parse('<timedtext><body><p t="100" d="50"><s>a</s><s> b</s></p></body></timedtext>', "srv3")[0]
        self.assertEqual((cue.start, cue.end, cue.text), (100, 150, "a b"))

    def test_ass(self):
        data = "Dialogue: 0,0:00:01.00,0:00:02.50,Default,,0,0,0,,{\\b1}Selam, dünya\\Nalt"
        cue = s.parse(data, "ass")[0]
        self.assertEqual((cue.start, cue.end, cue.text), (1000, 2500, "Selam, dünya\nalt"))

    def test_errors(self):
        with self.assertRaises(s.SubtitleParseError):
            s.parse("WEBVTT\n", "vtt")
        with self.assertRaises(s.SubtitleParseError):
            s.parse("<bozuk", "ttml")
        with self.assertRaises(s.SubtitleParseError):
            s.parse("{bozuk", "json3")
        with self.assertRaises(s.SubtitleParseError):
            s.parse("x", "bilinmeyen")


class WriterTests(unittest.TestCase):
    cues = [s.Cue(1000, 2500, "A\nB"), s.Cue(3661001, 3662000, "C")]

    def test_srt(self):
        self.assertEqual(s.to_srt(self.cues),
                         "1\n00:00:01,000 --> 00:00:02,500\nA\nB\n\n2\n01:01:01,001 --> 01:01:02,000\nC\n")

    def test_vtt_round_trip(self):
        out = s.to_vtt(self.cues)
        self.assertTrue(out.startswith("WEBVTT\n\n00:00:01.000 --> 00:00:02.500"))
        self.assertEqual(s.parse(out, "vtt"), self.cues)

    def test_txt_removes_adjacent_duplicates(self):
        self.assertEqual(s.to_txt([s.Cue(0, 1, "x"), s.Cue(1, 2, "x\ny")]), "x\ny\n")

    def test_timed(self):
        self.assertEqual(s.to_timed_txt(self.cues), "[00:00:01] A B\n[01:01:01] C\n")

    def test_collapse_rolling(self):
        cues = [s.Cue(0, 1000, "bir"), s.Cue(1000, 1010, "bir"), s.Cue(1010, 2000, "bir\niki"), s.Cue(2000, 3000, "iki\nüç")]
        self.assertEqual([c.text for c in s.collapse_rolling(cues)], ["bir", "iki", "üç"])

    def test_merge_dual(self):
        merged = s.merge_dual([s.Cue(0, 1000, "hello"), s.Cue(5000, 6000, "alone")],
                              [s.Cue(500, 1500, "mer\nhaba"), s.Cue(1000, 1200, "yok")])
        self.assertEqual(merged[0].text, "hello\nmer haba")
        self.assertEqual(merged[1].text, "alone")


class FileTests(unittest.TestCase):
    def test_safe_filename(self):
        self.assertEqual(s.safe_filename('a<b>:c/d\\e|f?*"g. '), "a b c d e f g")
        self.assertEqual(s.safe_filename("CON"), "altyazi")
        self.assertEqual(s.safe_filename("..."), "altyazi")
        self.assertEqual(s.safe_filename("..\\..\\x"), "x")
        self.assertLessEqual(len(s.safe_filename("x" * 500)), 150)

    def test_write_unique_never_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            first = write_unique(Path(folder), "a", "srt", b"1")
            second = write_unique(Path(folder), "a", "srt", b"2")
            self.assertEqual(first.read_bytes(), b"1")
            self.assertEqual(second.name, "a (1).srt")


class EngineHelpersTests(unittest.TestCase):
    def test_validate_url(self):
        self.assertEqual(validate_url(" youtu.be/x "), "https://youtu.be/x")
        for bad in ["", "file:///c:/x", "ftp://a.b/c", "merhaba"]:
            with self.assertRaises(EngineError):
                validate_url(bad)

    def test_build_tracks_classifies_translations(self):
        tracks = _build_tracks({
            "subtitles": {"tr": [{"ext": "vtt", "name": "Türkçe"}], "live_chat": [{"ext": "json"}]},
            "automatic_captions": {
                "en-orig": [{"ext": "vtt", "name": "English (Original)"}],
                "en": [{"ext": "vtt"}],
                "de": [{"ext": "vtt"}],
            },
        })
        self.assertEqual(set(tracks), {"manual:tr", "auto:en-orig", "auto:en", "auto:de"})
        self.assertEqual(tracks["auto:en-orig"]["kind"], "auto")
        self.assertEqual(tracks["auto:en"]["kind"], "auto")
        self.assertEqual(tracks["auto:de"]["kind"], "translated")

    def test_pick_format_priority(self):
        self.assertEqual(_pick_format([{"ext": "srv1"}, {"ext": "vtt"}, {"ext": "json3"}])["ext"], "json3")
        self.assertEqual(_pick_format([{"ext": "vtt", "protocol": "m3u8_native"}, {"ext": "ttml"}])["ext"], "ttml")


if __name__ == "__main__":
    unittest.main()
