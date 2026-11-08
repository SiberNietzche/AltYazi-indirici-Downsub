"""Uygulama girişi: yerel sunucuyu başlatır ve WebView2 penceresini açar."""

from __future__ import annotations

import argparse
import os
import sys
import threading
import webbrowser

from . import APP_NAME
from .server import AppContext, create_server


def _guard_streams() -> None:
    # Pencereli exe'de stdout/stderr yoktur; yazma denemeleri hata vermemeli.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")


def main() -> int:
    _guard_streams()
    parser = argparse.ArgumentParser(prog="AltyaziIndirici")
    parser.add_argument("--serve", action="store_true", help="Pencere açmadan yalnızca yerel sunucuyu çalıştırır")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--token", help="Sınama için sabit erişim anahtarı")
    args = parser.parse_args()

    context = AppContext(args.token)
    server = create_server(context, args.port)
    url = f"http://127.0.0.1:{server.server_address[1]}/?token={context.token}"

    if args.serve:
        print(url, flush=True)
        server.serve_forever()
        return 0

    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        import webview

        window = webview.create_window(APP_NAME, url, width=1100, height=780, min_size=(760, 560))

        def choose_folder(initial: str) -> str | None:
            result = window.create_file_dialog(webview.FileDialog.FOLDER, directory=initial)
            return result[0] if result else None

        context.choose_folder = choose_folder
        webview.start()
    except Exception:  # WebView2 açılamazsa uygulama tarayıcıda çalışmaya devam eder
        webbrowser.open(url)
        threading.Event().wait()
    finally:
        server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
