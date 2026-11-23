#!/usr/bin/env bash
# Motoru kaynak koddan eski ve yeni server.py ile başlatıp açılış süresini karşılaştırır.
set -uo pipefail
sw_vers | grep ProductVersion; uname -m
python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
.venv/bin/python -m unittest discover -s tests 2>&1 | tail -2
cp src/altyazi/server.py .github/server_yeni.py

run() {
  local name=$1 port=$((8700 + RANDOM % 200)) start ready=""
  start=$(date +%s)
  (sleep 150 | .venv/bin/python run_app.py --serve --exit-with-stdin --port "$port" --token t >/dev/null 2>&1) &
  for _ in $(seq 1 140); do
    curl -s -o /dev/null "http://127.0.0.1:$port/?token=t" && { ready=$(( $(date +%s) - start )); break; }
    sleep 1
  done
  echo "SONUÇ $name: ${ready:-AÇILMADI} saniye"
  pkill -f "run_app.py --serve" || true; sleep 2
}
cp .github/server_eski.py src/altyazi/server.py
for n in 1 2; do run "eski-$n"; done
cp .github/server_yeni.py src/altyazi/server.py
for n in 1 2 3 4 5; do run "yeni-$n"; done
