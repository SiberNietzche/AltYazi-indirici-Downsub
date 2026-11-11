window.APP_MESSAGES = {
  tr: {
    nav: { download: 'Altyazı indir', files: 'İndirilenler', sites: 'Kaynaklar', guide: "Kılavuz", settings: 'Ayarlar', skip: 'Ana içeriğe geç', main: 'Ana menü' },
    home: {
      title: 'Altyazı indir', sub: 'Bir video veya oynatma listesi bağlantısı yapıştırın.',
      label: 'Video bağlantısı', placeholder: 'https://', paste: 'Panodan yapıştır', fetch: 'Getir', loading: 'Video bilgileri alınıyor…',
      pasteFailed: 'Pano okunamadı. Ctrl+V ile yapıştırın.', retry: 'Yeniden dene', refreshRetry: 'Yenile ve yeniden dene', refreshList: 'Dil listesini yenile', refreshed: 'Dil listesi yenilendi',
      step1: 'Bağlantıyı yapıştırın', step1d: 'Video, oynatma listesi veya kanal bağlantısı olabilir.',
      step2: 'Dil ve biçim seçin', step2d: 'Gerçek altyazılar, otomatik altyazılar ve çeviriler ayrı listelenir.',
      step3: 'İndirin', step3d: 'Dosya, Ayarlar\'da belirlediğiniz klasöre kaydedilir.',
      noTracks: 'Bu video için altyazı bulunamadı.', search: 'Dil ara', format: 'Biçim', download: 'İndir',
      noMatch: 'Bu sekmede eşleşen dil yok. Sekmelerdeki sayılara bakın.', duration: 'Süre', tracks: '{count} altyazı dili',
    },
    tracks: { manual: 'Altyazılar', auto: 'Otomatik', translated: 'Çeviriler', dual: 'Çift dil', original: 'özgün' },
    fmt: { srt: 'SRT', vtt: 'VTT', txt: 'TXT', timed: 'TXT + zaman', raw: 'Özgün' },
    dual: {
      hint: 'İki dili zamanlarına göre tek dosyada birleştirir. Her satırda önce üst dil, altında alt dil görünür.',
      first: 'Üst satır dili', second: 'Alt satır dili', download: 'Çift dilli indir', same: 'İki farklı dil seçin.',
    },
    playlist: {
      videos: '{count} video', lang: 'Dil kodu', langHint: 'Örneğin tr veya en', format: 'Biçim',
      auto: 'Altyazı yoksa otomatik olanı kullan', start: 'Seçilenleri indir ({count})', cancel: 'İptal et',
      selectAll: 'Tümünü seç', selectNone: 'Seçimi kaldır', selected: '{count} / {total} seçili', current: 'İşleniyor: {name}',
      finished: 'Liste tamamlandı', partial: 'Liste tamamlandı, bazı videolar alınamadı', nothing: 'Hiçbir altyazı alınamadı',
      cancelled: 'İptal edildi', running: 'İndiriliyor',
      processed: 'İşlenen', saved: 'Kaydedilen', failed: 'Alınamayan', open: 'Klasörü aç', failures: 'Alınamayan videolar',
    },
    files: {
      title: 'İndirilenler', sub: 'İndirme klasöründeki altyazı dosyaları. Video gibi diğer dosyalar burada görünmez ve silinmez.',
      empty: 'Listede dosya yok.', go: 'Altyazı indir', show: 'Klasörde göster', open: 'Klasörü aç',
      clearList: 'Listeyi temizle', restore: 'Gizlenenleri geri getir ({count})', deleteAll: 'Tüm dosyaları sil',
      remove: 'Listeden kaldır', delete: 'Dosyayı sil', removed: '{count} dosya listeden kaldırıldı',
      deleted: '{count} dosya Geri Dönüşüm Kutusu\'na taşındı', someFailed: 'Silinemeyen dosyalar: {names}',
      confirmTitle: 'Dosyalar silinsin mi?', confirmOne: '{name} Geri Dönüşüm Kutusu\'na taşınacak.',
      confirmAll: '{count} altyazı dosyası Geri Dönüşüm Kutusu\'na taşınacak.', cancel: 'Vazgeç', confirm: 'Sil',
    },
    sites: {
      title: 'Kaynaklar',
      sub: 'Altyazılar yt-dlp motoruyla doğrudan kaynak siteden alınır. Motor binin üzerinde siteyi tanır; aşağıdakiler yalnızca örnektir.',
      limit: 'Sınırlar', limitBody: 'DRM ile korunan, ücretli veya oturum isteyen içerikler ya da kaynak sitenin sınırladığı istekler indirilemez.',
    },
    settings: {
      title: 'Ayarlar', sub: 'Tercihleriniz bu bilgisayarda saklanır.', folder: 'İndirme klasörü', folderHint: 'Altyazı dosyalarının kaydedileceği yer.',
      choose: 'Klasör seç', save: 'Kaydet', open: 'Klasörü aç', theme: 'Renk teması', themeHint: 'Beş açık ve dört koyu tema arasından seçin.',
      language: 'Arayüz dili', languageHint: 'Menü ve mesajların dili.', saved: 'Ayarlar kaydedildi',
      about: 'Hakkında', version: 'Sürüm {version}. Altyazı motoru: yt-dlp.',
    },
    errors: {
      invalid_url: 'Geçerli bir video bağlantısı girin.',
      drm: 'Bu içerik DRM ile korunuyor, altyazısı alınamaz.',
      rate_limited: 'Kaynak site bu isteği geçici olarak sınırladı (HTTP 429). Birkaç dakika sonra yeniden deneyin veya başka bir dil seçin.',
      unsupported_url: 'Bu bağlantı desteklenmiyor.',
      not_found: 'Bu bağlantıda sayfa bulunamadı (HTTP 404). Bağlantıyı kontrol edin.',
      login_required: 'Kaynak site bu içerik için oturum açmayı istiyor.',
      source_error: 'Kaynak site hata bildirdi: {detail}',
      no_info: 'Bağlantıdan bilgi alınamadı.',
      session_missing: 'Oturum bulunamadı. Bağlantıyı yeniden getirin.',
      track_missing: 'Altyazı dili bulunamadı.',
      dual_raw: 'Çift dilli altyazı Özgün biçimde indirilemez.',
      unknown_format: 'Bilinmeyen dosya biçimi.',
      parse_failed: 'Altyazı dosyası çözülemedi.',
      no_language: '{lang} dilinde altyazı yok.',
      job_missing: 'İş bulunamadı.',
      relative_folder: 'Klasör tam yol olmalı.',
      unknown_theme: 'Bilinmeyen tema.',
      unknown_locale: 'Bilinmeyen dil.',
      select_video: 'En az bir video seçin.',
      need_lang: 'Bir dil kodu girin.',
      invalid_request: 'Geçersiz istek.',
      file_error: 'Dosya işlemi başarısız: {detail}',
      unexpected: 'Beklenmeyen hata: {detail}',
      not_listed: 'Bu dosya listede değil, işlem yapılmadı.',
      network: 'Programın iç sunucusuna ulaşılamadı.',
    },
    themes: { ocean: 'Okyanus', emerald: 'Zümrüt', amethyst: 'Ametist', rose: 'Gül', amber: 'Kehribar', graphite: 'Grafit', midnight: 'Gece mavisi', forest: 'Orman', wine: 'Şarap' },
    guide: {
      title: "Kılavuz", sub: "Programın nasıl kullanılacağını adım adım anlatır.",
      sections: [
        { title: "Tek videonun altyazısını indirme", items: [
          "Videonun bağlantısını tarayıcıdan kopyalayın.",
          "Altyazı indir sayfasında bağlantıyı kutuya yapıştırın ya da Panodan yapıştır düğmesine basın.",
          "Getir düğmesine basın; program videonun adını ve altyazı dillerini listeler.",
          "Üstten bir biçim seçin, ardından istediğiniz dilin satırındaki İndir düğmesine basın.",
          "Dosya indirme klasörüne kaydedilir. Aynı adda bir dosya varsa üzerine yazılmaz, yeni dosyaya ayrı bir ad verilir.",
        ] },
        { title: "Altyazı sekmeleri", items: [
          "Altyazılar: videoyu yükleyenin eklediği gerçek altyazılar. Varsa en doğru sonuç bunlardır.",
          "Otomatik: kaynak sitenin konuşmadan kendiliğinden ürettiği altyazılar. Hatalı sözcükler içerebilir.",
          "Çeviriler: kaynak sitenin başka dillere yaptığı otomatik çeviriler.",
          "Çift dil: iki dili tek dosyada birleştirir.",
          "Dil listesi uzunsa Dil ara kutusuna dilin adını yazın. Sekmelerdeki sayılar o sekmede kaç dil olduğunu gösterir.",
        ] },
        { title: "Dosya biçimleri", items: [
          "SRT: en yaygın altyazı biçimi. Video oynatıcıların ve televizyonların çoğu açar.",
          "VTT: internet sayfalarındaki oynatıcılar için kullanılan biçim.",
          "TXT: zaman bilgisi olmadan yalnızca konuşma metni. Okumak veya çevirmek için uygundur.",
          "TXT + zaman: her satırın başında zamanı yazan düz metin.",
          "Özgün: kaynak sitenin verdiği dosya, hiç dönüştürülmeden.",
        ] },
        { title: "Çift dilli altyazı", items: [
          "Çift dil sekmesini açın.",
          "Üst satır dilini ve alt satır dilini seçin. İki dil birbirinden farklı olmalıdır.",
          "Çift dilli indir düğmesine basın. Her satırda önce üst dil, altında alt dil görünür.",
          "Çift dilli altyazı Özgün biçimde indirilemez; başka bir biçim seçin.",
        ] },
        { title: "Oynatma listesi ve kanal", items: [
          "Bir oynatma listesinin veya kanalın bağlantısını yapıştırıp Getir düğmesine basın. En fazla 500 video listelenir.",
          "İndirmek istediğiniz videoları işaretleyin ya da Tümünü seç düğmesini kullanın.",
          "Dil kodunu yazın (örneğin tr, ku veya en) ve biçimi seçin.",
          "Gerçek altyazısı olmayan videolar için otomatik altyazı kullanılsın istiyorsanız ilgili kutuyu işaretleyin.",
          "Seçilenleri indir düğmesine basın. İşlem sürerken İptal et ile durdurabilirsiniz.",
          "İşlem bitince kaç dosyanın kaydedildiği ve hangi videoların alınamadığı gösterilir.",
        ] },
        { title: "İndirilenler sayfası", items: [
          "İndirme klasöründeki altyazı dosyalarını listeler. Video gibi başka dosyalar burada görünmez ve silinmez.",
          "Klasörde göster: dosyayı Windows klasöründe açar.",
          "Listeden kaldır: dosyayı yalnızca listeden gizler, bilgisayardan silmez. Gizlenenleri geri getir ile geri alınır.",
          "Dosyayı sil: dosyayı Geri Dönüşüm Kutusu'na taşır. Yanlışlıkla sildiyseniz oradan geri alabilirsiniz.",
        ] },
        { title: "Ayarlar", items: [
          "İndirme klasörü: altyazıların kaydedileceği yeri Klasör seç ile belirleyin ya da yolu yazıp Kaydet düğmesine basın.",
          "Renk teması: beş açık ve dört koyu temadan birini seçin.",
          "Arayüz dili: Türkçe, Kurdî veya English.",
        ] },
        { title: "Sorun çıkarsa", items: [
          "HTTP 429 hatası: kaynak site istekleri geçici olarak sınırlamıştır. Birkaç dakika bekleyip yeniden deneyin ya da başka bir dil seçin.",
          "İndirme başarısız olursa program dil listesini yenileyip kendiliğinden bir kez daha dener. Yine olmazsa satırdaki Yenile ve yeniden dene düğmesine basın.",
          "DRM ile korunan, ücretli veya oturum açmayı gerektiren içeriklerin altyazısı indirilemez.",
          "Altyazı bulunamadı uyarısı çıkarsa videonun o dilde altyazısı yoktur; Otomatik ve Çeviriler sekmelerine bakın.",
          "Önceden çalışan bir site artık çalışmıyorsa programın yeni sürümü gerekir.",
        ] },
      ],
    },
    saved: '{name} kaydedildi', show: 'Göster', close: 'Kapat',
  },
  ku: {
    nav: { download: 'Binnivîs daxe', files: 'Daxistin', sites: 'Çavkanî', guide: "Rêber", settings: 'Mîheng', skip: 'Derbasî naveroka sereke bibe', main: 'Menûya sereke' },
    home: {
      title: 'Binnivîs daxe', sub: 'Girêdana vîdyoyekê an lîsteya lêdanê pêve bike.',
      label: 'Girêdana vîdyoyê', placeholder: 'https://', paste: 'Ji panoyê pêve bike', fetch: 'Bîne', loading: 'Agahiyên vîdyoyê têne girtin…',
      pasteFailed: 'Pano nehat xwendin. Ctrl+V bi kar bîne.', retry: 'Dîsa biceribîne', refreshRetry: 'Nû bike û dîsa biceribîne', refreshList: 'Lîsteya zimanan nû bike', refreshed: 'Lîsteya zimanan hat nûkirin',
      step1: 'Girêdanê pêve bike', step1d: 'Dikare girêdana vîdyo, lîsteya lêdanê an kanalê be.',
      step2: 'Ziman û formatê hilbijêre', step2d: 'Binnivîs, binnivîsên xweber û werger cuda têne nîşandan.',
      step3: 'Daxe', step3d: 'Pel di peldanka ku te di Mîhengan de hilbijartiye de tê tomarkirin.',
      noTracks: 'Ji bo vê vîdyoyê binnivîs nehat dîtin.', search: 'Li zimên bigere', format: 'Format', download: 'Daxe',
      noMatch: 'Di vê beşê de zimanekî lihevhatî tune. Li hejmarên li ser beşan binêre.', duration: 'Dem', tracks: '{count} zimanên binnivîsê',
    },
    tracks: { manual: 'Binnivîs', auto: 'Xweber', translated: 'Werger', dual: 'Du ziman', original: 'resen' },
    fmt: { srt: 'SRT', vtt: 'VTT', txt: 'TXT', timed: 'TXT + dem', raw: 'Resen' },
    dual: {
      hint: 'Du zimanan li gorî demê di yek pelî de dike yek. Di her rêzê de pêşî zimanê jorîn, li binê wî zimanê jêrîn xuya dibe.',
      first: 'Zimanê rêza jorîn', second: 'Zimanê rêza jêrîn', download: 'Bi du zimanan daxe', same: 'Du zimanên cuda hilbijêre.',
    },
    playlist: {
      videos: '{count} vîdyo', lang: 'Koda zimên', langHint: 'Wek ku, tr an en', format: 'Format',
      auto: 'Ger binnivîs tune be, ya xweber bi kar bîne', start: 'Yên hilbijartî daxe ({count})', cancel: 'Betal bike',
      selectAll: 'Hemûyan hilbijêre', selectNone: 'Hilbijartinê rake', selected: '{count} / {total} hilbijartî', current: 'Tê xebitandin: {name}',
      finished: 'Lîste qediya', partial: 'Lîste qediya, hin vîdyo nehatin girtin', nothing: 'Tu binnivîs nehat girtin',
      cancelled: 'Hat betalkirin', running: 'Tê daxistin',
      processed: 'Xebitî', saved: 'Tomarkirî', failed: 'Negirtî', open: 'Peldankê veke', failures: 'Vîdyoyên ku nehatin girtin',
    },
    files: {
      title: 'Daxistin', sub: 'Pelên binnivîsê yên di peldanka daxistinê de. Pelên din ên wek vîdyo li vir xuya nabin û nayên jêbirin.',
      empty: 'Di lîsteyê de pel tune.', go: 'Binnivîs daxe', show: 'Di peldankê de nîşan bide', open: 'Peldankê veke',
      clearList: 'Lîsteyê paqij bike', restore: 'Yên veşartî vegerîne ({count})', deleteAll: 'Hemû pelan jê bibe',
      remove: 'Ji lîsteyê rake', delete: 'Pelî jê bibe', removed: '{count} pel ji lîsteyê hatin rakirin',
      deleted: '{count} pel çûn Sepeta Çopê', someFailed: 'Pelên ku nehatin jêbirin: {names}',
      confirmTitle: 'Pel bên jêbirin?', confirmOne: '{name} dê biçe Sepeta Çopê.',
      confirmAll: '{count} pelên binnivîsê dê biçin Sepeta Çopê.', cancel: 'Dev jê berde', confirm: 'Jê bibe',
    },
    sites: {
      title: 'Çavkanî',
      sub: 'Binnivîs bi motora yt-dlp rasterast ji malpera çavkanî têne girtin. Motor zêdetirî hezar malperan nas dike; yên li jêr tenê mînak in.',
      limit: 'Sînor', limitBody: 'Naverokên bi DRM parastî, bi pere an yên ku têketinê dixwazin, û daxwazên ku malpera çavkanî sînor dike nayên daxistin.',
    },
    settings: {
      title: 'Mîheng', sub: 'Bijareyên te li ser vê komputerê têne tomarkirin.', folder: 'Peldanka daxistinê', folderHint: 'Cihê ku pelên binnivîsê lê têne tomarkirin.',
      choose: 'Peldankê hilbijêre', save: 'Tomar bike', open: 'Peldankê veke', theme: 'Rengê xuyangê', themeHint: 'Ji pênc rengên vekirî û çar rengên tarî hilbijêre.',
      language: 'Zimanê navrûyê', languageHint: 'Zimanê menû û peyaman.', saved: 'Mîheng hatin tomarkirin',
      about: 'Derbarê bernameyê', version: 'Guherto {version}. Motora binnivîsê: yt-dlp.',
    },
    errors: {
      invalid_url: 'Girêdaneke vîdyoyê ya derbasdar binivîse.',
      drm: 'Ev naverok bi DRM hatiye parastin, binnivîsa wê nayê girtin.',
      rate_limited: 'Malpera çavkanî ev daxwaz bi awayekî demkî sînor kir (HTTP 429). Piştî çend deqeyan dîsa biceribîne an zimanekî din hilbijêre.',
      unsupported_url: 'Ev girêdan nayê piştgirîkirin.',
      not_found: 'Di vê girêdanê de rûpel nehat dîtin (HTTP 404). Girêdanê kontrol bike.',
      login_required: 'Malpera çavkanî ji bo vê naverokê têketinê dixwaze.',
      source_error: 'Malpera çavkanî çewtiyek ragihand: {detail}',
      no_info: 'Ji girêdanê agahî nehat girtin.',
      session_missing: 'Danişîn nehat dîtin. Girêdanê dîsa bîne.',
      track_missing: 'Zimanê binnivîsê nehat dîtin.',
      dual_raw: 'Binnivîsa du zimanî bi formata Resen nayê daxistin.',
      unknown_format: 'Formata pelê nayê zanîn.',
      parse_failed: 'Pelê binnivîsê nehat xwendin.',
      no_language: 'Bi zimanê {lang} binnivîs tune.',
      job_missing: 'Kar nehat dîtin.',
      relative_folder: 'Divê rêya peldankê temam be.',
      unknown_theme: 'Reng nayê zanîn.',
      unknown_locale: 'Ziman nayê zanîn.',
      select_video: 'Herî kêm vîdyoyekê hilbijêre.',
      need_lang: 'Koda zimên binivîse.',
      invalid_request: 'Daxwaza nederbasdar.',
      file_error: 'Karê pelê bi ser neket: {detail}',
      unexpected: 'Çewtiya nediyar: {detail}',
      not_listed: 'Ev pel ne di lîsteyê de ye, tiştek nehat kirin.',
      network: 'Bi servera hundirîn a bernameyê re têkilî çênebû.',
    },
    themes: { ocean: 'Okyanûs', emerald: 'Zimrût', amethyst: 'Ametîst', rose: 'Gul', amber: 'Kehrîba', graphite: 'Grafît', midnight: 'Şîniya şevê', forest: 'Daristan', wine: 'Şerab' },
    guide: {
      title: "Rêber", sub: "Gav bi gav rave dike ka bername çawa tê bikaranîn.",
      sections: [
        { title: "Daxistina binnivîsa vîdyoyekê", items: [
          "Girêdana vîdyoyê ji gerokê kopî bike.",
          "Di rûpela Binnivîs daxe de girêdanê di qutiyê de pêve bike an li bişkoka Ji panoyê pêve bike bixe.",
          "Li bişkoka Bîne bixe; bername navê vîdyoyê û zimanên binnivîsê nîşan dide.",
          "Li jor formatekê hilbijêre, paşê di rêza zimanê ku tu dixwazî de li bişkoka Daxe bixe.",
          "Pel di peldanka daxistinê de tê tomarkirin. Heke pelek bi heman navî hebe, li ser nayê nivîsandin; navekî cuda li pelê nû tê kirin.",
        ] },
        { title: "Beşên binnivîsê", items: [
          "Binnivîs: binnivîsên rastîn ên ku xwediyê vîdyoyê lê zêde kirine. Heke hebin, encama herî rast ev in.",
          "Xweber: binnivîsên ku malpera çavkanî bi xwe ji axaftinê çêdike. Dibe ku peyvên çewt tê de hebin.",
          "Werger: wergerên xweber ên ku malpera çavkanî ji bo zimanên din çêdike.",
          "Du ziman: du zimanan di yek pelî de dike yek.",
          "Heke lîsteya zimanan dirêj be, navê zimên di qutiya Li zimên bigere de binivîse. Hejmarên li ser beşan nîşan didin ka di wê beşê de çend ziman hene.",
        ] },
        { title: "Formatên pelan", items: [
          "SRT: formata binnivîsê ya herî belav. Piraniya lêderên vîdyoyê û televîzyonan wê vedikin.",
          "VTT: formata ku ji bo lêderên li ser rûpelên înternetê tê bikaranîn.",
          "TXT: bêyî agahiya demê, tenê nivîsa axaftinê. Ji bo xwendin an wergerandinê guncaw e.",
          "TXT + dem: nivîsa sade ya ku di serê her rêzê de dem tê nivîsandin.",
          "Resen: pelê ku malpera çavkanî dide, bêyî tu guherandinê.",
        ] },
        { title: "Binnivîsa bi du zimanan", items: [
          "Beşa Du ziman veke.",
          "Zimanê rêza jorîn û zimanê rêza jêrîn hilbijêre. Divê her du ziman ji hev cuda bin.",
          "Li bişkoka Bi du zimanan daxe bixe. Di her rêzê de pêşî zimanê jorîn, li binê wî zimanê jêrîn xuya dibe.",
          "Binnivîsa bi du zimanan bi formata Resen nayê daxistin; formateke din hilbijêre.",
        ] },
        { title: "Lîsteya lêdanê û kanal", items: [
          "Girêdana lîsteyeke lêdanê an kanalekê pêve bike û li bişkoka Bîne bixe. Herî zêde 500 vîdyo têne nîşandan.",
          "Vîdyoyên ku tu dixwazî daxî nîşan bike an bişkoka Hemûyan hilbijêre bi kar bîne.",
          "Koda zimên binivîse (wek ku, tr an en) û formatê hilbijêre.",
          "Heke tu dixwazî ji bo vîdyoyên ku binnivîsa wan a rastîn tune binnivîsa xweber bê bikaranîn, qutiya têkildar nîşan bike.",
          "Li bişkoka Yên hilbijartî daxe bixe. Dema kar didome, tu dikarî bi Betal bike wî rawestînî.",
          "Dema kar diqede, tê nîşandan ka çend pel hatine tomarkirin û kîjan vîdyo nehatine girtin.",
        ] },
        { title: "Rûpela Daxistin", items: [
          "Pelên binnivîsê yên di peldanka daxistinê de nîşan dide. Pelên din ên wek vîdyo li vir xuya nabin û nayên jêbirin.",
          "Di peldankê de nîşan bide: pelî di peldanka Windowsê de vedike.",
          "Ji lîsteyê rake: pelî tenê ji lîsteyê vedişêre, ji komputerê jê nabe. Bi Yên veşartî vegerîne tê vegerandin.",
          "Pelî jê bibe: pelî dişîne Sepeta Çopê. Heke te bi xeletî jê biribe, tu dikarî ji wir vegerînî.",
        ] },
        { title: "Mîheng", items: [
          "Peldanka daxistinê: cihê ku binnivîs lê têne tomarkirin bi Peldankê hilbijêre diyar bike an rêyê binivîse û li bişkoka Tomar bike bixe.",
          "Rengê xuyangê: ji pênc rengên vekirî û çar rengên tarî yekî hilbijêre.",
          "Zimanê navrûyê: Türkçe, Kurdî an English.",
        ] },
        { title: "Heke pirsgirêk derkeve", items: [
          "Çewtiya HTTP 429: malpera çavkanî daxwazan bi awayekî demkî sînor kiriye. Çend deqeyan bisekine û dîsa biceribîne an zimanekî din hilbijêre.",
          "Heke daxistin bi ser nekeve, bername lîsteya zimanan nû dike û bi xwe carekê din diceribîne. Heke dîsa nebe, di rêzê de li bişkoka Nû bike û dîsa biceribîne bixe.",
          "Binnivîsên naverokên bi DRM parastî, bi pere an yên ku têketinê dixwazin nayên daxistin.",
          "Heke hişyariya ku binnivîs nehat dîtin derkeve, binnivîsa vîdyoyê bi wî zimanî tune; li beşên Xweber û Werger binêre.",
          "Heke malpereke ku berê dixebitî êdî nexebite, guhertoya nû ya bernameyê pêwîst e.",
        ] },
      ],
    },
    saved: '{name} hat tomarkirin', show: 'Nîşan bide', close: 'Bigire',
  },
  en: {
    nav: { download: 'Get subtitles', files: 'Downloads', sites: 'Sources', guide: "Guide", settings: 'Settings', skip: 'Skip to main content', main: 'Main menu' },
    home: {
      title: 'Get subtitles', sub: 'Paste a link to a video or playlist.',
      label: 'Video link', placeholder: 'https://', paste: 'Paste from clipboard', fetch: 'Fetch', loading: 'Getting video details…',
      pasteFailed: 'Could not read the clipboard. Use Ctrl+V.', retry: 'Try again', refreshRetry: 'Refresh and try again', refreshList: 'Refresh language list', refreshed: 'Language list refreshed',
      step1: 'Paste the link', step1d: 'It can be a video, playlist or channel link.',
      step2: 'Pick language and format', step2d: 'Subtitles, automatic captions and translations are listed separately.',
      step3: 'Download', step3d: 'The file is saved to the folder chosen in Settings.',
      noTracks: 'No subtitles were found for this video.', search: 'Search languages', format: 'Format', download: 'Download',
      noMatch: 'No language in this tab matches. Check the counts on the tabs.', duration: 'Duration', tracks: '{count} subtitle languages',
    },
    tracks: { manual: 'Subtitles', auto: 'Automatic', translated: 'Translations', dual: 'Dual', original: 'original' },
    fmt: { srt: 'SRT', vtt: 'VTT', txt: 'TXT', timed: 'TXT + time', raw: 'Original' },
    dual: {
      hint: 'Combines two languages into one file by timing. Each line shows the top language with the bottom one beneath it.',
      first: 'Top line language', second: 'Bottom line language', download: 'Download dual', same: 'Choose two different languages.',
    },
    playlist: {
      videos: '{count} videos', lang: 'Language code', langHint: 'For example en or tr', format: 'Format',
      auto: 'Use automatic captions when needed', start: 'Download selected ({count})', cancel: 'Cancel',
      selectAll: 'Select all', selectNone: 'Clear selection', selected: '{count} of {total} selected', current: 'Processing: {name}',
      finished: 'Playlist finished', partial: 'Playlist finished, some videos failed', nothing: 'No subtitles could be downloaded',
      cancelled: 'Cancelled', running: 'Downloading',
      processed: 'Processed', saved: 'Saved', failed: 'Failed', open: 'Open folder', failures: 'Videos that failed',
    },
    files: {
      title: 'Downloads', sub: 'Subtitle files in the download folder. Other files such as videos are not shown and never deleted here.',
      empty: 'No files in the list.', go: 'Get subtitles', show: 'Show in folder', open: 'Open folder',
      clearList: 'Clear list', restore: 'Show hidden files ({count})', deleteAll: 'Delete all files',
      remove: 'Remove from list', delete: 'Delete file', removed: '{count} files removed from the list',
      deleted: '{count} files moved to the Recycle Bin', someFailed: 'Could not delete: {names}',
      confirmTitle: 'Delete files?', confirmOne: '{name} will be moved to the Recycle Bin.',
      confirmAll: '{count} subtitle files will be moved to the Recycle Bin.', cancel: 'Cancel', confirm: 'Delete',
    },
    sites: {
      title: 'Sources',
      sub: 'Subtitles come directly from the source site through the yt-dlp engine. It recognises over a thousand sites; these are only examples.',
      limit: 'Limits', limitBody: 'DRM-protected, paid or sign-in-only content, and requests the source site limits, cannot be downloaded.',
    },
    settings: {
      title: 'Settings', sub: 'Your preferences are stored on this computer.', folder: 'Download folder', folderHint: 'Where subtitle files are saved.',
      choose: 'Choose folder', save: 'Save', open: 'Open folder', theme: 'Color theme', themeHint: 'Choose from five light and four dark themes.',
      language: 'Interface language', languageHint: 'Language of menus and messages.', saved: 'Settings saved',
      about: 'About', version: 'Version {version}. Subtitle engine: yt-dlp.',
    },
    errors: {
      invalid_url: 'Enter a valid video link.',
      drm: 'This content is DRM-protected, so its subtitles cannot be downloaded.',
      rate_limited: 'The source site temporarily limited this request (HTTP 429). Try again in a few minutes or choose another language.',
      unsupported_url: 'This link is not supported.',
      not_found: 'No page was found at this link (HTTP 404). Check the link.',
      login_required: 'The source site requires signing in for this content.',
      source_error: 'The source site reported an error: {detail}',
      no_info: 'Could not get details from this link.',
      session_missing: 'Session not found. Fetch the link again.',
      track_missing: 'Subtitle language not found.',
      dual_raw: 'Dual subtitles cannot be downloaded in Original format.',
      unknown_format: 'Unknown file format.',
      parse_failed: 'The subtitle file could not be read.',
      no_language: 'No subtitles in {lang}.',
      job_missing: 'Job not found.',
      relative_folder: 'The folder must be a full path.',
      unknown_theme: 'Unknown theme.',
      unknown_locale: 'Unknown language.',
      select_video: 'Select at least one video.',
      need_lang: 'Enter a language code.',
      invalid_request: 'Invalid request.',
      file_error: 'File operation failed: {detail}',
      unexpected: 'Unexpected error: {detail}',
      not_listed: 'This file is not in the list, so nothing was done.',
      network: 'Could not reach the app\'s internal server.',
    },
    themes: { ocean: 'Ocean', emerald: 'Emerald', amethyst: 'Amethyst', rose: 'Rose', amber: 'Amber', graphite: 'Graphite', midnight: 'Midnight', forest: 'Forest', wine: 'Wine' },
    guide: {
      title: "Guide", sub: "Explains step by step how to use the program.",
      sections: [
        { title: "Downloading subtitles for one video", items: [
          "Copy the video link from your browser.",
          "On the Get subtitles page, paste the link into the box or press Paste from clipboard.",
          "Press Fetch; the program lists the video name and its subtitle languages.",
          "Pick a format at the top, then press Download on the row of the language you want.",
          "The file is saved to the download folder. An existing file with the same name is not overwritten; the new file gets a different name.",
        ] },
        { title: "Subtitle tabs", items: [
          "Subtitles: real subtitles added by the uploader. When available they are the most accurate.",
          "Automatic: subtitles the source site generates from speech on its own. They may contain wrong words.",
          "Translations: automatic translations the source site makes into other languages.",
          "Dual: joins two languages in one file.",
          "If the language list is long, type the language name into the Search languages box. The numbers on the tabs show how many languages each tab has.",
        ] },
        { title: "File formats", items: [
          "SRT: the most common subtitle format. Most video players and TVs open it.",
          "VTT: the format used by players on web pages.",
          "TXT: the spoken text only, without timing. Good for reading or translating.",
          "TXT + time: plain text with the time at the start of each line.",
          "Original: the file as the source site provides it, with no conversion.",
        ] },
        { title: "Dual-language subtitles", items: [
          "Open the Dual tab.",
          "Choose the top-line language and the bottom-line language. The two must be different.",
          "Press the dual-language download button. Each cue shows the top language first and the bottom language under it.",
          "Dual-language subtitles cannot be downloaded in the Original format; pick another format.",
        ] },
        { title: "Playlists and channels", items: [
          "Paste the link of a playlist or a channel and press Fetch. Up to 500 videos are listed.",
          "Tick the videos you want or use Select all.",
          "Type the language code (for example tr, ku or en) and choose the format.",
          "Tick the box if automatic subtitles should be used for videos that have no real subtitles.",
          "Press the download button for the selection. You can stop a running job with Cancel.",
          "When the job ends you see how many files were saved and which videos could not be fetched.",
        ] },
        { title: "Downloads page", items: [
          "Lists the subtitle files in the download folder. Other files such as videos are not shown here and are never deleted.",
          "Show in folder: opens the file in its Windows folder.",
          "Remove from list: only hides the file from the list; it stays on the computer. Hidden files can be restored.",
          "Delete file: moves the file to the Recycle Bin, where you can restore it if it was a mistake.",
        ] },
        { title: "Settings", items: [
          "Download folder: choose where subtitles are saved with the folder button, or type the path and press Save.",
          "Colour theme: pick one of five light and four dark themes.",
          "Interface language: Türkçe, Kurdî or English.",
        ] },
        { title: "If something goes wrong", items: [
          "HTTP 429 error: the source site is temporarily limiting requests. Wait a few minutes and try again, or pick another language.",
          "If a download fails, the program refreshes the language list and retries once by itself. If it still fails, press the refresh-and-retry button on the row.",
          "Subtitles of DRM-protected, paid or login-only content cannot be downloaded.",
          "If no subtitles are found, the video has none in that language; check the Automatic and Translations tabs.",
          "If a site that used to work stops working, a newer version of the program is needed.",
        ] },
      ],
    },
    saved: '{name} saved', show: 'Show', close: 'Close',
  },
};

// Çöp kutusunun adı işletim sistemine göre değişir; metinler Windows adıyla yazılmıştır.
(function () {
  if (/Windows/.test(navigator.userAgent)) return;
  if (window.AndroidHost || /Android/.test(navigator.userAgent)) {
    // Android'de çöp kutusu, klasör seçimi ve dosya yöneticisi yoktur; ilgili metinler değişir.
    const android = {
      tr: {
        deleted: '{count} dosya silindi', one: '{name} kalıcı olarak silinecek.', all: '{count} altyazı dosyası kalıcı olarak silinecek.',
        del: 'Dosyayı sil: dosyayı telefondan kalıcı olarak siler.',
        folder: 'Dosyalar telefonun İndirilenler klasöründeki AltyaziIndirici klasörüne kaydedilir; dosya yöneticisiyle açabilirsiniz.',
        share: 'Başka bir uygulamada (örneğin YouTube) Paylaş düğmesine basıp Altyazı İndirici\'yi seçerseniz bağlantı kendiliğinden gelir.',
        sub: 'Tercihleriniz bu cihazda saklanır.', hint: 'Dosyalar telefonun İndirilenler klasörüne kaydedilir.',
      },
      ku: {
        deleted: '{count} pel hatin jêbirin', one: '{name} dê bi temamî bê jêbirin.', all: '{count} pelên binnivîsê dê bi temamî bên jêbirin.',
        del: 'Pelî jê bibe: pelî bi temamî ji telefonê jê dibe.',
        folder: 'Pel di peldanka AltyaziIndirici ya di nav peldanka Daxistinan a telefonê de têne tomarkirin; tu dikarî bi rêvebirê pelan vekî.',
        share: 'Heke tu di sepaneke din de (wek YouTube) li bişkoka Parve bike bixî û Altyazı İndirici hilbijêrî, girêdan bi xwe tê.',
        sub: 'Bijareyên te li ser vê cîhazê têne tomarkirin.', hint: 'Pel di peldanka Daxistinan a telefonê de têne tomarkirin.',
      },
      en: {
        deleted: '{count} files deleted', one: '{name} will be permanently deleted.', all: '{count} subtitle files will be permanently deleted.',
        del: 'Delete file: permanently deletes the file from the phone.',
        folder: 'Files are saved to the AltyaziIndirici folder inside the phone\'s Downloads folder; open it with a file manager.',
        share: 'If you press Share in another app (for example YouTube) and pick Altyazı İndirici, the link arrives by itself.',
        sub: 'Your preferences are stored on this device.', hint: 'Files are saved to the phone\'s Downloads folder.',
      },
    };
    Object.keys(android).forEach((locale) => {
      const messages = window.APP_MESSAGES[locale];
      const text = android[locale];
      Object.assign(messages.files, { deleted: text.deleted, confirmOne: text.one, confirmAll: text.all });
      messages.settings.folderHint = text.hint;
      messages.settings.sub = text.sub;
      const sections = messages.guide.sections;
      sections[0].items.push(text.share);
      // İndirilenler: "Klasörde göster" maddesi çıkar, silme maddesi değişir. Ayarlar: klasör maddesi değişir.
      sections[5].items.splice(1, 1);
      sections[5].items[sections[5].items.length - 1] = text.del;
      sections[6].items[0] = text.folder;
    });
    return;
  }
  const names = [['Geri Dönüşüm Kutusu', 'Çöp Kutusu'], ['Recycle Bin', 'Trash']];
  const rename = (node) => {
    Object.keys(node).forEach((key) => {
      if (typeof node[key] === 'string') names.forEach(([from, to]) => { node[key] = node[key].split(from).join(to); });
      else if (node[key] && typeof node[key] === 'object') rename(node[key]);
    });
  };
  rename(window.APP_MESSAGES);
})();
