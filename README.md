# Altyazı İndirici

Video bağlantısından altyazı indiren Windows masaüstü programı. Altyazılar açık kaynak
[yt-dlp](https://github.com/yt-dlp/yt-dlp) ile doğrudan kaynak siteden alınır; arada
başka bir sunucu kullanılmaz.

*A Windows desktop app that downloads subtitles from a video link with yt-dlp. The interface
is available in Turkish, Kurdish (Kurmancî) and English and includes a built-in user guide.*

## Kurulum

`AltyaziIndirici_<sürüm>_x64-setup.exe` kurulum dosyasını çalıştırın. Windows 10 veya 11 (64 bit)
gerekir. Program WebView2 Runtime kullanır; Windows 11'de hazır gelir, yoksa kurulum sırasında
indirilir.

Kurulum dosyası imzalı değildir. Windows SmartScreen uyarı gösterirse "Ek bilgi" ve ardından
"Yine de çalıştır" seçilir. Dosyayı güvendiğiniz bir yerden aldığınızdan emin olun ya da programı
aşağıdaki adımlarla kaynaktan kendiniz derleyin.

## Kullanım

Bağlantıyı yapıştırıp **Getir**'e basın ve istediğiniz dilin satırındaki **İndir** düğmesine
tıklayın. Dosyalar varsayılan olarak `İndirilenler\AltyaziIndirici` klasörüne kaydedilir; klasör
**Ayarlar**'dan değiştirilebilir. Ayrıntılı anlatım program içindeki **Kılavuz** sayfasındadır.

## Özellikler

- SRT, VTT, TXT, zaman damgalı TXT ve özgün (RAW) biçimde indirme
- Gerçek altyazılar, otomatik altyazılar ve kaynak sitenin sunduğu otomatik çeviriler
- İki dili tek dosyada birleştiren çift dilli altyazı
- Oynatma listesi ve kanal indirme (en fazla 500 video)
- Türkçe, Kürtçe (Kurmancî) ve İngilizce arayüz; program içinde adım adım kullanım kılavuzu
- Beş açık ve dört koyu renk teması
- Aranabilir dil listesi; dil adları Türkçe ve İngilizce arayüzde o dilde görünür,
  Kürtçe arayüzde kaynağın verdiği İngilizce adlarla gösterilir
- İndirilenler ekranı: listeden kaldırma (geri alınabilir), Geri Dönüşüm Kutusu'na taşıyarak silme.
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
- Ayarlar ve indirilenler listesi yalnızca bu bilgisayarda, `%APPDATA%\AltyaziIndirici`
  klasöründe tutulur. Programı kaldırdıktan sonra bu klasörü silebilirsiniz.

## Sınırlar

- DRM ile korunan, ücretli veya oturum gerektiren içerikler indirilemez.
- Kaynak siteler istekleri sınırlayabilir. YouTube otomatik çevirilerde zaman zaman
  HTTP 429 döndürür; birkaç dakika sonra yeniden denemek veya başka dil seçmek gerekir.
- Siteler değiştikçe yt-dlp'nin güncellenmesi gerekir: `requirements.txt` içindeki
  sürümü yükseltip programı yeniden derleyin.
- İndirdiğiniz altyazıların kullanımından ve kaynak sitenin kurallarına uymaktan
  kullanıcı sorumludur.

## Kaynaktan derleme

Python 3.11, Rust (MSVC araç zinciri) ve Node.js gerekir.

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

Betik testleri çalıştırır, Python motorunu `altyazi-server` adlı yan süreç olarak paketler ve
`src-tauri\target\release\altyazi-indirici.exe` ile `bundle\nsis` altındaki kurulum dosyasını
üretir. Kurulum dosyası istenmiyorsa `-NoBundle` eklenir. Derleyicinin programa gömdüğü kaynak
yollarındaki kullanıcı klasörü `~` ile değiştirilir; böylece derleyenin Windows kullanıcı adı
dağıtılan dosyalara girmez.

Arayüzü derlemeden denemek için motor tek başına çalıştırılabilir; arayüz varsayılan
tarayıcıda açılır (klasör seçme düğmesi yalnızca masaüstü penceresinde bulunur):

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python run_app.py
```

Testler: `.venv\Scripts\python -m unittest discover -s tests`

## Yapı

Program iki parçadır: Tauri kabuğu pencereyi açar, Python motoru altyazı işini yapar. Kabuk
açılışta motoru başlatır, arayüzü ondan yükler ve kapanırken motoru da kapatır.

| Yol | Görev |
| --- | --- |
| `src/altyazi/subtitles.py` | Altyazı ayrıştırma ve dönüştürme |
| `src/altyazi/engine.py` | yt-dlp bağlantısı, indirme ve liste işleri |
| `src/altyazi/library.py` | İndirilenler listesi, gizleme ve Geri Dönüşüm Kutusu'na taşıma |
| `src/altyazi/server.py` | Yalnızca 127.0.0.1'e açık, anahtarlı yerel API |
| `src/altyazi/main.py` | Motorun girişi: yerel sunucuyu başlatır |
| `src-tauri/` | Tauri kabuğu: motoru yan süreç olarak başlatır, pencereyi ve klasör seçiciyi sağlar |
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
- Vue, Vuex, vue-router, vue-i18n, Vuetify, axios (MIT); `src/altyazi/web/vendor` altında
- Material Icons yazı tipi (Apache-2.0); `src/altyazi/web/vendor/fonts` altında

## Lisans

[MIT](LICENSE). CYBERGAH ekibinin katkılarıyla.
