"""Android uygulamasının girişi: motoru uygulamanın içinde, arka plan iş parçacığında başlatır.

Android'de ayrı bir süreç çalıştırılamadığı için sunucu uygulamayla aynı süreçte çalışır
(Python'u uygulamaya Chaquopy gömer). ``android/`` altındaki uygulama ``start`` işlevini
çağırır ve dönen adresi kendi web görünümünde açar.
"""

from __future__ import annotations

import os
import threading

_url: str | None = None
_lock = threading.Lock()


def start(data_dir: str, download_dir: str) -> str:
    """Sunucuyu (bir kez) başlatır ve arayüzün adresini döndürür."""
    global _url
    with _lock:
        if _url is None:
            # Klasörleri uygulama verir; system modülü bunları içe aktarılırken okur.
            os.environ["ALTYAZI_PLATFORM"] = "android"
            os.environ["ALTYAZI_DATA_DIR"] = data_dir
            os.environ["ALTYAZI_DOWNLOAD_DIR"] = download_dir
            from . import updater

            # İndirilmiş daha yeni bir yt-dlp, motor yüklenmeden önce devreye alınır.
            updater.activate()
            from .server import AppContext, create_server

            context = AppContext()
            # Ayarlarda başka bir klasör kalmış olsa bile Android'de yalnızca verilen klasöre yazılabilir.
            context.settings.update({"download_dir": download_dir})
            server = create_server(context, 0)
            threading.Thread(target=server.serve_forever, name="altyazi-server", daemon=True).start()
            updater.check_later(lambda: context.settings.data["auto_update"])
            from . import release

            release.check_later(lambda: context.settings.data["update_notice"])
            _url = f"http://127.0.0.1:{server.server_address[1]}/?token={context.token}"
        return _url
