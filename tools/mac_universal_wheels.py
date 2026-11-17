"""macOS universal2 derlemesi için derlenmiş Python paketlerini universal2 sürümleriyle değiştirir.

PyInstaller ``--target-arch universal2`` ile tek bir yan süreç hem Apple Silicon (arm64) hem Intel
(x86_64) için çalışır; bunun için içine giren her .so/.dylib dosyasının iki mimariyi de içermesi
gerekir. pip, Apple Silicon'da yalnızca arm64 tekerleğini seçtiği için derlenmiş kod içeren her paket
aynı sürümün universal2 tekerleğiyle yeniden kurulur. Sonunda bütün ikili dosyalar denetlenir;
iki mimariyi içermeyen kalırsa betik hata verir.

Python'un kendisi de universal2 olmalıdır (python.org'daki macOS kurulumu).
"""

import importlib.metadata as metadata
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

WANTED = {"arm64", "x86_64"}
PLATFORMS = [f"macosx_10_{minor}_universal2" for minor in range(9, 16)] + [f"macosx_{major}_0_universal2" for major in range(11, 16)]


def archs(path: Path) -> set[str]:
    result = subprocess.run(["lipo", "-archs", str(path)], capture_output=True, text=True)
    return set(result.stdout.split()) if result.returncode == 0 else set()


def thin_files(dist) -> list[Path]:
    files = []
    for entry in dist.files or []:
        if str(entry).endswith((".so", ".dylib")):
            path = Path(dist.locate_file(entry))
            if path.exists() and not WANTED <= archs(path):
                files.append(path)
    return files


def main() -> int:
    if not sysconfig.get_platform().endswith("universal2"):
        print(f"Python universal2 değil ({sysconfig.get_platform()}); python.org'daki macOS kurulumunu kullanın.")
        return 1
    version = f"{sys.version_info.major}{sys.version_info.minor}"
    for dist in metadata.distributions():
        if not thin_files(dist):
            continue
        name, release = dist.metadata["Name"], dist.version
        print(f"universal2: {name}=={release}")
        with tempfile.TemporaryDirectory() as folder:
            command = [sys.executable, "-m", "pip", "download", "--quiet", "--no-deps", "--only-binary=:all:",
                       "--python-version", version, "--implementation", "cp",
                       "--abi", f"cp{version}", "--abi", "abi3", "--abi", "none", "--dest", folder]
            for platform in PLATFORMS:
                command += ["--platform", platform]
            subprocess.run(command + [f"{name}=={release}"], check=True)
            wheels = list(Path(folder).glob("*.whl"))
            subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--no-deps", "--force-reinstall", *map(str, wheels)], check=True)
    remaining = [path for dist in metadata.distributions() for path in thin_files(dist)]
    for path in remaining:
        print(f"iki mimariyi içermiyor: {path} ({' '.join(sorted(archs(path))) or '?'})")
    return 1 if remaining else 0


if __name__ == "__main__":
    sys.exit(main())
