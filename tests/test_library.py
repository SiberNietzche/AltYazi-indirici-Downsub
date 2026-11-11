import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from altyazi import engine as engine_module  # noqa: E402
from altyazi.engine import Engine, EngineError, Session, _friendly_error  # noqa: E402
from altyazi.library import Library  # noqa: E402


def fake_trash(path):
    os.remove(path)
    return True


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.state = base / "state" / "files.json"
        self.folder = base / "downloads"
        (self.folder / "liste").mkdir(parents=True)
        (self.folder / "derin" / "ic").mkdir(parents=True)
        for name in ["a.srt", "b.vtt", "video.mp4", "notlar.txt", "liste/c.srt", "derin/ic/d.srt"]:
            (self.folder / name).write_text("x", "utf-8")
        self.library = Library(self.state, trash=fake_trash)

    def names(self, library=None):
        return sorted((library or self.library).listing(self.folder)["files"], key=lambda f: f["name"])

    def test_lists_only_subtitles_one_level_deep(self):
        self.assertEqual([f["name"] for f in self.names()], ["a.srt", "b.vtt", "c.srt"])
        self.assertEqual([f["folder"] for f in self.names()], ["", "", "liste"])

    def test_txt_listed_only_when_written_by_app(self):
        self.library.record_written(self.folder / "notlar.txt")
        self.assertIn("notlar.txt", [f["name"] for f in self.names()])

    def test_hide_and_restore_survive_restart(self):
        self.library.hide(self.folder, [str(self.folder / "a.srt")])
        reopened = Library(self.state, trash=fake_trash)
        listing = reopened.listing(self.folder)
        self.assertEqual(listing["hidden"], 1)
        self.assertNotIn("a.srt", [f["name"] for f in listing["files"]])
        self.assertTrue((self.folder / "a.srt").exists())
        reopened.restore(self.folder)
        self.assertEqual(reopened.listing(self.folder)["hidden"], 0)

    def test_redownload_unhides(self):
        path = self.folder / "a.srt"
        self.library.hide(self.folder, [str(path)])
        self.library.record_written(path)
        self.assertIn("a.srt", [f["name"] for f in self.names()])

    def test_delete_removes_files_and_empty_playlist_folder(self):
        result = self.library.delete(self.folder, [str(self.folder / "a.srt"), str(self.folder / "liste" / "c.srt")])
        self.assertEqual(result, {"deleted": 2, "failed": []})
        self.assertFalse((self.folder / "a.srt").exists())
        self.assertFalse((self.folder / "liste").exists())
        self.assertTrue((self.folder / "video.mp4").exists())

    def test_refuses_anything_not_listed(self):
        outside = Path(self.temp.name) / "gizli.srt"
        outside.write_text("x", "utf-8")
        for bad in [outside, self.folder / "video.mp4", self.folder / "notlar.txt", self.folder / "derin" / "ic" / "d.srt",
                    self.folder / "liste" / ".." / ".." / "gizli.srt"]:
            with self.assertRaises(EngineError) as caught:
                self.library.delete(self.folder, [str(bad)])
            self.assertEqual(caught.exception.code, "not_listed")
            self.assertTrue(Path(bad).exists())
        with self.assertRaises(EngineError):
            self.library.hide(self.folder, [5])

    def test_failed_trash_is_reported_and_kept(self):
        library = Library(self.state, trash=lambda path: False)
        result = library.delete(self.folder, [str(self.folder / "a.srt")])
        self.assertEqual(result, {"deleted": 0, "failed": ["a.srt"]})
        self.assertTrue((self.folder / "a.srt").exists())

    def test_corrupt_state_file_ignored(self):
        self.state.parent.mkdir(parents=True, exist_ok=True)
        self.state.write_text("{bozuk", "utf-8")
        self.assertEqual(len(self.names(Library(self.state, trash=fake_trash))), 3)


class RefreshRetryTests(unittest.TestCase):
    def setUp(self):
        self.engine = Engine()
        self.session = Session("s", "https://x.y/z", {"title": "t"}, None, {"manual:en": {"lang": "en"}})
        self.engine._sessions["s"] = self.session
        self.refreshed = 0

        def refresh(_session_id):
            self.refreshed += 1

        self.engine.refresh = refresh

    def test_retryable_failure_refreshes_once_then_succeeds(self):
        calls = []

        def action(delays):
            calls.append(delays)
            if len(calls) == 1:
                raise EngineError("rate_limited", retryable=True)
            return "ok"

        self.assertEqual(self.engine._with_refresh(self.session, action), "ok")
        self.assertEqual(self.refreshed, 1)
        self.assertEqual(calls, [engine_module._FIRST_TRY_DELAYS, engine_module._AFTER_REFRESH_DELAYS])

    def test_second_failure_is_not_retried_again(self):
        def action(_delays):
            raise EngineError("not_found", retryable=True)

        with self.assertRaises(EngineError) as caught:
            self.engine._with_refresh(self.session, action)
        self.assertEqual(caught.exception.code, "not_found")
        self.assertEqual(self.refreshed, 1)

    def test_permanent_failure_skips_refresh(self):
        def action(_delays):
            raise EngineError("drm")

        with self.assertRaises(EngineError):
            self.engine._with_refresh(self.session, action)
        self.assertEqual(self.refreshed, 0)

    def test_original_error_kept_when_refresh_fails(self):
        def refresh(_session_id):
            raise EngineError("no_info")

        self.engine.refresh = refresh

        def action(_delays):
            raise EngineError("rate_limited", retryable=True)

        with self.assertRaises(EngineError) as caught:
            self.engine._with_refresh(self.session, action)
        self.assertEqual(caught.exception.code, "rate_limited")

    def test_error_classification(self):
        cases = {"This video has DRM": ("drm", False), "HTTP Error 429: Too Many": ("rate_limited", True),
                 "Unsupported URL: x": ("unsupported_url", False), "HTTP Error 404: Not Found": ("not_found", True),
                 "Sign in to confirm": ("login_required", False), "boom": ("source_error", True)}
        for message, (code, retryable) in cases.items():
            error = _friendly_error(Exception(message))
            self.assertEqual((error.code, error.retryable), (code, retryable), message)


class MessageCoverageTests(unittest.TestCase):
    def test_every_error_code_translated_in_every_locale(self):
        src = ROOT / "src" / "altyazi"
        python = "".join((src / name).read_text("utf-8") for name in ["engine.py", "server.py", "library.py"])
        codes = set(re.findall(r'EngineError\(\s*"(\w+)"', python))
        self.assertGreater(len(codes), 15)
        messages = (src / "web" / "i18n.js").read_text("utf-8")
        blocks = re.findall(r"errors: \{(.*?)\n    \},", messages, re.S)
        self.assertEqual(len(blocks), 3)
        for block in blocks:
            defined = set(re.findall(r"(\w+): ['\"]", block))
            self.assertEqual(codes - defined, set())

    def test_backend_sends_no_turkish_messages(self):
        src = ROOT / "src" / "altyazi"
        for name in ["engine.py", "server.py", "library.py"]:
            for call in re.findall(r'EngineError\((.*?)\)', (src / name).read_text("utf-8")):
                self.assertNotRegex(call, r"[çğıöşüÇĞİÖŞÜ]", f"{name}: {call}")


if __name__ == "__main__":
    unittest.main()


class FreedesktopTrashTests(unittest.TestCase):
    """Linux çöp kutusu kuralı; yalnızca dosya işlemleri kullandığı için her sistemde sınanır."""

    def setUp(self):
        from altyazi.system import trash_freedesktop

        self.trash_file = trash_freedesktop
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.trash = self.root / "Trash"

    def test_file_moves_with_restore_info_and_same_names_do_not_collide(self):
        for round_number in range(2):
            source = self.root / "film.tr.srt"
            source.write_text(f"altyazı {round_number}", "utf-8")
            self.assertTrue(self.trash_file(str(source), self.trash))
            self.assertFalse(source.exists())
        self.assertEqual(sorted(p.name for p in (self.trash / "files").iterdir()), ["film.tr (1).srt", "film.tr.srt"])
        info = (self.trash / "info" / "film.tr.srt.trashinfo").read_text("utf-8")
        self.assertTrue(info.startswith("[Trash Info]\nPath="))
        self.assertIn("film.tr.srt", info)
        self.assertEqual((self.trash / "files" / "film.tr (1).srt").read_text("utf-8"), "altyazı 1")

    def test_missing_file_is_reported_and_leaves_no_record(self):
        self.assertFalse(self.trash_file(str(self.root / "yok.srt"), self.trash))
        self.assertEqual(list((self.trash / "info").iterdir()), [])
