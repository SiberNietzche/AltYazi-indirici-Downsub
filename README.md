# Altyazı İndirici

Video bağlantısından altyazı indiren program: Windows, Linux ve Android. Altyazılar açık kaynak
[yt-dlp](https://github.com/yt-dlp/yt-dlp) ile doğrudan kaynak siteden alınır; arada
başka bir sunucu kullanılmaz.

*An app for Windows, Linux and Android that downloads subtitles from a video link with yt-dlp. The interface
is available in Turkish, Kurdish (Kurmancî) and English and includes a built-in user guide.*

## Kurulum

| Sistem | Dosya | Not |
| --- | --- | --- |
| Windows 10/11 (64 bit) | `AltyaziIndirici_<sürüm>_x64-setup.exe` | WebView2 Runtime gerekir; Windows 11'de hazır gelir, yoksa kurulum sırasında indirilir |
| Linux (64 bit) | `.deb` (Debian, Ubuntu, Mint) veya `.AppImage` (diğer dağıtımlar) | `.deb`: `sudo apt install ./dosya.deb`. AppImage: dosyayı çalıştırılabilir yapıp açın |
| Android 7 ve üstü | `.apk` | Telefonda "bilinmeyen kaynaklardan yükleme"ye izin vermek gerekir; Android 10 ve öncesinde depolama izni istenir |

Dosyalar imzalı değildir. Windows SmartScreen uyarı gösterirse "Ek bilgi" ve ardından "Yine de
çalıştır" seçilir. Dosyayı güvendiğiniz bir yerden aldığınızdan emin olun ya da programı
aşağıdaki adımlarla kaynaktan kendiniz derleyin.

YouTube için bilgisayarda [Deno](https://deno.com) veya Node.js kurulu olması önerilir; yt-dlp
bazı videolarda bunlardan birine gerek duyar. Android'de bu olanak yoktur, bu yüzden orada bazı
YouTube videolarının altyazısı alınamayabilir.

## Kullanım

Bağlantıyı yapıştırıp **Getir**'e basın ve istediğiniz dilin satırındaki **İndir** düğmesine
tıklayın. Dosyalar varsayılan olarak İndirilenler klasörünün içindeki `AltyaziIndirici` klasörüne
kaydedilir; masaüstünde klasör **Ayarlar**'dan değiştirilebilir. Android'de başka bir uygulamadan
(örneğin YouTube) **Paylaş** ile bağlantı doğrudan programa gönderilebilir. Ayrıntılı anlatım
program içindeki **Kılavuz** sayfasındadır.

## Özellikler

- SRT, VTT, TXT, zaman damgalı TXT ve özgün (RAW) biçimde indirme
- Gerçek altyazılar, otomatik altyazılar ve kaynak sitenin sunduğu otomatik çeviriler
- İki dili tek dosyada birleştiren çift dilli altyazı
- Oynatma listesi ve kanal indirme (en fazla 500 video)
- Türkçe, Kürtçe (Kurmancî) ve İngilizce arayüz; program içinde adım adım kullanım kılavuzu
- Beş açık ve dört koyu renk teması
- Aranabilir dil listesi; dil adları Türkçe ve İngilizce arayüzde o dilde görünür,
  Kürtçe arayüzde kaynağın verdiği İngilizce adlarla gösterilir
- İndirilenler ekranı: listeden kaldırma (geri alınabilir), çöp kutusuna taşıyarak silme
  (Android'de çöp kutusu olmadığı için dosya kalıcı olarak silinir).
  Yalnızca altyazı dosyaları listelenir; `.txt` dosyaları ancak program yazdıysa görünür,
  video gibi diğer dosyalar hiç listelenmez ve silinmez
- İndirme başarısız olursa dil listesini tazeleyip kendiliğinden bir kez daha deneme,
  yine olmazsa satırda "Yenile ve yeniden dene" düğmesi
- Tüm hata mesajları seçili arayüz dilinde
- Var olan dosyaların üzerine yazmama

## Gizlilik

- Program kullanım verisi toplamaz, hesap istemez ve hiçbir yere bilgi göndermez.
- İnternete yalnızca yapıştırdığınız bağlantının kaynak sitesine bağlanır: video bilgisi,
  küçük resim ve altyazı oradan alınır. Kaynak site bu istekleri kendi kurallarına göre görür.
- Arayüz ile motor aynı bilgisayarda, yalnızca `127.0.0.1` üzerinden ve her açılışta yeniden
  üretilen bir anahtarla konuşur; ağdaki başka cihazlar erişemez.
- Ayarlar ve indirilenler listesi yalnızca kendi cihazınızda tutulur: Windows'ta
  `%APPDATA%\AltyaziIndirici`, Linux'ta `~/.config/AltyaziIndirici`, Android'de uygulamanın kendi
  alanı. Masaüstünde programı kaldırdıktan sonra bu klasörü silebilirsiniz.
- Android uygulaması internet izni ister; Android 11 ve üstünde dosyaları izin istemeden İndirilenler
  klasörüne yazar ve başka dosyalarınıza erişemez.

## Sınırlar

- DRM ile korunan, ücretli veya oturum gerektiren içerikler indirilemez.
- Kaynak siteler istekleri sınırlayabilir. YouTube otomatik çevirilerde zaman zaman
  HTTP 429 döndürür; birkaç dakika sonra yeniden denemek veya başka dil seçmek gerekir.
- Siteler değiştikçe yt-dlp'nin güncellenmesi gerekir: `requirements.txt` içindeki
  sürümü yükseltip programı yeniden derleyin.
- İndirdiğiniz altyazıların kullanımından ve kaynak sitenin kurallarına uymaktan
  kullanıcı sorumludur.

## Kaynaktan derleme

Her paket kendi sisteminde derlenir. Depodaki GitHub Actions iş akışı
(`.github/workflows/build.yml`) üçünü birden derler: Actions sekmesinden elle başlatılır ya da
`v` ile başlayan bir etiket gönderilince çalışır.

### Windows

Python 3.11, Rust (MSVC araç zinciri) ve Node.js gerekir.

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

Betik testleri çalıştırır, Python motorunu `altyazi-server` adlı yan süreç olarak paketler ve
`src-tauri\target\release\altyazi-indirici.exe` ile `bundle\nsis` altındaki kurulum dosyasını
üretir. Kurulum dosyası istenmiyorsa `-NoBundle` eklenir.

### Linux

Python 3.11+, Rust, Node.js ve Tauri'nin sistem kitaplıkları gerekir (liste `build.sh` başındadır).

```bash
./build.sh
```

Çıktı `src-tauri/target/release/bundle` altında `.deb` ve `.AppImage` olarak oluşur.

### Android

JDK 17+, Android SDK (platform 35) ve Python 3.11 gerekir. Python uygulamaya
[Chaquopy](https://chaquo.com/chaquopy/) ile gömülür.

```bash
cd android
./gradlew assembleDebug        # Windows'ta: gradlew.bat assembleDebug
```

Çıktı `android/app/build/outputs/apk/debug/app-debug.apk` olur. Yayın sürümünü kendi anahtarınızla
imzalamak için `android/keystore.properties` dosyasına `storeFile`, `storePassword`, `keyAlias` ve
`keyPassword` yazıp `assembleRelease` çalıştırın; bu dosya ve anahtar depoya girmez.

### Derlemeden deneme

Windows ve Linux betikleri, derleyicinin programa gömdüğü kaynak yollarındaki kullanıcı klasörünü
`~` ile değiştirir; böylece derleyenin kullanıcı adı dağıtılan dosyalara girmez.

Arayüzü derlemeden denemek için motor tek başına çalıştırılabilir; arayüz varsayılan
tarayıcıda açılır (klasör seçme düğmesi yalnızca masaüstü penceresinde bulunur):

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python run_app.py
```

Testler: `.venv\Scripts\python -m unittest discover -s tests`

## Yapı

Program iki parçadır: bir kabuk pencereyi açar, Python motoru altyazı işini yapar. Masaüstünde
kabuk Tauri'dir: açılışta motoru yan süreç olarak başlatır, arayüzü ondan yükler ve kapanırken
motoru da kapatır. Android'de kabuk küçük bir uygulamadır; motor uygulamanın içinde çalışır ve
aynı arayüz bir web görünümünde gösterilir.

| Yol | Görev |
| --- | --- |
| `src/altyazi/subtitles.py` | Altyazı ayrıştırma ve dönüştürme |
| `src/altyazi/engine.py` | yt-dlp bağlantısı, indirme ve liste işleri |
| `src/altyazi/library.py` | İndirilenler listesi, gizleme ve çöp kutusuna taşıma |
| `src/altyazi/system.py` | İşletim sistemine bağlı işler: klasör yerleri, çöp kutusu, dosya yöneticisi |
| `src/altyazi/server.py` | Yalnızca 127.0.0.1'e açık, anahtarlı yerel API |
| `src/altyazi/main.py` | Motorun masaüstü girişi: yerel sunucuyu başlatır |
| `src/altyazi/android.py` | Motorun Android girişi |
| `src-tauri/` | Tauri kabuğu (Windows, Linux): pencereyi ve klasör seçiciyi sağlar |
| `android/` | Android uygulaması: web görünümü, pano ve "Paylaş" ile gelen bağlantılar |
| `src/altyazi/web/` | Arayüz (Vue 2, Vuetify 2, Vuex, vue-router, vue-i18n, axios) |
| `src/altyazi/web/themes.js` | Renk temaları; yeni tema `server.py` içindeki `THEMES` kümesine de eklenir |
| `src/altyazi/web/i18n.js` | Arayüz ve kılavuz metinleri (tr, ku, en) |
| `tools/make_icon.py` | Program simgesini ve arayüzdeki amblem maskesini (`laurel.svg`) üretir |
| `tests/` | Ağ gerektirmeyen birim testleri |

Vue 2 ve vue-i18n 8 artık bakım almıyor. Arayüz yalnızca yerel dosyaları yükler ve katı
bir içerik güvenliği politikasıyla çalışır, ama uzun vadede güncel sürümlere geçilmesi
önerilir.

## Katkı

Hata bildirimleri ve düzeltmeler memnuniyetle karşılanır. Yeni bir arayüz metni eklerken üç
dilin de (`tr`, `ku`, `en`) karşılığını ekleyin; Kürtçe metinlerdeki düzeltmeler özellikle
değerlidir.

## Üçüncü taraf bileşenler

Program şu açık kaynak bileşenleri kullanır; her biri kendi lisansına tabidir:

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) (Unlicense) ve yt-dlp-ejs (Unlicense, MIT, ISC)
- [Tauri](https://tauri.app) (MIT veya Apache-2.0)
- [Chaquopy](https://chaquo.com/chaquopy/) (MIT) ve CPython (PSF lisansı); Android uygulamasında
- Vue, Vuex, vue-router, vue-i18n, Vuetify, axios (MIT); `src/altyazi/web/vendor` altında
- Material Icons yazı tipi (Apache-2.0); `src/altyazi/web/vendor/fonts` altında

## Lisans

[MIT](LICENSE). CYBERGAH ekibinin katkılarıyla.
