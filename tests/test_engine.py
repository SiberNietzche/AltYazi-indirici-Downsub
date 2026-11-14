import json
import sys
import unittest
from urllib.parse import parse_qs
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
    """Çeviri isteklerine (tlang) 429, ötekilere altyazı döndürür; istekleri sayar.

    Google Çeviri isteklerini de (translate.http_post yerine) karşılar: her satırın başına "TR:"
    ekler; google=False ise 429 verir.
    """

    def __init__(self, block_all=False, google=True):
        self.requests = []
        self.block_all = block_all
        self.google = google

    def post(self, url, body, headers):
        self.requests.append(url)
        if not self.google:
            raise Exception("HTTP Error 429: Too Many Requests")
        text = parse_qs(body.decode())["q"][0]
        out = "\n".join("TR:" + line for line in text.split("\n"))
        return json.dumps([[out, "en"]] if "clients5" in url else [[[out, text]]]).encode()

    def urlopen(self, request):
        self.requests.append(request.url)
        response = mock.MagicMock()
        if self.block_all or "tlang=" in request.url:
            raise Exception("HTTP Error 429: Too Many Requests")
        response.__enter__.return_value.read.return_value = JSON3
        return response

    def close(self):
        pass


class TranslationBlockedTests(unittest.TestCase):
    def setUp(self):
        self.engine = Engine()
        self.ydl = FakeYDL(google=False)
        self.session = Session("s", "https://www.youtube.com/watch?v=x", INFO, self.ydl, _build_tracks(INFO))
        self.engine._sessions["s"] = self.session
        sleep = mock.patch.object(engine.time, "sleep")
        self.sleep = sleep.start()
        self.addCleanup(sleep.stop)
        refresh = mock.patch.object(Engine, "refresh", side_effect=AssertionError("tazelenmemeli"))
        self.refresh = refresh.start()
        self.addCleanup(refresh.stop)
        post = mock.patch.object(engine.translate, "http_post", side_effect=lambda *a: self.session.ydl.post(*a))
        post.start()
        self.addCleanup(post.stop)

    def test_translation_429_fails_at_once_and_offers_the_original(self):
        with self.assertRaises(EngineError) as caught:
            self.engine.render("s", "auto:tr", "srt")
        error = caught.exception
        self.assertEqual(error.code, "translation_blocked")
        self.assertFalse(error.retryable)
        self.assertEqual((error.params["lang"], error.params["source"], error.params["source_lang"]), ("tr", "auto:en-orig", "en-orig"))
        tlang = [url for url in self.ydl.requests if 'tlang=' in url]
        self.assertEqual(len(tlang), 1)  # YouTube çevirisi beklenip yeniden denenmez
        google = [url for url in self.ydl.requests if 'translate_a' in url]
        self.assertEqual(len(google), 6)  # İki Google uç noktası, iki bekleme, sonra vazgeçilir
        self.assertEqual([c.args[0] for c in self.sleep.call_args_list if c.args[0] >= 5], [5, 15])
        self.refresh.assert_not_called()

    def test_original_still_downloads(self):
        data, ext, _, google = self.engine.render("s", "auto:en-orig", "srt")
        self.assertIn("merhaba", data.decode())
        self.assertFalse(google)

    def test_blocked_translation_falls_back_to_google(self):
        self.session.ydl = FakeYDL()
        data, _, stem, google = self.engine.render("s", "auto:tr", "srt")
        self.assertTrue(google)
        self.assertIn("TR:merhaba", data.decode())
        self.assertTrue(stem.endswith(".tr"))
        self.assertIn("tl=tr", self.session.ydl.requests[-1])
        self.sleep.assert_not_called()  # İlk Google isteği beklemeden gider

    def test_raw_format_does_not_use_google(self):
        self.session.ydl = FakeYDL()
        with self.assertRaises(EngineError) as caught:
            self.engine.render("s", "auto:tr", "raw")
        self.assertEqual(caught.exception.code, "translation_blocked")

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

    def test_dual_uses_google_for_the_blocked_side(self):
        self.session.ydl = FakeYDL()
        data, _, _, google = self.engine.render("s", "manual:de", "srt", second_key="auto:tr")
        self.assertTrue(google)
        self.assertIn("merhaba\nTR:merhaba", data.decode())

    def test_dual_with_blocked_translation_names_it(self):
        with self.assertRaises(EngineError) as caught:
            self.engine.render("s", "manual:de", "srt", second_key="auto:tr")
        self.assertEqual((caught.exception.code, caught.exception.params["lang"]), ("translation_blocked", "tr"))


class PlaylistLinkTests(unittest.TestCase):
    def test_watch_link_with_list_gives_the_playlist(self):
        for url in (
            "https://www.youtube.com/watch?v=abc&list=PLx_1-2&index=3",
            "https://m.youtube.com/watch?v=abc&list=PLx_1-2",
            "https://youtu.be/abc?list=PLx_1-2",
        ):
            self.assertEqual(engine.playlist_link(url), "https://www.youtube.com/playlist?list=PLx_1-2")

    def test_other_links_give_nothing(self):
        for url in (
            "https://www.youtube.com/watch?v=abc",
            "https://example.com/watch?v=abc&list=PLx",
            "https://www.youtube.com/watch?v=abc&list=bad%20id",
        ):
            self.assertIsNone(engine.playlist_link(url))


class DualPlaylistTests(unittest.TestCase):
    def setUp(self):
        self.engine = mock.MagicMock()
        self.engine.open.side_effect = lambda url: {"id": url, "title": url}
        self.engine.pick_track.side_effect = lambda vid, lang, auto: None if lang == "xx" else f"manual:{lang}"
        self.engine.download.return_value = (Path("a.srt"), False)
        patcher = mock.patch.object(engine.time, "sleep")
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_job(self, second):
        jobs = engine.JobManager(self.engine)
        job, cancel = {"done": 0, "saved": 0, "failures": [], "state": "running", "current": ""}, mock.MagicMock()
        cancel.is_set.return_value = False
        jobs._run(job, cancel, ["v1"], "en", "srt", True, Path("out"), second)
        return job

    def test_second_language_is_merged_into_one_file(self):
        job = self.run_job("tr")
        self.assertEqual(job["saved"], 1)
        self.engine.download.assert_called_once_with("v1", "manual:en", "srt", Path("out"), "manual:tr")

    def test_missing_second_language_is_reported(self):
        job = self.run_job("xx")
        self.assertEqual((job["saved"], job["failures"][0]["code"], job["failures"][0]["params"]), (0, "no_language", {"lang": "xx"}))

    def test_single_language_still_works(self):
        self.run_job(None)
        self.engine.download.assert_called_once_with("v1", "manual:en", "srt", Path("out"), None)


if __name__ == "__main__":
    unittest.main()
