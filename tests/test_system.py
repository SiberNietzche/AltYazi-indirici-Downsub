import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from altyazi import APP_DIR_NAME, main, system  # noqa: E402


class PlatformTests(unittest.TestCase):
    def test_platform_names(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ALTYAZI_PLATFORM", None)
            for value, expected in (("win32", "windows"), ("darwin", "macos"), ("linux", "linux")):
                with mock.patch.object(system.sys, "platform", value):
                    self.assertEqual(system.platform_name(), expected)

    def test_macos_data_dir(self):
        with mock.patch.object(system, "PLATFORM", "macos"), mock.patch.dict(os.environ, {"ALTYAZI_DATA_DIR": ""}):
            self.assertEqual(system.data_dir(), Path.home() / "Library" / "Application Support" / APP_DIR_NAME)

    def test_macos_path_gets_homebrew(self):
        with mock.patch.object(system, "PLATFORM", "macos"), mock.patch.dict(os.environ, {"PATH": os.pathsep.join(["/usr/bin", "/bin"])}):
            main._extend_path()
            self.assertEqual(os.environ["PATH"].split(os.pathsep), ["/usr/bin", "/bin", "/opt/homebrew/bin", "/usr/local/bin"])

    def test_other_platforms_keep_path(self):
        with mock.patch.object(system, "PLATFORM", "windows"), mock.patch.dict(os.environ, {"PATH": "C:\\Windows"}):
            main._extend_path()
            self.assertEqual(os.environ["PATH"], "C:\\Windows")


if __name__ == "__main__":
    unittest.main()
