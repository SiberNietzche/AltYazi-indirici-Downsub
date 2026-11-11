import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from altyazi.engine import EngineError  # noqa: E402
from altyazi.server import LOCALES, THEMES, Settings  # noqa: E402

WEB = ROOT / "src" / "altyazi" / "web"


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        # Ayar klasörü her işletim sisteminde aynı yolla sınama klasörüne yönlendirilir.
        patcher = mock.patch.dict(os.environ, {"ALTYAZI_DATA_DIR": str(Path(self.folder.name) / "AltyaziIndirici")})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.path = Path(self.folder.name) / "AltyaziIndirici" / "settings.json"

    def write(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(data if isinstance(data, str) else json.dumps(data), "utf-8")

    def test_defaults(self):
        settings = Settings()
        self.assertEqual((settings.data["theme"], settings.data["locale"]), ("ocean", "tr"))

    def test_old_dark_preference_becomes_graphite(self):
        self.write({"download_dir": "C:\\x", "dark": True, "locale": "tr"})
        settings = Settings()
        self.assertEqual(settings.data["theme"], "graphite")
        self.assertEqual(settings.data["download_dir"], "C:\\x")

    def test_old_light_preference_stays_default(self):
        self.write({"dark": False})
        self.assertEqual(Settings().data["theme"], "ocean")

    def test_saved_values_round_trip(self):
        Settings().update({"theme": "forest", "locale": "ku"})
        settings = Settings()
        self.assertEqual((settings.data["theme"], settings.data["locale"]), ("forest", "ku"))

    def test_invalid_values_rejected(self):
        settings = Settings()
        with self.assertRaises(EngineError):
            settings.update({"theme": "yok"})
        with self.assertRaises(EngineError):
            settings.update({"locale": "xx"})
        self.assertEqual(settings.data["theme"], "ocean")

    def test_corrupt_or_unknown_file_values_ignored(self):
        self.write("{bozuk")
        self.assertEqual(Settings().data["theme"], "ocean")
        self.write({"theme": "yok", "locale": "xx", "download_dir": 5})
        settings = Settings()
        self.assertEqual((settings.data["theme"], settings.data["locale"]), ("ocean", "tr"))
        self.assertIsInstance(settings.data["download_dir"], str)


class WebDataTests(unittest.TestCase):
    def test_theme_ids_match_server(self):
        source = (WEB / "themes.js").read_text("utf-8")
        self.assertEqual(set(re.findall(r"(?:light|dark)\('(\w+)'", source)), THEMES)

    def test_every_locale_names_every_theme(self):
        source = (WEB / "i18n.js").read_text("utf-8")
        blocks = re.findall(r"themes: \{(.*?)\}", source)
        self.assertEqual(len(blocks), len(LOCALES))
        for block in blocks:
            self.assertEqual(set(re.findall(r"(\w+):", block)), THEMES)


if __name__ == "__main__":
    unittest.main()
