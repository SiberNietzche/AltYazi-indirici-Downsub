import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from altyazi import engine  # noqa: E402
from altyazi.engine import Engine, EngineError, Session, _build_tracks  # noqa: E402

BASE = "https://www.youtube.com/api/timedtext?v=x&fmt=json3"
JSON3 = b'{"events": [{"tStartMs": 0, "dDurationMs": 1000, "segs": [{"utf8": "merhaba"}]}]}'


def fmt(query):
    return [{"ext": "json3", "url": f"{BASE}&{query}", "name": "x"}]


INFO = {
    "title": "Deneme",
    "subtitles": {"de": fmt("lang=de")},
    "automatic_captions": {
        "en-orig": fmt("lang=en&kind=asr"),
        "en": fmt("lang=en&kind=asr"),
        "tr": fmt("lang=en&kind=asr&tlang=tr"),
    },
}


class FakeYDL:
    """Çeviri isteklerine (tlang) 429, ötekilere altyazı döndürür; istekleri sayar."""

    def __init__(self, block_all=False):
        self.requests = []
        self.block_all = block_all

    def urlopen(self, request):
        self.requests.append(request.url)
        if self.block_all or "tlang=" in request.url:
            raise Exception("HTTP Error 429: Too Many Requests")
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = JSON3
        return response

    def close(self):
        pass


class TranslationBlockedTests(unittest.TestCase):
    def setUp(self):
        self.engine = Engine()
        self.ydl = FakeYDL()
        self.session = Session("s", "https://www.youtube.com/watch?v=x", INFO, self.ydl, _build_tracks(INFO))
        self.engine._sessions["s"] = self.session
        sleep = mock.patch.object(engine.time, "sleep")
        self.sleep = sleep.start()
        self.addCleanup(sleep.stop)
        refresh = mock.patch.object(Engine, "refresh", side_effect=AssertionError("tazelenmemeli"))
        self.refresh = refresh.start()
        self.addCleanup(refresh.stop)

    def test_translation_429_fails_at_once_and_offers_the_original(self):
        with self.assertRaises(EngineError) as caught:
            self.engine.render("s", "auto:tr", "srt")
        error = caught.exception
        self.assertEqual(error.code, "translation_blocked")
        self.assertFalse(error.retryable)
        self.assertEqual((error.params["lang"], error.params["source"], error.params["source_lang"]), ("tr", "auto:en-orig", "en-orig"))
        self.assertEqual(len(self.ydl.requests), 1)  # Bekleyip yeniden denemez
        self.sleep.assert_not_called()
        self.refresh.assert_not_called()

    def test_original_still_downloads(self):
        data, ext, _ = self.engine.render("s", "auto:en-orig", "srt")
        self.assertIn("merhaba", data.decode())

    def test_translation_of_manual_track_offers_manual_source(self):
        info = dict(INFO, automatic_captions={"tr": fmt("lang=de&tlang=tr")})
        self.session.tracks = _build_tracks(info)
        with self.assertRaises(EngineError) as caught:
            self.engine.render("s", "auto:tr", "srt")
        self.assertEqual(caught.exception.params["source"], "manual:de")

    def test_other_429_keeps_waiting_and_refreshing(self):
        self.session.ydl = FakeYDL(block_all=True)
        self.refresh.side_effect = None
        with self.assertRaises(EngineError) as caught:
            self.engine.render("s", "auto:en-orig", "srt")
        self.assertEqual(caught.exception.code, "rate_limited")
        self.assertEqual([c.args[0] for c in self.sleep.call_args_list], [5, 15, 5])
        self.refresh.assert_called_once()

    def test_dual_with_blocked_translation_names_it(self):
        with self.assertRaises(EngineError) as caught:
            self.engine.render("s", "manual:de", "srt", second_key="auto:tr")
        self.assertEqual((caught.exception.code, caught.exception.params["lang"]), ("translation_blocked", "tr"))


if __name__ == "__main__":
    unittest.main()
