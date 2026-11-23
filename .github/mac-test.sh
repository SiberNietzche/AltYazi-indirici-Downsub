#!/usr/bin/env bash
# Yayımlanan macOS DMG'sini kurar; motorun açılış süresini ölçer ve gecikmenin nerede olduğunu bulur.
set -uo pipefail
OUT="$PWD/sonuc"; mkdir -p "$OUT"
URL="https://github.com/SiberNietzche/AltYazi-indirici-Downsub/releases/download/v1.0.1/AltyaziIndirici_1.0.1_macos.dmg"
APP=/Applications/AltyaziIndirici.app
SERVER="$APP/Contents/MacOS/altyazi-server"
LIMIT=120

echo "== Sistem"; sw_vers; uname -m; hostname; scutil --get LocalHostName 2>/dev/null

echo "== Ad çözme süreleri (sistem Python'u)"
for i in 1 2 3; do
python3 - <<'EOF'
import socket, time
for name, fn in [("getfqdn(127.0.0.1)", lambda: socket.getfqdn("127.0.0.1")),
                 ("gethostbyaddr(127.0.0.1)", lambda: socket.gethostbyaddr("127.0.0.1")),
                 ("getfqdn()", lambda: socket.getfqdn())]:
    t = time.time()
    try: r = fn()
    except Exception as e: r = repr(e)
    print(f"ZAMAN {name}: {time.time()-t:.2f} sn -> {r}")
EOF
done

curl -fsSL -o app.dmg "$URL"
hdiutil attach -nobrowse -mountpoint /Volumes/AI app.dmg >/dev/null
ditto /Volumes/AI/AltyaziIndirici.app "$APP"
hdiutil detach /Volumes/AI >/dev/null

run_server() {
  local name=$1; shift
  local port=$((8700 + RANDOM % 200)) start ready="" sampled=""
  start=$(date +%s)
  (sleep $((LIMIT + 10)) | "$@" "$SERVER" --serve --exit-with-stdin --port "$port" --token t \
     >"$OUT/$name.out" 2>"$OUT/$name.err"; echo "çıkış kodu=$?" >>"$OUT/$name.out") &
  for _ in $(seq 1 $LIMIT); do
    if curl -s -o /dev/null "http://127.0.0.1:$port/?token=t"; then ready=$(( $(date +%s) - start )); break; fi
    if [ -z "$sampled" ] && [ $(( $(date +%s) - start )) -ge 8 ]; then
      sampled=1
      echo "-- 8. saniyede süreçler:"; ps -axo pid,ppid,etime,command | grep altyazi-server | grep -v grep
      echo "-- açık kapılar:"; lsof -nP -a -c altyazi -i 2>/dev/null
      for pid in $(pgrep -f "altyazi-server --serve"); do
        sample "$pid" 2 -file "$OUT/$name-$pid.sample" >/dev/null 2>&1
        echo "-- $pid yığını (özet):"
        grep -E "getaddrinfo|gethostby|getfqdn|getnameinfo|mdns|DNS|connect|recv|read|select|poll|kevent|inflate|write|open|stat" "$OUT/$name-$pid.sample" | sort | uniq -c | sort -rn | head -15
      done
    fi
    sleep 1
  done
  echo "SONUÇ $name: ${ready:-AÇILMADI} saniye"
  pkill -f "altyazi-server --serve" || true; sleep 2
}

for n in 1 2 3 4 5; do run_server "arm-$n"; done
exit 0
