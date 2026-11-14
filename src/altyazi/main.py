"""Motorun girişi: yerel sunucuyu başlatır.

Tauri kabuğu bu programı ``--serve --exit-with-stdin`` ile yan süreç olarak çalıştırır.
Seçeneksiz çalıştırıldığında (geliştirme) arayüz varsayılan tarayıcıda açılır.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import webbrowser

from . import release, updater


def _guard_streams() -> None:
    # Pencereli exe'de stdout/stderr yoktur; yazma denemeleri hata vermemeli.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")


def _exit_when_stdin_closes() -> None:
    """Sunucuyu başlatan program (Tauri kabuğu) kapanınca borusu da kapanır; o zaman çıkılır.

    Böylece kabuk çökse veya zorla kapatılsa bile sunucu arkada çalışır durumda kalmaz.
    """
    try:
        sys.stdin.buffer.read()
    except (OSError, ValueError):
        pass
    os._exit(0)


def main() -> int:
    stdin = sys.stdin  # _guard_streams öncesi: pencereli exe'de None olabilir
    _guard_streams()
    parser = argparse.ArgumentParser(prog="altyazi-server")
    parser.add_argument("--serve", action="store_true", help="Tarayıcı açmadan yalnızca yerel sunucuyu çalıştırır")
    parser.add_argument("--exit-with-stdin", action="store_true", help="Standart girdi kapanınca sunucuyu kapatır (Tauri kabuğu kullanır)")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--token", help="Sınama için sabit erişim anahtarı")
    args = parser.parse_args()

    # İndirilmiş daha yeni bir yt-dlp, motor (server -> engine) yüklenmeden önce devreye alınır.
    updater.activate()
    from .server import AppContext, create_server

    context = AppContext(args.token)
    server = create_server(context, args.port)
    url = f"http://127.0.0.1:{server.server_address[1]}/?token={context.token}"

    if args.serve and args.exit_with_stdin and stdin is not None:
        threading.Thread(target=_exit_when_stdin_closes, daemon=True).start()
    updater.check_later(lambda: context.settings.data["auto_update"])
    release.check_later(lambda: context.settings.data["update_notice"])
    print(url, flush=True)
    if not args.serve:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
