#!/usr/bin/env bash
# Derlenen DMG'yi internetten inmiş gibi kurar; motoru ve uygulamayı birkaç kez açıp süreleri ölçer.
set -uo pipefail
APP=/Applications/AltyaziIndirici.app
SERVER="$APP/Contents/MacOS/altyazi-server"
sw_vers | grep ProductVersion; uname -m
python3 -c 'import socket,time; t=time.time(); socket.getfqdn("127.0.0.1"); print(f"getfqdn bu makinede {time.time()-t:.1f} sn")'
dmg=$(ls dmg/*.dmg); shasum -a 256 "$dmg"
xattr -w com.apple.quarantine "0083;$(printf %x "$(date +%s)");Safari;$(uuidgen)" "$dmg"
hdiutil attach -nobrowse -mountpoint /Volumes/AI "$dmg" >/dev/null
ditto /Volumes/AI/AltyaziIndirici.app "$APP"; hdiutil detach /Volumes/AI >/dev/null

run() {
  local name=$1; shift; local port=$((8700 + RANDOM % 200)) start ready=""
  start=$(date +%s)
  (sleep 100 | "$@" "$SERVER" --serve --exit-with-stdin --port "$port" --token t >/dev/null 2>&1) &
  for _ in $(seq 1 90); do
    curl -s -o /dev/null "http://127.0.0.1:$port/?token=t" && { ready=$(( $(date +%s) - start )); break; }
    sleep 1
  done
  echo "SONUÇ $name: ${ready:-AÇILMADI} saniye"
  pkill -f "altyazi-server --serve" || true; sleep 2
}
for n in 1 2 3 4; do run "motor-$n"; done
arch -x86_64 /usr/bin/true 2>/dev/null || softwareupdate --install-rosetta --agree-to-license >/dev/null 2>&1
run rosetta arch -x86_64

xattr -dr com.apple.quarantine "$APP"
for n in 1 2; do
  open "$APP"; start=$(date +%s); ok=""
  for _ in $(seq 1 75); do
    lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | grep -q altyazi && { ok=$(( $(date +%s) - start )); break; }
    sleep 1
  done
  echo "SONUÇ uygulama-$n: ${ok:-AÇILMADI} saniye"
  pkill -f AltyaziIndirici || true; pkill -f altyazi-server || true; sleep 3
done
