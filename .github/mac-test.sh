#!/usr/bin/env bash
# Yayımlanan macOS DMG'sini gerçek kullanıcı gibi kurar ve altyazı motorunun açılıp açılmadığını sınar.
set -uo pipefail
OUT="$PWD/sonuc"; mkdir -p "$OUT"
URL="https://github.com/SiberNietzche/AltYazi-indirici-Downsub/releases/download/v1.0.1/AltyaziIndirici_1.0.1_macos.dmg"
APP=/Applications/AltyaziIndirici.app
SERVER="$APP/Contents/MacOS/altyazi-server"
LIMIT=120

echo "== Sistem"; sw_vers; uname -m; sysctl -n machdep.cpu.brand_string; spctl --status || true

echo "== İndir, internetten inmiş gibi işaretle, kur"
curl -fsSL -o app.dmg "$URL"
xattr -w com.apple.quarantine "0083;$(printf %x "$(date +%s)");Safari;$(uuidgen)" app.dmg
hdiutil attach -nobrowse -mountpoint /Volumes/AI app.dmg >/dev/null
ditto /Volumes/AI/AltyaziIndirici.app "$APP"
hdiutil detach /Volumes/AI >/dev/null
xattr -l "$APP" | head; xattr -l "$SERVER" | head
spctl -a -vv "$APP" 2>&1 || true
codesign -dv "$SERVER" 2>&1 | head -5

# $1: ad, geri kalanı: komutun önüne eklenecekler (ör. arch -x86_64)
run_server() {
  local name=$1; shift
  local port=$((8700 + RANDOM % 200)) start ready=""
  echo "== Motor tek başına: $name (kapı $port)"
  start=$(date +%s)
  (sleep $((LIMIT + 10)) | "$@" "$SERVER" --serve --exit-with-stdin --port "$port" --token t \
     >"$OUT/$name.out" 2>"$OUT/$name.err"; echo "çıkış kodu=$?" >>"$OUT/$name.out") &
  for _ in $(seq 1 $LIMIT); do
    if curl -s -o /dev/null "http://127.0.0.1:$port/?token=t"; then ready=$(( $(date +%s) - start )); break; fi
    if grep -q "çıkış kodu" "$OUT/$name.out" 2>/dev/null; then break; fi
    sleep 1
  done
  if [ -n "$ready" ]; then
    echo "SONUÇ $name: HAZIR, ${ready} saniye"
    curl -s "http://127.0.0.1:$port/?token=t" | head -c 200; echo
  else
    echo "SONUÇ $name: AÇILMADI ($(( $(date +%s) - start )) saniye sonra)"
  fi
  pkill -f "altyazi-server --serve" || true; sleep 2
  echo "-- stdout"; cat "$OUT/$name.out"; echo "-- stderr"; tail -40 "$OUT/$name.err"
}

run_server karantinali
run_server ikinci-acilis
if [ "$(uname -m)" = arm64 ]; then
  arch -x86_64 /usr/bin/true 2>/dev/null || softwareupdate --install-rosetta --agree-to-license >/dev/null 2>&1
  run_server rosetta arch -x86_64
fi

echo "== Uygulamayı Finder'dan açılmış gibi aç"
xattr -dr com.apple.quarantine "$APP"  # kullanıcı "Yine de Aç" demiş gibi
open "$APP"; start=$(date +%s); ok=""
for _ in $(seq 1 75); do
  if lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | grep -q altyazi; then ok=$(( $(date +%s) - start )); break; fi
  sleep 1
done
[ -n "$ok" ] && echo "SONUÇ uygulama: motor ${ok} saniyede dinlemeye başladı" || echo "SONUÇ uygulama: motor 75 saniyede dinlemeye başlamadı"
ps -axo pid,etime,command | grep -i altyazi | grep -v grep
sleep 5; screencapture -x "$OUT/ekran.png" || true
pkill -f AltyaziIndirici || true; pkill -f altyazi || true

echo "== Sistem günlüğü (öldürme, imza, Gatekeeper)"
log show --last 10m --style compact --predicate \
  '(eventMessage CONTAINS[c] "altyazi") OR (process == "kernel" AND eventMessage CONTAINS[c] "signature")' \
  2>/dev/null | tail -80 | tee "$OUT/gunluk.txt"
ls ~/Library/Logs/DiagnosticReports/ 2>/dev/null | grep -i altyazi && cp ~/Library/Logs/DiagnosticReports/*altyazi* "$OUT/" 2>/dev/null
exit 0
