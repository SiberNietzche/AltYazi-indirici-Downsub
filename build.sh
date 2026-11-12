#!/usr/bin/env bash
# Linux derlemesi: testleri çalıştırır, Python motorunu yan süreç olarak paketler ve Tauri
# uygulamasını derler. Çıktı: src-tauri/target/release/bundle altında .deb ve .AppImage.
# Kurulum dosyası istenmiyorsa: ./build.sh --no-bundle
#
# Gerekenler: Python 3.11+, Rust, Node.js ve Tauri'nin sistem kitaplıkları. Debian/Ubuntu için:
#   sudo apt install build-essential curl wget file libwebkit2gtk-4.1-dev libssl-dev \
#     libxdo-dev libayatana-appindicator3-dev librsvg2-dev python3-venv
#
# Uyumluluk: program, derlendiği sistemin glibc sürümünü ve daha yenisini ister. Ubuntu 22.04'te
# (glibc 2.35) derlenen paket Ubuntu 22.04, 24.04 ve sonrasında, Debian 12'de ve Mint 21+'da çalışır;
# daha yeni bir sistemde derlenen paket eskilerde açılmaz. Dağıtılacak paketi bu yüzden Ubuntu 22.04'te
# derleyin (GitHub Actions iş akışı da öyle yapar). Ubuntu 22.04'ün Python'u 3.10'dur; 3.11 kurup
# PYTHON=python3.11 ./build.sh ile verin.
set -euo pipefail
cd "$(dirname "$0")"

glibc=$(ldd --version | head -1 | awk '{print $NF}')
if [ "$(printf '%s\n' "$glibc" 2.35 | sort -V | tail -1)" != 2.35 ]; then
  echo "UYARI: glibc $glibc; bu paket Ubuntu 22.04 ve 24.04'te açılmaz (yukarıdaki uyumluluk notuna bakın)." >&2
fi

[ -x .venv/bin/python ] || "${PYTHON:-python3}" -m venv .venv
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
  # Dağıtım dosyaları her sistemde aynı düzende adlandırılıp dist klasörüne kopyalanır:
  # AltyaziIndirici_<sürüm>_<sistem>.<uzantı>
  version=$(sed -n 's/.*"version": "\([^"]*\)".*/\1/p' src-tauri/tauri.conf.json | head -1)
  mkdir -p dist
  cp src-tauri/target/release/bundle/deb/*.deb "dist/AltyaziIndirici_${version}_linux.deb"
  cp src-tauri/target/release/bundle/appimage/*.AppImage "dist/AltyaziIndirici_${version}_linux.AppImage"
  ls -l "dist/AltyaziIndirici_${version}_linux.deb" "dist/AltyaziIndirici_${version}_linux.AppImage"
fi
ls -l src-tauri/target/release/altyazi-indirici
