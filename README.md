# Altyazı İndirici

Video bağlantısından altyazı indiren Windows masaüstü programı. Altyazılar açık kaynak
[yt-dlp](https://github.com/yt-dlp/yt-dlp) ile doğrudan kaynak siteden alınır; arada
başka bir sunucu kullanılmaz.

## Kullanım

`dist\AltyaziIndirici.exe` dosyasını çalıştırın, bağlantıyı yapıştırıp **Getir**'e basın
ve istediğiniz dilin yanındaki biçim tuşuna tıklayın. Dosyalar varsayılan olarak
`İndirilenler\AltyaziIndirici` klasörüne kaydedilir. Klasör **Ayarlar**'dan değiştirilebilir.

## Özellikler

- SRT, VTT, TXT, zaman damgalı TXT ve özgün (RAW) biçimde indirme
- Gerçek altyazılar, otomatik altyazılar ve kaynak sitenin sunduğu otomatik çeviriler
- İki dili tek dosyada birleştiren çift dilli altyazı
- Oynatma listesi ve kanal indirme (en fazla 500 video)
- Türkçe, Kürtçe (Kurmancî) ve İngilizce arayüz
- Beş açık ve dört koyu renk teması, çerçeveli ve kabartmalı düğmeler
- Aranabilir dil listesi; dil adları Türkçe ve İngilizce arayüzde o dilde görünür,
  Kürtçe arayüzde kaynağın verdiği İngilizce adlarla gösterilir
- Oturumda kaydedilen dosyaları gösteren İndirilenler ekranı
- İndirilenler ekranı: listeden kaldırma (geri alınabilir), Geri Dönüşüm Kutusu'na taşıyarak silme.
  Yalnızca altyazı dosyaları listelenir; `.txt` dosyaları ancak program yazdıysa görünür,
  video gibi diğer dosyalar hiç listelenmez ve silinmez
- İndirme başarısız olursa dil listesini tazeleyip kendiliğinden bir kez daha deneme,
  yine olmazsa satırda "Yenile ve yeniden dene" düğmesi
- Tüm hata mesajları seçili arayüz dilinde
- Var olan dosyaların üzerine yazmama

## Sınırlar

- DRM ile korunan, ücretli veya oturum gerektiren içerikler indirilemez.
- Kaynak siteler istekleri sınırlayabilir. YouTube otomatik çevirilerde zaman zaman
  HTTP 429 döndürür; birkaç dakika sonra yeniden denemek veya başka dil seçmek gerekir.
- Siteler değiştikçe yt-dlp'nin güncellenmesi gerekir: `requirements.txt` içindeki
  sürümü yükseltip programı yeniden derleyin.
- İndirdiğiniz altyazıların kullanımından ve kaynak sitenin kurallarına uymaktan
  kullanıcı sorumludur.

## Kaynaktan derleme

Python 3.11 ve WebView2 Runtime gerekir (Windows 11'de hazır gelir).

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

Betik testleri çalıştırır ve `dist\AltyaziIndirici.exe` dosyasını üretir.

## Yapı

| Yol | Görev |
| --- | --- |
| `src/altyazi/subtitles.py` | Altyazı ayrıştırma ve dönüştürme |
| `src/altyazi/engine.py` | yt-dlp bağlantısı, indirme ve liste işleri |
| `src/altyazi/library.py` | İndirilenler listesi, gizleme ve Geri Dönüşüm Kutusu'na taşıma |
| `src/altyazi/server.py` | Yalnızca 127.0.0.1'e açık, anahtarlı yerel API |
| `src/altyazi/main.py` | Masaüstü penceresi (pywebview ve WebView2) |
| `src/altyazi/web/` | Arayüz (Vue 2, Vuetify 2, Vuex, vue-router, vue-i18n, axios) |
| `src/altyazi/web/themes.js` | Renk temaları; yeni tema `server.py` içindeki `THEMES` kümesine de eklenir |
| `src/altyazi/web/i18n.js` | Arayüz metinleri (tr, ku, en) |
| `tests/` | Ağ gerektirmeyen birim testleri |

Vue 2 ve vue-i18n 8 artık bakım almıyor. Arayüz yalnızca yerel dosyaları yükler ve katı
bir içerik güvenliği politikasıyla çalışır, ama uzun vadede güncel sürümlere geçilmesi
önerilir.
