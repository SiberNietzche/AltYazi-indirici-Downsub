#!/usr/bin/env bash
# macOS derlemesi: testleri çalıştırır, Python motorunu universal2 (Apple Silicon + Intel) yan süreç
# olarak paketler ve Tauri uygulamasını universal olarak derler.
# Çıktı: dist/AltyaziIndirici_<sürüm>_macos.dmg (tek dosya, iki mimari).
#
# Gerekenler (bir Mac'te ya da GitHub Actions'ın macOS makinesinde):
#   - python.org'daki macOS kurulumuyla gelen universal2 Python 3.11; PYTHON=... ile verin, örneğin
#     PYTHON=/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11 ./build_macos.sh
#   - Rust ve iki hedef: rustup target add aarch64-apple-darwin x86_64-apple-darwin
#   - Node.js (Tauri komut satırı aracı npx ile indirilir) ve Xcode komut satırı araçları
#
# Uygulama Apple geliştirici kimliğiyle değil, yerel (ad-hoc) imzayla imzalanır: ilk açılışta
# Gatekeeper uyarır, kullanıcı Sistem Ayarları > Gizlilik ve Güvenlik > "Yine de Aç" ile açar.
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11}"
[ -x .venv/bin/python ] || "$PY" -m venv .venv
py=.venv/bin/python

"$py" -m pip install -q --upgrade pip
"$py" -m pip install -q -r requirements.txt
"$py" tools/mac_universal_wheels.py
"$py" -m unittest discover -s tests

mkdir -p src-tauri/binaries
export CARGO_ENCODED_RUSTFLAGS="--remap-path-prefix=$HOME=~"

"$py" -m PyInstaller --noconfirm --clean --onefile --target-arch universal2 \
  --name altyazi-server \
  --distpath build/sidecar --workpath build/sidecar-work --specpath build \
  --paths src \
  --add-data "$PWD/src/altyazi/web:altyazi/web" \
  --collect-all yt_dlp_ejs \
  --collect-submodules yt_dlp \
  run_app.py
lipo -info build/sidecar/altyazi-server
# Tauri her mimarinin derlemesinde kendi adını, birleştirmede universal adını arar; dosya üçünde de aynıdır.
for triple in universal-apple-darwin aarch64-apple-darwin x86_64-apple-darwin; do
  cp build/sidecar/altyazi-server "src-tauri/binaries/altyazi-server-$triple"
done

(cd src-tauri && npx --yes "@tauri-apps/cli@2" build --target universal-apple-darwin)

version=$(sed -n 's/.*"version": "\([^"]*\)".*/\1/p' src-tauri/tauri.conf.json | head -1)
bundle=src-tauri/target/universal-apple-darwin/release/bundle
lipo -info "$bundle"/macos/*.app/Contents/MacOS/* || true
mkdir -p dist
cp "$bundle"/dmg/*.dmg "dist/AltyaziIndirici_${version}_macos.dmg"
ls -l "dist/AltyaziIndirici_${version}_macos.dmg"
