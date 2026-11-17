import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from altyazi import release, updater  # noqa: E402

REPO = f"https://github.com/{release.REPO}"


def github_reply(tag="v1.0.1", **extra):
    data = {
        "tag_name": tag, "draft": False, "prerelease": False,
        "html_url": f"{REPO}/releases/tag/{tag}",
        "assets": [
            {"name": f"AltyaziIndirici_{tag[1:]}_windows.exe", "browser_download_url": f"{REPO}/releases/download/{tag}/w.exe"},
            {"name": f"AltyaziIndirici_{tag[1:]}_android.apk", "browser_download_url": f"{REPO}/releases/download/{tag}/a.apk"},
            {"name": f"AltyaziIndirici_{tag[1:]}_linux.deb", "browser_download_url": f"{REPO}/releases/download/{tag}/l.deb"},
            {"name": f"AltyaziIndirici_{tag[1:]}_macos.dmg", "browser_download_url": f"{REPO}/releases/download/{tag}/m.dmg"},
        ],
    }
    data.update(extra)
    return data


class VersionTests(unittest.TestCase):
    def test_compare(self):
        self.assertTrue(release.newer("v1.0.1", "1.0.0"))
        self.assertTrue(release.newer("1.1", "1.0.9"))
        self.assertFalse(release.newer("v1.0.0", "1.0.0"))
        self.assertFalse(release.newer("v0.9.9", "1.0.0"))
        self.assertFalse(release.newer("nightly", "1.0.0"))


class ReadReleaseTests(unittest.TestCase):
    def test_platform_asset_is_picked(self):
        self.assertTrue(release.read_release(github_reply(), "windows")["download"].endswith("/w.exe"))
        self.assertTrue(release.read_release(github_reply(), "android")["download"].endswith("/a.apk"))
        self.assertTrue(release.read_release(github_reply(), "macos")["download"].endswith("/m.dmg"))

    def test_macos_without_dmg_gets_the_release_page(self):
        data = github_reply()
        data["assets"] = [a for a in data["assets"] if not a["name"].endswith(".dmg")]
        self.assertEqual(release.read_release(data, "macos")["download"], f"{REPO}/releases/tag/v1.0.1")

    def test_linux_gets_the_release_page(self):
        info = release.read_release(github_reply(), "linux")
        self.assertEqual(info, {"latest": "1.0.1", "page": f"{REPO}/releases/tag/v1.0.1", "download": f"{REPO}/releases/tag/v1.0.1"})

    def test_foreign_links_are_ignored(self):
        data = github_reply(html_url="https://evil.example/x")
        data["assets"][0]["browser_download_url"] = "https://evil.example/w.exe"
        info = release.read_release(data, "windows")
        self.assertEqual(info["page"], f"{REPO}/releases/latest")
        self.assertEqual(info["download"], info["page"])

    def test_prerelease_and_bad_tags_are_rejected(self):
        for data in (github_reply(prerelease=True), github_reply(tag="latest")):
            with self.assertRaises(updater.UpdateError):
                release.read_release(data, "windows")


class CheckTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        env = mock.patch.dict(os.environ, {"ALTYAZI_DATA_DIR": folder.name})
        env.start()
        self.addCleanup(env.stop)
        patches = [mock.patch.object(release, "__version__", "1.0.0"), mock.patch.object(release.system, "PLATFORM", "windows")]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.fetch = mock.patch.object(release.updater, "_get_json", return_value=github_reply())
        self.get_json = self.fetch.start()
        self.addCleanup(self.fetch.stop)

    def test_new_version_is_reported(self):
        status = release.check(True)
        self.assertTrue(status["available"])
        self.assertFalse(status["dismissed"])
        self.assertEqual((status["latest"], status["current"]), ("1.0.1", "1.0.0"))
        self.assertTrue(status["download"].endswith("/w.exe"))

    def test_checks_at_most_once_a_day_unless_forced(self):
        release.check(True)
        release.check(True)
        self.assertEqual(self.get_json.call_count, 1)
        release.check(True, force=True)
        self.assertEqual(self.get_json.call_count, 2)

    def test_disabled_does_not_ask_github(self):
        release.check(False)
        self.get_json.assert_not_called()

    def test_dismissed_until_a_newer_release(self):
        release.check(True)
        release.dismiss("1.0.1")
        self.assertTrue(release.status(True)["dismissed"])
        self.get_json.return_value = github_reply("v1.0.2")
        status = release.check(True, force=True)
        self.assertEqual((status["latest"], status["dismissed"]), ("1.0.2", False))

    def test_network_error_keeps_the_program_working(self):
        self.get_json.side_effect = OSError("offline")
        status = release.check(True)
        self.assertEqual((status["state"], status["available"]), ("error", False))

    def test_same_version_is_not_available(self):
        self.get_json.return_value = github_reply("v1.0.0")
        self.assertFalse(release.check(True)["available"])

    def test_open_download_uses_the_browser_on_desktop(self):
        release.check(True)
        with mock.patch.object(release.webbrowser, "open") as browser:
            url = release.open_download()
        browser.assert_called_once_with(url)
        self.assertTrue(url.endswith("/w.exe"))


if __name__ == "__main__":
    unittest.main()
