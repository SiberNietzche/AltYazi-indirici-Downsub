#!/usr/bin/env bash
# Linux derlemesi: testleri çalıştırır, Python motorunu yan süreç olarak paketler ve Tauri
# uygulamasını derler. Çıktı: src-tauri/target/release/bundle altında .deb ve .AppImage.
# Kurulum dosyası istenmiyorsa: ./build.sh --no-bundle
#
# Gerekenler: Python 3.11+, Rust, Node.js ve Tauri'nin sistem kitaplıkları. Debian/Ubuntu için:
#   sudo apt install build-essential curl wget file libwebkit2gtk-4.1-dev libssl-dev \
#     libxdo-dev libayatana-appindicator3-dev librsvg2-dev python3-venv
set -euo pipefail
cd "$(dirname "$0")"

[ -x .venv/bin/python ] || python3 -m venv .venv
py=.venv/bin/python

"$py" -m pip install -q -r requirements.txt
"$py" -m unittest discover -s tests

# Pencere simgesi ve amblem maskesi aynı çizimden üretilir.
mkdir -p src-tauri/icons src-tauri/binaries
"$py" tools/make_icon.py src-tauri/icons/icon.ico src/altyazi/web/laurel.svg src-tauri/icons/icon.png

# Derleyenin ev klasörü programa gömülen kaynak yollarına girmesin.
export CARGO_ENCODED_RUSTFLAGS="--remap-path-prefix=$HOME=~"

# Tauri, yan sürecin dosya adında Rust hedef üçlüsünü bekler.
triple=$(rustc -vV | sed -n 's/^host: //p')

"$py" -m PyInstaller --noconfirm --clean --onefile \
  --name altyazi-server \
  --distpath build/sidecar --workpath build/sidecar-work --specpath build \
  --paths src \
  --add-data "$PWD/src/altyazi/web:altyazi/web" \
  --collect-all yt_dlp_ejs \
  --collect-submodules yt_dlp \
  run_app.py
cp build/sidecar/altyazi-server "src-tauri/binaries/altyazi-server-$triple"

if [ "${1:-}" = "--no-bundle" ]; then
  cargo build --release --manifest-path src-tauri/Cargo.toml
else
  (cd src-tauri && npx --yes "@tauri-apps/cli@2" build)
  ls -l src-tauri/target/release/bundle/deb/*.deb src-tauri/target/release/bundle/appimage/*.AppImage
fi
ls -l src-tauri/target/release/altyazi-indirici
