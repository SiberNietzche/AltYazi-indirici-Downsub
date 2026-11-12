import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from altyazi import updater  # noqa: E402

FILES = "https://files.pythonhosted.org/packages/x/"
GOOD_INIT = (
    "class YoutubeDL:\n"
    "    def __init__(self, params=None): pass\n"
    "    def __enter__(self): return self\n"
    "    def __exit__(self, *args): return False\n"
)


def wheel(files: dict) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in files.items():
            archive.writestr(name, text)
    return buffer.getvalue()


def fake_yt_dlp(version: str, init: str = GOOD_INIT, ejs: str | None = "0.9.0") -> dict:
    metadata = f"Name: yt-dlp\nVersion: {version}\n"
    if ejs:
        metadata += f'Requires-Dist: yt-dlp-ejs=={ejs}; extra == "default"\n'
    return {
        "yt_dlp/__init__.py": init,
        "yt_dlp/version.py": f"__version__ = {version!r}\n",
        "yt_dlp/networking/__init__.py": "class Request: pass\n",
        f"yt_dlp-{version}.dist-info/METADATA": metadata,
    }


def meta(version: str, filename: str, data: bytes, url: str | None = None, digest: str | None = None) -> bytes:
    return json.dumps({
        "info": {"version": version},
        "urls": [
            {"packagetype": "sdist", "filename": filename.replace("-py3-none-any.whl", ".tar.gz"), "url": FILES + "a.tar.gz",
             "digests": {"sha256": "0" * 64}},
            {"packagetype": "bdist_wheel", "filename": filename, "url": url or FILES + filename,
             "digests": {"sha256": digest or hashlib.sha256(data).hexdigest()}},
        ],
    }).encode()


class Fixture(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.data = Path(self.folder.name) / "AltyaziIndirici"
        patcher = mock.patch.dict(os.environ, {"ALTYAZI_DATA_DIR": str(self.data)})
        patcher.start()
        self.addCleanup(patcher.stop)
        for name, value in (("_active", {"version": "2026.10.26", "source": "bundled"}),
                            ("_status", {"state": "idle", "pending": None, "error": None})):
            patch = mock.patch.dict(getattr(updater, name), value)
            patch.start()
            self.addCleanup(patch.stop)
        self.responses = {}
        self.requested = []
        fetch = mock.patch.object(updater, "_fetch", side_effect=self.fetch)
        fetch.start()
        self.addCleanup(fetch.stop)

    def fetch(self, url, limit):
        self.requested.append(url)
        if url not in self.responses:
            raise OSError("ağ yok")
        return self.responses[url]

    def publish(self, version="9999.1.1", files=None, **options):
        data = wheel(files or fake_yt_dlp(version))
        name = f"yt_dlp-{version}-py3-none-any.whl"
        self.responses[updater.PYPI.format(name="yt-dlp")] = meta(version, name, data, **options)
        self.responses[FILES + name] = data
        ejs = wheel({"yt_dlp_ejs/__init__.py": "", "yt_dlp_ejs-0.9.0.dist-info/METADATA": "Name: yt-dlp-ejs\n"})
        ejs_name = "yt_dlp_ejs-0.9.0-py3-none-any.whl"
        self.responses[updater.PYPI_VERSION.format(name="yt-dlp-ejs", version="0.9.0")] = meta("0.9.0", ejs_name, ejs)
        self.responses[FILES + ejs_name] = ejs

    def state(self):
        path = self.data / "yt-dlp" / "state.json"
        return json.loads(path.read_text("utf-8")) if path.exists() else {}


class VersionTests(unittest.TestCase):
    def test_compare(self):
        self.assertTrue(updater.newer("2026.11.2", "2026.10.26"))
        self.assertTrue(updater.newer("2026.10.26.1", "2026.10.26"))
        self.assertFalse(updater.newer("2026.10.26", "2026.10.26"))
        self.assertFalse(updater.newer("2026.9.1", "2026.10.26"))
        self.assertFalse(updater.newer("2026.11.2.dev0", "2026.10.26"))  # Ön sürümler alınmaz
        self.assertFalse(updater.newer("", "2026.10.26"))
        self.assertTrue(updater.newer("2026.10.26.post1", "2026.10.26"))
        self.assertTrue(updater.newer("2026.10.26.1", "2026.10.26.post1"))
        self.assertFalse(updater.newer("2026.10.26.post1", "2026.10.26.post1"))


class CheckTests(Fixture):
    def test_downloads_verifies_and_unpacks(self):
        self.publish()
        result = updater.check(True)
        self.assertEqual((result["state"], result["pending"]), ("downloaded", "9999.1.1"))
        folder = self.data / "yt-dlp" / "9999.1.1"
        self.assertTrue((folder / "yt_dlp" / "version.py").is_file())
        self.assertTrue((folder / "yt_dlp_ejs" / "__init__.py").is_file())  # yt-dlp'nin istediği sürüm
        self.assertFalse(any(p.name.endswith(".dist-info") for p in folder.iterdir()))
        self.assertEqual(self.state()["version"], "9999.1.1")

    def test_wrong_digest_is_rejected(self):
        self.publish(digest="f" * 64)
        result = updater.check(True)
        self.assertEqual(result["state"], "error")
        self.assertNotIn("version", self.state())
        self.assertEqual([p.name for p in (self.data / "yt-dlp").iterdir()], ["state.json"])

    def test_download_only_from_pypi_file_host(self):
        self.publish(url="https://example.com/yt_dlp-9999.1.1-py3-none-any.whl")
        self.assertEqual(updater.check(True)["state"], "error")
        self.assertFalse(any("example.com" in url for url in self.requested))

    def test_paths_outside_the_folder_are_rejected(self):
        files = fake_yt_dlp("9999.1.1")
        files["yt_dlp/../../evil.py"] = "x"
        self.publish(files=files)
        self.assertEqual(updater.check(True)["state"], "error")
        self.assertFalse((self.data / "evil.py").exists())
        self.assertFalse((self.data / "yt-dlp" / "9999.1.1").exists())

    def test_no_update_when_not_newer(self):
        self.publish(version="2026.10.26")
        self.assertEqual(updater.check(True)["state"], "uptodate")
        self.assertEqual(len(self.requested), 1)  # Yalnızca sürüm bilgisi istendi

    def test_known_bad_version_is_skipped(self):
        self.publish()
        (self.data / "yt-dlp").mkdir(parents=True)
        (self.data / "yt-dlp" / "state.json").write_text(json.dumps({"bad": ["9999.1.1"]}), "utf-8")
        self.assertEqual(updater.check(True)["state"], "uptodate")

    def test_checks_at_most_daily_unless_forced(self):
        self.publish()
        (self.data / "yt-dlp").mkdir(parents=True)
        (self.data / "yt-dlp" / "state.json").write_text(json.dumps({"checked": time.time()}), "utf-8")
        updater.check(True)
        self.assertEqual(self.requested, [])
        self.assertEqual(updater.check(True, force=True)["pending"], "9999.1.1")

    def test_disabled_does_not_connect(self):
        self.publish()
        updater.check(False)
        self.assertEqual(self.requested, [])

    def test_offline_is_harmless(self):
        result = updater.check(True)
        self.assertEqual((result["state"], result["error"]), ("error", "OSError"))


class ActivateTests(unittest.TestCase):
    """Devreye alma yt-dlp modüllerini yüklediği için ayrı bir Python sürecinde sınanır."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.data = Path(self.folder.name) / "AltyaziIndirici"
        self.updates = self.data / "yt-dlp"

    def install(self, version, init=GOOD_INIT):
        target = self.updates / version
        for name, text in fake_yt_dlp(version, init).items():
            if name.startswith("yt_dlp/"):
                path = target / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, "utf-8")
        (self.updates / "state.json").write_text(json.dumps({"version": version}), "utf-8")

    def activate(self):
        script = (
            "import json, sys; sys.path.insert(0, sys.argv[1]);"
            "from altyazi import updater; result = updater.activate();"
            "import yt_dlp.version; print(json.dumps([result, yt_dlp.version.__version__]))"
        )
        env = {**os.environ, "ALTYAZI_DATA_DIR": str(self.data)}
        out = subprocess.run([sys.executable, "-c", script, str(ROOT / "src")], capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        result, loaded = json.loads(out.stdout.strip().splitlines()[-1])
        state = json.loads((self.updates / "state.json").read_text("utf-8")) if (self.updates / "state.json").exists() else {}
        return result, loaded, state

    def test_newer_download_is_used(self):
        self.install("9999.1.1")
        result, loaded, _ = self.activate()
        self.assertEqual((result["source"], result["version"], loaded), ("update", "9999.1.1", "9999.1.1"))

    def test_broken_download_falls_back_and_is_not_retried(self):
        self.install("9999.1.1", init="raise RuntimeError('bozuk')\n")
        result, loaded, state = self.activate()
        self.assertEqual(result["source"], "bundled")
        self.assertEqual(loaded, result["version"])
        self.assertNotEqual(loaded, "9999.1.1")
        self.assertEqual((state.get("version"), state.get("bad")), (None, ["9999.1.1"]))
        self.assertFalse((self.updates / "9999.1.1").exists())

    def test_download_older_than_bundled_is_removed(self):
        self.install("2000.1.1")
        result, loaded, state = self.activate()
        self.assertEqual(result["source"], "bundled")
        self.assertNotEqual(loaded, "2000.1.1")
        self.assertNotIn("version", state)
        self.assertFalse((self.updates / "2000.1.1").exists())


if __name__ == "__main__":
    unittest.main()
