/* global Vue, Vuex, VueRouter, VueI18n, Vuetify, axios */
(function () {
  'use strict';

  const token = new URLSearchParams(window.location.search).get('token') || '';
  const tauri = window.__TAURI__ || null; // Yalnızca Tauri kabuğunda tanımlıdır
  // Android uygulamasında sayfa bir WebView içinde çalışır; AndroidHost'u uygulama sağlar.
  // Orada dosya yöneticisi ve klasör seçimi yoktur: "desktop-only" öğeler gizlenir.
  // Telefonda ve Linux'ta (WebKitGTK) bulanıklık ve sürekli animasyonlar ağır kalır; style.css bunları
  // platform-android ve platform-linux sınıflarıyla kapatır.
  const android = window.AndroidHost || null;
  const mobile = !!android || /Android/.test(navigator.userAgent);
  if (mobile) document.documentElement.classList.add('platform-android');
  const linux = !mobile && /Linux/.test(navigator.userAgent);
  if (linux) document.documentElement.classList.add('platform-linux');
  const api = axios.create({ baseURL: '/api', headers: { 'X-App-Token': token }, timeout: 0 });
  // Sunucu hata kodu gönderir; metin, kullanıcının seçtiği dilde burada üretilir.
  const errorInfo = (err) => {
    const data = err.response && err.response.data;
    if (data && data.code) return { code: data.code, params: data.params || {} };
    if (data && data.error) return { code: 'unexpected', params: { detail: data.error } };
    return { code: 'network', params: {} };
  };

  Vue.use(Vuex);
  Vue.use(VueRouter);
  Vue.use(VueI18n);
  Vue.use(Vuetify);

  const i18n = new VueI18n({ locale: 'tr', fallbackLocale: 'en', messages: window.APP_MESSAGES });
  const errorMessage = (info) => {
    let params = info.params || {};
    // Kaynak, çeviri izlerine ad vermez; dil kodu arayüz dilindeki adıyla gösterilir.
    if (info.code === 'translation_blocked' && params.lang) {
      const track = { lang: params.lang, name: params.name || params.lang };
      params = Object.assign({}, params, { name: languageLabel(track, i18n.locale, i18n.t('tracks.original')) });
    }
    if (info.code === 'no_language' && params.lang) {
      params = Object.assign({}, params, { lang: languageLabel({ lang: params.lang, name: params.lang }, i18n.locale, '') });
    }
    return i18n.t(`errors.${info.code}`, params);
  };
  const vuetify = new Vuetify({ icons: { iconfont: 'md' } });

  function applyTheme(id) {
    const theme = window.APP_THEMES.find((t) => t.id === id) || window.APP_THEMES[0];
    const root = document.documentElement;
    Object.entries(window.APP_THEME_TOKENS(theme)).forEach(([name, value]) => root.style.setProperty(`--${name}`, value));
    root.dataset.theme = theme.id;
    root.classList.toggle('dark-theme', theme.dark);
    vuetify.framework.theme.dark = theme.dark;
    const palette = vuetify.framework.theme.themes[theme.dark ? 'dark' : 'light'];
    palette.primary = theme.accent;
    palette.accent = theme.accent;
  }

  const store = new Vuex.Store({
    state: {
      settings: { download_dir: '', theme: 'ocean', locale: 'tr', version: '', auto_update: true },
      video: null, url: '', toast: null, files: [], hiddenFiles: 0,
    },
    mutations: {
      settings(state, value) { state.settings = Object.assign({}, state.settings, value); },
      video(state, value) { state.video = value; },
      url(state, value) { state.url = value; },
      toast(state, value) { state.toast = value; },
      files(state, value) { state.files = value.files; state.hiddenFiles = value.hidden; },
    },
    actions: {
      async loadSettings({ commit }) {
        const { data } = await api.get('/settings');
        commit('settings', data);
      },
      async saveSettings({ commit, dispatch }, values) {
        const { data } = await api.post('/settings', values);
        commit('settings', data);
        if ('download_dir' in values) await dispatch('loadFiles');
      },
      async loadFiles({ commit }) {
        const { data } = await api.get('/files');
        commit('files', data);
      },
      async refreshVideo({ commit }, id) {
        const { data } = await api.post('/refresh', { id });
        commit('video', data);
      },
    },
  });

  const notify = (text, kind, path) => store.commit('toast', { text, kind: kind || 'success', path: path || null, id: Date.now() });
  const notifyError = (err) => notify(errorMessage(errorInfo(err)), 'error');
  const reveal = (path) => api.post('/reveal', path ? { path } : {}).catch(notifyError);
  const refreshFiles = () => store.dispatch('loadFiles').catch(notifyError);

  async function requestDownload(vm, payload) {
    const { data } = await api.post('/download', payload);
    refreshFiles();
    // YouTube çeviriyi engellediyse dosya, özgün altyazının Google Çeviri ile çevrilmesiyle üretilmiştir.
    notify(vm.$t(data.google ? 'savedGoogle' : 'saved', { name: data.name }), 'success', data.path);
  }

  /* İndirme hatasını kullanıcının dilinde gösterir ve yenileyip yeniden denemeyi sunar. YouTube bir
     makine çevirisini vermediğinde, çevirinin yapıldığı özgün dili indirmeyi de önerir (canSource).
     Her denemede hata yeniden değerlendirilir: çeviri gelirse bildirim kaybolur. */
  const RetryNotice = {
    props: { info: Object, busy: Boolean, canSource: Boolean },
    computed: {
      text() { return errorMessage(this.info); },
      source() {
        const params = this.info && this.info.params;
        return this.canSource && this.info.code === 'translation_blocked' && params && params.source ? params : null;
      },
      sourceLabel() {
        const s = this.source;
        // Düğme zaten "özgün" dediği için dil adına "(özgün)" eklenmez.
        return s ? languageLabel({ lang: s.source_lang.replace(/-orig$/, ''), name: s.source_name || s.source_lang }, this.$i18n.locale, '') : '';
      },
    },
    template: `
      <div class="retry-notice" role="alert" :data-error="info.code">
        <v-icon aria-hidden="true">error_outline</v-icon>
        <div class="fill break">{{ text }}</div>
        <v-btn v-if="source" small class="retry-button" :disabled="busy" data-source-download
               @click="$emit('source', source.source)">
          <v-icon left small aria-hidden="true">file_download</v-icon>{{ $t('home.downloadSource', { lang: sourceLabel }) }}
        </v-btn>
        <v-btn small class="retry-button" :loading="busy" @click="$emit('retry')">
          <v-icon left small aria-hidden="true">refresh</v-icon>{{ $t('home.refreshRetry') }}
        </v-btn>
      </div>`,
  };

  const formatDuration = (total) => {
    if (!total) return '';
    const s = Math.round(total);
    const pad = (n) => String(n).padStart(2, '0');
    return (s >= 3600 ? `${Math.floor(s / 3600)}:` : '') + `${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)}`;
  };

  // Dil adlarını arayüz diliyle gösterir; bilinmeyen kodlarda kaynağın verdiği ada döner.
  const displayNames = {};
  const nameIn = (locale, code) => {
    try {
      // Tarayıcı motorunda bu dilin verisi yoksa (ör. Kürtçe) ad üretilmez.
      if (!Intl.DisplayNames.supportedLocalesOf([locale]).length) return null;
      displayNames[locale] = displayNames[locale] || new Intl.DisplayNames([locale], { type: 'language' });
      const name = displayNames[locale].of(code);
      return name && name !== code ? name : null;
    } catch (err) {
      return null; // Geçersiz dil kodu
    }
  };
  const languageLabel = (track, locale, originalText) => {
    const isOriginal = track.lang.endsWith('-orig');
    const code = track.lang.replace(/-orig$/, '');
    // Kaynak çeviri izlerine ad vermez (ad = kod). Arayüz dilinin adları da yoksa İngilizce ad kullanılır;
    // Kürtçe arayüz böylece her yerde kaynağın kullandığı İngilizce adları gösterir.
    const sourceName = track.name && track.name !== track.lang && track.name !== code ? track.name : null;
    const label = nameIn(locale, code) || sourceName || nameIn('en', code) || track.name;
    return isOriginal ? `${label} (${originalText})` : label;
  };

  /* Oynatma listesinde seçilebilen diller. Liste önceden bilinmediği için YouTube'un altyazı ve
     makine çevirisi sunduğu yaygın diller kullanılır; adlar arayüz dilinde gösterilir. */
  const PLAYLIST_LANGS = [
    'af', 'am', 'ar', 'az', 'be', 'bg', 'bn', 'bs', 'ca', 'cs', 'cy', 'da', 'de', 'el', 'en', 'es', 'et', 'eu',
    'fa', 'fi', 'fil', 'fr', 'ga', 'gl', 'gu', 'ha', 'hi', 'hr', 'hu', 'hy', 'id', 'is', 'it', 'iw', 'ja', 'ka',
    'kk', 'km', 'kn', 'ko', 'ku', 'ky', 'lo', 'lt', 'lv', 'mk', 'ml', 'mn', 'mr', 'ms', 'my', 'ne', 'nl', 'no',
    'pa', 'pl', 'ps', 'pt', 'ro', 'ru', 'si', 'sk', 'sl', 'so', 'sq', 'sr', 'sv', 'sw', 'ta', 'te', 'tg', 'th',
    'tk', 'tr', 'uk', 'ur', 'uz', 'vi', 'yo', 'zh-Hans', 'zh-Hant', 'zu',
  ];
  const languageItems = (locale) => PLAYLIST_LANGS
    .map((code) => ({ value: code, text: `${languageLabel({ lang: code, name: code }, locale, '')} (${code})` }))
    .sort((a, b) => a.text.localeCompare(b.text, locale));

  const Segmented = {
    props: { value: String, options: Array, label: String },
    template: `
      <div class="segmented" role="group" :aria-label="label">
        <button v-for="o in options" :key="o.value" type="button" :aria-pressed="String(o.value === value)"
                :data-option="o.value" @click="$emit('input', o.value)">{{ o.text }}</button>
      </div>`,
  };

  const TrackRows = {
    components: { RetryNotice },
    props: { tracks: Array, videoId: String, format: String },
    data() { return { busy: null, retrying: false, failures: {} }; },
    methods: {
      async download(track) {
        this.busy = track.key;
        this.$delete(this.failures, track.key);
        try {
          await requestDownload(this, { id: this.videoId, track: track.key, format: this.format });
        } catch (err) {
          this.$set(this.failures, track.key, errorInfo(err));
        } finally {
          this.busy = null;
        }
      },
      // Çevirinin yerine özgün dil indirilir; başarılı olursa çevirinin bildirimi kapanır.
      async downloadSource(track, key) {
        this.busy = track.key;
        try {
          await requestDownload(this, { id: this.videoId, track: key, format: this.format });
          this.$delete(this.failures, track.key);
        } catch (err) {
          this.$set(this.failures, track.key, errorInfo(err));
        } finally {
          this.busy = null;
        }
      },
      async refreshAndRetry(track) {
        this.retrying = true;
        try {
          await this.$store.dispatch('refreshVideo', this.videoId);
          await this.download(track);
        } catch (err) {
          this.$set(this.failures, track.key, errorInfo(err));
        } finally {
          this.retrying = false;
        }
      },
    },
    template: `
      <div class="rows">
        <div v-for="track in tracks" :key="track.key" class="track-block">
          <div class="item-row">
            <div class="row-name break">{{ track.label }}<span class="code">{{ track.lang }}</span></div>
            <v-btn small :loading="busy === track.key" :disabled="!!busy || retrying"
                   :data-track="track.key" :data-format="format"
                   :aria-label="$t('home.download') + ': ' + track.label"
                   @click="download(track)">
              <v-icon left small aria-hidden="true">file_download</v-icon>{{ $t('home.download') }}
            </v-btn>
          </div>
          <retry-notice v-if="failures[track.key]" :info="failures[track.key]" :busy="retrying || busy === track.key" can-source
                        @retry="refreshAndRetry(track)" @source="downloadSource(track, $event)"></retry-notice>
        </div>
      </div>`,
  };

  const DualPanel = {
    components: { Segmented, RetryNotice },
    props: { tracks: Array, videoId: String },
    data() { return { first: null, second: null, format: 'srt', busy: false, failure: null }; },
    computed: {
      options() { return this.tracks.map((t) => ({ value: t.key, text: `${t.label} (${t.lang})` })); },
      formats() { return ['srt', 'vtt', 'txt'].map((f) => ({ value: f, text: this.$t(`fmt.${f}`) })); },
      same() { return this.first && this.first === this.second; },
    },
    methods: {
      async download() {
        this.busy = true;
        this.failure = null;
        try {
          await requestDownload(this, { id: this.videoId, track: this.first, second_track: this.second, format: this.format });
        } catch (err) {
          this.failure = errorInfo(err);
        } finally {
          this.busy = false;
        }
      },
      async refreshAndRetry() {
        this.busy = true;
        try {
          await this.$store.dispatch('refreshVideo', this.videoId);
          await this.download();
        } catch (err) {
          this.failure = errorInfo(err);
          this.busy = false;
        }
      },
    },
    template: `
      <div class="pad">
        <p class="small muted mt-0 mb-4">{{ $t('dual.hint') }}</p>
        <div class="dual">
          <div>
            <label class="field-label" for="dual-first">{{ $t('dual.first') }}</label>
            <v-autocomplete id="dual-first" v-model="first" :items="options" dense outlined hide-details></v-autocomplete>
          </div>
          <div>
            <label class="field-label" for="dual-second">{{ $t('dual.second') }}</label>
            <v-autocomplete id="dual-second" v-model="second" :items="options" dense outlined hide-details></v-autocomplete>
          </div>
        </div>
        <div class="actions">
          <segmented v-model="format" :options="formats" :label="$t('home.format')"></segmented>
          <v-btn depressed color="primary" :loading="busy" :disabled="!first || !second || same" @click="download">
            <v-icon left small aria-hidden="true">call_merge</v-icon>{{ $t('dual.download') }}
          </v-btn>
          <span v-if="same" class="small muted" role="status">{{ $t('dual.same') }}</span>
        </div>
        <retry-notice v-if="failure" class="mt-3" :info="failure" :busy="busy" @retry="refreshAndRetry"></retry-notice>
      </div>`,
  };

  const VideoResult = {
    components: { Segmented, TrackRows, DualPanel },
    props: { video: Object },
    data() { return { query: '', format: 'srt', tab: null, thumbFailed: false, refreshing: false }; },
    methods: {
      async refreshList() {
        this.refreshing = true;
        try {
          await this.$store.dispatch('refreshVideo', this.video.id);
          notify(this.$t('home.refreshed'));
        } catch (err) {
          notifyError(err);
        } finally {
          this.refreshing = false;
        }
      },
    },
    computed: {
      duration() { return formatDuration(this.video.duration); },
      tracks() {
        const locale = this.$i18n.locale;
        const original = this.$t('tracks.original');
        return this.video.tracks
          .map((t) => Object.assign({}, t, { label: languageLabel(t, locale, original) }))
          .sort((a, b) => a.label.localeCompare(b.label, locale));
      },
      filtered() {
        const locale = this.$i18n.locale;
        const term = (this.query || '').trim().toLocaleLowerCase(locale);
        if (!term) return this.tracks;
        return this.tracks.filter((t) => `${t.label} ${t.name} ${t.lang}`.toLocaleLowerCase(locale).includes(term));
      },
      groups() {
        return ['manual', 'auto', 'translated']
          .filter((kind) => this.tracks.some((t) => t.kind === kind))
          .map((kind) => ({ kind, tracks: this.filtered.filter((t) => t.kind === kind) }));
      },
      active() { return this.tab || (this.groups[0] && this.groups[0].kind) || 'manual'; },
      current() { return this.groups.find((g) => g.kind === this.active); },
      formats() { return ['srt', 'vtt', 'txt', 'timed', 'raw'].map((f) => ({ value: f, text: this.$t(`fmt.${f}`) })); },
    },
    template: `
      <div>
        <section class="panel pad video">
          <img v-if="video.thumbnail && !thumbFailed" class="thumb" :src="video.thumbnail" alt="" referrerpolicy="no-referrer" @error="thumbFailed = true">
          <div v-else class="thumb thumb-empty"><v-icon aria-hidden="true">movie</v-icon></div>
          <div class="break">
            <h2 id="video-title" class="video-title">{{ video.title }}</h2>
            <div class="meta">
              <span v-if="video.site"><v-icon aria-hidden="true">public</v-icon>{{ video.site }}</span>
              <span v-if="video.uploader"><v-icon aria-hidden="true">person_outline</v-icon>{{ video.uploader }}</span>
              <span v-if="duration" class="num"><v-icon aria-hidden="true">schedule</v-icon>{{ duration }}</span>
              <span><v-icon aria-hidden="true">subtitles</v-icon>{{ $t('home.tracks', { count: video.tracks.length }) }}</span>
            </div>
            <v-btn id="refresh-list" small class="mt-3" :loading="refreshing" @click="refreshList">
              <v-icon left small aria-hidden="true">refresh</v-icon>{{ $t('home.refreshList') }}
            </v-btn>
          </div>
        </section>

        <section v-if="video.playlist_url" id="playlist-hint" class="panel pad playlist-hint">
          <v-icon aria-hidden="true">playlist_play</v-icon>
          <div class="fill small">{{ $t('home.fromPlaylist') }}</div>
          <v-btn small id="open-playlist" @click="$emit('open-playlist', video.playlist_url)">
            <v-icon left small aria-hidden="true">playlist_add_check</v-icon>{{ $t('home.openPlaylist') }}
          </v-btn>
        </section>

        <section v-if="!video.tracks.length" class="panel note">{{ $t('home.noTracks') }}</section>
        <section v-else class="panel">
          <div class="tabs" role="tablist">
            <button v-for="g in groups" :key="g.kind" class="tab" role="tab" type="button" :data-tab="g.kind"
                    :aria-selected="String(active === g.kind)" @click="tab = g.kind">
              {{ $t('tracks.' + g.kind) }}<span class="count">{{ g.tracks.length }}</span>
            </button>
            <button v-if="video.tracks.length > 1" class="tab" role="tab" type="button" data-tab="dual"
                    :aria-selected="String(active === 'dual')" @click="tab = 'dual'">{{ $t('tracks.dual') }}</button>
          </div>
          <dual-panel v-show="active === 'dual'" :tracks="tracks" :video-id="video.id"></dual-panel>
          <div v-show="active !== 'dual'">
            <div class="toolbar">
              <v-text-field v-model="query" class="search" :label="$t('home.search')" prepend-inner-icon="search"
                            dense outlined hide-details clearable></v-text-field>
              <div class="d-flex align-center">
                <span class="seg-label">{{ $t('home.format') }}</span>
                <segmented v-model="format" :options="formats" :label="$t('home.format')"></segmented>
              </div>
            </div>
            <track-rows v-if="current && current.tracks.length" :tracks="current.tracks" :video-id="video.id" :format="format"></track-rows>
            <div v-else class="note">{{ $t('home.noMatch') }}</div>
          </div>
        </section>
      </div>`,
  };

  const PlaylistPanel = {
    components: { Segmented },
    props: { video: Object },
    data() {
      return {
        selected: this.video.entries.map((e) => e.url), format: 'srt', allowAuto: true,
        lang: PLAYLIST_LANGS.includes(this.$i18n.locale) ? this.$i18n.locale : 'en', second: null,
        job: null, timer: null,
      };
    },
    computed: {
      running() { return !!this.job && this.job.state === 'running'; },
      percent() { return this.job && this.job.total ? this.job.done / this.job.total : 0; },
      failedCount() { return this.job && this.job.failures ? this.job.failures.length : 0; },
      formats() { return ['srt', 'vtt', 'txt', 'timed'].map((f) => ({ value: f, text: this.$t(`fmt.${f}`) })); },
      languages() { return languageItems(this.$i18n.locale); },
      same() { return !!this.second && this.second === this.lang; },
      stateLabel() {
        if (this.running) return this.$t('playlist.running');
        if (!this.job || this.job.state !== 'finished') return this.$t('playlist.cancelled');
        if (!this.job.saved) return this.$t('playlist.nothing');
        return this.failedCount ? this.$t('playlist.partial') : this.$t('playlist.finished');
      },
    },
    beforeDestroy() {
      clearInterval(this.timer);
      if (this.running) this.cancel(); // Liste ekrandan kaldırılırsa süren indirme de durdurulur
    },
    methods: {
      formatDuration,
      errorMessage,
      async start() {
        try {
          const { data } = await api.post('/playlist', {
            title: this.video.title, urls: this.selected, lang: this.lang, format: this.format, allow_auto: this.allowAuto,
            second_lang: this.second || null,
          });
          this.job = { id: data.job, state: 'running', done: 0, saved: 0, total: this.selected.length, failures: [] };
          this.timer = setInterval(() => this.poll(data.job), 1000);
        } catch (err) {
          notifyError(err);
        }
      },
      async poll(id) {
        try {
          const { data } = await api.get(`/jobs/${id}`);
          this.job = data;
          if (data.state !== 'running') {
            clearInterval(this.timer);
            refreshFiles();
          }
        } catch (err) {
          clearInterval(this.timer);
          notifyError(err);
        }
      },
      cancel() { api.post('/cancel', { job: this.job.id }).catch(notifyError); },
      openFolder() { reveal(); },
    },
    template: `
      <div>
        <section class="panel pad">
          <h2 id="video-title" class="video-title break">{{ video.title }}</h2>
          <div class="meta"><span><v-icon aria-hidden="true">playlist_play</v-icon>{{ $t('playlist.videos', { count: video.entries.length }) }}</span></div>
          <div class="options mt-4">
            <div>
              <label class="field-label" for="pl-lang">{{ $t('playlist.lang') }}</label>
              <v-autocomplete id="pl-lang" v-model="lang" :items="languages" dense outlined hide-details></v-autocomplete>
            </div>
            <div>
              <label class="field-label" for="pl-second">{{ $t('playlist.second') }}</label>
              <v-autocomplete id="pl-second" v-model="second" :items="languages" dense outlined hide-details clearable></v-autocomplete>
            </div>
            <div>
              <span class="field-label">{{ $t('playlist.format') }}</span>
              <segmented v-model="format" :options="formats" :label="$t('playlist.format')"></segmented>
            </div>
            <label class="check-label">
              <input v-model="allowAuto" type="checkbox">{{ $t('playlist.auto') }}
            </label>
          </div>
          <div class="actions">
            <v-btn v-if="!running" id="playlist-start" depressed color="primary" :disabled="!selected.length || !lang || same" @click="start">
              <v-icon left small aria-hidden="true">file_download</v-icon>{{ $t('playlist.start', { count: selected.length }) }}
            </v-btn>
            <v-btn v-else outlined class="btn-quiet" @click="cancel">
              <v-icon left small aria-hidden="true">close</v-icon>{{ $t('playlist.cancel') }}
            </v-btn>
            <span v-if="same" class="small muted" role="status">{{ $t('errors.same_language') }}</span>
            <span v-else-if="second" class="small muted">{{ $t('playlist.secondHint') }}</span>
          </div>
        </section>

        <section v-if="job" id="playlist-progress" class="panel pad" aria-live="polite">
          <div class="section-title">{{ stateLabel }}</div>
          <div class="progress-track"><div class="progress-bar" :style="{ transform: 'scaleX(' + percent + ')' }"></div></div>
          <div v-if="running && job.current" class="small muted break mb-3">{{ $t('playlist.current', { name: job.current }) }}</div>
          <div class="stats">
            <div><div class="stat-value">{{ job.done }} / {{ job.total }}</div><div class="stat-label">{{ $t('playlist.processed') }}</div></div>
            <div><div class="stat-value">{{ job.saved }}</div><div class="stat-label">{{ $t('playlist.saved') }}</div></div>
            <div><div class="stat-value">{{ failedCount }}</div><div class="stat-label">{{ $t('playlist.failed') }}</div></div>
            <v-spacer></v-spacer>
            <v-btn v-if="!running" outlined small class="btn-quiet desktop-only" @click="openFolder">
              <v-icon left small aria-hidden="true">folder_open</v-icon>{{ $t('playlist.open') }}
            </v-btn>
          </div>
        </section>

        <section v-if="failedCount" class="panel">
          <div class="pad section-title">{{ $t('playlist.failures') }}</div>
          <div v-for="(f, i) in job.failures" :key="i" class="failure break"><v-icon aria-hidden="true">error_outline</v-icon><strong>{{ f.item }}</strong>: {{ errorMessage(f) }}</div>
        </section>

        <section class="panel">
          <div class="list-head">
            <span class="small muted num">{{ $t('playlist.selected', { count: selected.length, total: video.entries.length }) }}</span>
            <v-spacer></v-spacer>
            <v-btn small text @click="selected = video.entries.map(e => e.url)">{{ $t('playlist.selectAll') }}</v-btn>
            <v-btn small text @click="selected = []">{{ $t('playlist.selectNone') }}</v-btn>
          </div>
          <div class="rows">
            <label v-for="(entry, i) in video.entries" :key="entry.url" class="check-row">
              <input v-model="selected" type="checkbox" :value="entry.url">
              <span class="index">{{ i + 1 }}</span>
              <span class="fill break">{{ entry.title }}</span>
              <span class="small muted num">{{ formatDuration(entry.duration) }}</span>
            </label>
          </div>
        </section>
      </div>`,
  };

  const Home = {
    components: { VideoResult, PlaylistPanel },
    data() { return { loading: false, error: null, mobile }; },
    computed: {
      url: {
        get() { return this.$store.state.url; },
        set(value) { this.$store.commit('url', value || ''); },
      },
      video() { return this.$store.state.video; },
      errorText() { return this.error ? errorMessage(this.error) : ''; },
    },
    methods: {
      async paste() {
        try {
          this.url = (android ? android.clipboardText() : await navigator.clipboard.readText()).trim();
        } catch (err) {
          notify(this.$t('home.pasteFailed'), 'warning');
        }
      },
      // Getirilen videoyu, hatayı ve bağlantıyı kaldırıp sayfayı ilk haline döndürür.
      clear() {
        this.error = null;
        this.url = '';
        this.$store.commit('video', null);
      },
      openPlaylist(link) {
        this.url = link;
        this.fetchInfo();
      },
      async fetchInfo() {
        if (!this.url.trim() || this.loading) return;
        this.loading = true;
        this.error = null;
        this.$store.commit('video', null);
        try {
          const { data } = await api.post('/info', { url: this.url });
          this.$store.commit('video', data);
        } catch (err) {
          this.error = errorInfo(err);
        } finally {
          this.loading = false;
        }
      },
    },
    template: `
      <div class="page">
        <h1 class="page-title">{{ $t('home.title') }}</h1>
        <p class="page-sub">{{ $t('home.sub') }}</p>

        <v-form class="panel pad" @submit.prevent="fetchInfo">
          <label class="field-label" for="url-input">{{ $t('home.label') }}</label>
          <div class="url-row">
            <v-text-field v-model="url" id="url-input" :placeholder="$t('home.placeholder')" prepend-inner-icon="link"
                          outlined dense hide-details clearable :autofocus="!mobile"></v-text-field>
            <v-btn outlined height="40" class="btn-quiet" @click="paste">
              <v-icon left small aria-hidden="true">content_paste</v-icon>{{ $t('home.paste') }}
            </v-btn>
            <v-btn id="fetch-button" type="submit" depressed color="primary" height="40" :loading="loading" :disabled="!url">{{ $t('home.fetch') }}</v-btn>
            <v-btn v-if="(video || error) && !loading" id="clear-button" outlined height="40" class="btn-quiet" @click="clear">
              <v-icon left small aria-hidden="true">close</v-icon>{{ $t('home.clear') }}
            </v-btn>
          </div>
        </v-form>

        <div v-if="error" id="error-box" class="error-box" role="alert">
          <v-icon aria-hidden="true">error_outline</v-icon>
          <div class="fill break">{{ errorText }}</div>
          <v-btn small outlined class="btn-quiet" @click="fetchInfo">{{ $t('home.retry') }}</v-btn>
        </div>

        <div v-if="loading" class="panel pad mt-4" role="status">
          <div class="video">
            <div class="thumb skeleton"></div>
            <div class="fill">
              <div class="skeleton" style="height: 18px; width: 70%"></div>
              <div class="skeleton mt-3" style="height: 12px; width: 40%"></div>
              <div class="small muted mt-4">{{ $t('home.loading') }}</div>
            </div>
          </div>
        </div>

        <div v-if="!video && !loading && !error" class="steps">
          <div v-for="n in 3" :key="n" class="panel step">
            <div class="step-num" aria-hidden="true">{{ n }}</div>
            <div class="step-title">{{ $t('home.step' + n) }}</div>
            <div class="small muted mt-1">{{ $t('home.step' + n + 'd') }}</div>
          </div>
        </div>

        <div v-if="video" class="mt-4">
          <playlist-panel v-if="video.is_playlist" :key="video.id" :video="video"></playlist-panel>
          <video-result v-else :key="video.id" :video="video" @open-playlist="openPlaylist"></video-result>
        </div>
      </div>`,
  };

  const Files = {
    data() { return { pending: null, deleting: false }; },
    computed: {
      files() { return this.$store.state.files; },
      hidden() { return this.$store.state.hiddenFiles; },
      dialogOpen: {
        get() { return !!this.pending; },
        set(value) { if (!value && !this.deleting) this.pending = null; },
      },
      confirmText() {
        if (!this.pending) return '';
        return this.pending.length === 1
          ? this.$t('files.confirmOne', { name: this.pending[0].name })
          : this.$t('files.confirmAll', { count: this.pending.length });
      },
    },
    activated() { refreshFiles(); },
    methods: {
      reveal,
      openFolder() { reveal(); },
      size(bytes) { return `${(bytes / 1024).toLocaleString(this.$i18n.locale, { maximumFractionDigits: 1 })} KB`; },
      time(seconds) {
        return new Date(seconds * 1000).toLocaleString(this.$i18n.locale, { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
      },
      async hide(list) {
        try {
          const { data } = await api.post('/files/hide', { paths: list.map((f) => f.path) });
          notify(this.$t('files.removed', { count: data.hidden }));
        } catch (err) {
          notifyError(err);
        }
        refreshFiles();
      },
      async restore() {
        try {
          await api.post('/files/restore', {});
        } catch (err) {
          notifyError(err);
        }
        refreshFiles();
      },
      async confirmDelete() {
        this.deleting = true;
        try {
          const { data } = await api.post('/files/delete', { paths: this.pending.map((f) => f.path) });
          if (data.failed.length) notify(this.$t('files.someFailed', { names: data.failed.join(', ') }), 'error');
          else notify(this.$t('files.deleted', { count: data.deleted }));
        } catch (err) {
          notifyError(err);
        }
        this.deleting = false;
        this.pending = null;
        refreshFiles();
      },
    },
    template: `
      <div class="page">
        <h1 class="page-title">{{ $t('files.title') }}</h1>
        <p class="page-sub">{{ $t('files.sub') }}</p>
        <div class="actions file-actions">
          <v-btn class="desktop-only" @click="openFolder"><v-icon left small aria-hidden="true">folder_open</v-icon>{{ $t('files.open') }}</v-btn>
          <v-btn v-if="files.length" id="clear-list" @click="hide(files)"><v-icon left small aria-hidden="true">playlist_remove</v-icon>{{ $t('files.clearList') }}</v-btn>
          <v-btn v-if="hidden" id="restore-list" @click="restore"><v-icon left small aria-hidden="true">restore</v-icon>{{ $t('files.restore', { count: hidden }) }}</v-btn>
          <v-spacer></v-spacer>
          <v-btn v-if="files.length" id="delete-all" class="btn-danger" @click="pending = files.slice()"><v-icon left small aria-hidden="true">delete_outline</v-icon>{{ $t('files.deleteAll') }}</v-btn>
        </div>
        <section v-if="files.length" class="panel mt-4">
          <div v-for="file in files" :key="file.path" class="item-row file-row" :data-file="file.name">
            <v-icon small aria-hidden="true">description</v-icon>
            <div class="row-name break">
              {{ file.name }}
              <div class="small muted num"><span v-if="file.folder">{{ file.folder }} · </span>{{ size(file.size) }} · {{ time(file.modified) }}</div>
            </div>
            <v-btn icon small class="round-button desktop-only" :title="$t('files.show')" :aria-label="$t('files.show') + ': ' + file.name" @click="reveal(file.path)"><v-icon small aria-hidden="true">folder_open</v-icon></v-btn>
            <v-btn icon small class="round-button" data-action="hide" :title="$t('files.remove')" :aria-label="$t('files.remove') + ': ' + file.name" @click="hide([file])"><v-icon small aria-hidden="true">playlist_remove</v-icon></v-btn>
            <v-btn icon small class="round-button round-danger" data-action="delete" :title="$t('files.delete')" :aria-label="$t('files.delete') + ': ' + file.name" @click="pending = [file]"><v-icon small aria-hidden="true">delete_outline</v-icon></v-btn>
          </div>
        </section>
        <section v-else class="panel note mt-4">
          <p class="mb-3">{{ $t('files.empty') }}</p>
          <v-btn color="primary" to="/">{{ $t('files.go') }}</v-btn>
        </section>
        <v-dialog v-model="dialogOpen" max-width="440" :persistent="deleting">
          <div class="panel pad dialog-card" role="alertdialog" aria-modal="true">
            <div class="section-title">{{ $t('files.confirmTitle') }}</div>
            <p id="confirm-text" class="small mt-2 mb-0 break">{{ confirmText }}</p>
            <div class="actions dialog-actions">
              <v-spacer></v-spacer>
              <v-btn id="confirm-cancel" :disabled="deleting" @click="pending = null">{{ $t('files.cancel') }}</v-btn>
              <v-btn id="confirm-delete" class="btn-danger" :loading="deleting" @click="confirmDelete">{{ $t('files.confirm') }}</v-btn>
            </div>
          </div>
        </v-dialog>
      </div>`,
  };

  const Sites = {
    data() {
      return { sites: ['YouTube', 'Vimeo', 'Dailymotion', 'TED', 'Bilibili', 'Facebook', 'Instagram', 'TikTok', 'X / Twitter', 'VK', 'RuTube', 'Twitch', 'Naver TV', 'NRK TV', 'Tubi', 'Weverse', 'Brightcove'] };
    },
    template: `
      <div class="page">
        <h1 class="page-title">{{ $t('sites.title') }}</h1>
        <p class="page-sub">{{ $t('sites.sub') }}</p>
        <section class="panel pad"><div class="site-grid"><div v-for="site in sites" :key="site" class="site">{{ site }}</div></div></section>
        <section class="panel pad">
          <div class="section-title">{{ $t('sites.limit') }}</div>
          <p class="small muted mt-1 mb-0">{{ $t('sites.limitBody') }}</p>
        </section>
      </div>`,
  };

  // Kılavuz metni i18n.js içindeki guide.sections dizisinden gelir; her bölüm bir başlık ve maddelerdir.
  const Guide = {
    computed: {
      sections() { return this.$i18n.getLocaleMessage(this.$i18n.locale).guide.sections; },
    },
    template: `
      <div class="page">
        <h1 class="page-title">{{ $t('guide.title') }}</h1>
        <p class="page-sub">{{ $t('guide.sub') }}</p>
        <section v-for="(section, index) in sections" :key="index" class="panel pad guide-section">
          <h2 class="section-title"><span class="step-num" aria-hidden="true">{{ index + 1 }}</span>{{ section.title }}</h2>
          <ul class="guide-list"><li v-for="(item, i) in section.items" :key="i">{{ item }}</li></ul>
        </section>
      </div>`,
  };

  const Settings = {
    components: { Segmented },
    data() { return { folder: this.$store.state.settings.download_dir, update: null, checking: false }; },
    computed: {
      settings() { return this.$store.state.settings; },
      autoUpdate: {
        get() { return this.settings.auto_update === false ? 'off' : 'on'; },
        set(value) { this.$store.dispatch('saveSettings', { auto_update: value === 'on' }).then(this.loadUpdate).catch(notifyError); },
      },
      onOff() { return [{ value: 'on', text: this.$t('settings.on') }, { value: 'off', text: this.$t('settings.off') }]; },
      // Motorun durumu: indirilen yeni sürüm program yeniden açılınca kullanılır.
      updateText() {
        const u = this.update;
        if (!u) return '';
        if (this.checking || u.state === 'checking') return this.$t('settings.updateChecking');
        if (u.pending) return this.$t('settings.updatePending', { version: u.pending });
        if (u.state === 'error') return this.$t('settings.updateError');
        if (u.state === 'uptodate') return this.$t('settings.updateLatest');
        return '';
      },
      locale: {
        get() { return this.settings.locale; },
        set(value) { this.$store.dispatch('saveSettings', { locale: value }).catch(notifyError); },
      },
      canChoose() { return !!tauri; }, // Klasör seçiciyi Tauri kabuğu sağlar
      themes() { return window.APP_THEMES; },
      locales() { return [{ value: 'tr', text: 'Türkçe' }, { value: 'ku', text: 'Kurdî' }, { value: 'en', text: 'English' }]; },
    },
    watch: { 'settings.download_dir'(value) { this.folder = value; } },
    created() { this.loadUpdate(); },
    methods: {
      async loadUpdate() {
        try {
          this.update = (await api.get('/update')).data;
        } catch (err) {
          this.update = null;
        }
      },
      async checkNow() {
        this.checking = true;
        try {
          this.update = (await api.post('/update/check', {})).data;
        } catch (err) {
          notifyError(err);
        } finally {
          this.checking = false;
        }
      },
      async save() {
        try {
          await this.$store.dispatch('saveSettings', { download_dir: this.folder });
          notify(this.$t('settings.saved'));
        } catch (err) {
          notifyError(err);
        }
      },
      async choose() {
        try {
          // Seçilen yol olağan ayar olarak kaydedilir.
          const picked = await tauri.core.invoke('choose_folder', { initial: this.settings.download_dir });
          if (picked) await this.$store.dispatch('saveSettings', { download_dir: picked });
        } catch (err) {
          notifyError(err);
        }
      },
      openFolder() { reveal(); },
      pickTheme(id) { this.$store.dispatch('saveSettings', { theme: id }).catch(notifyError); },
    },
    template: `
      <div class="page">
        <h1 class="page-title">{{ $t('settings.title') }}</h1>
        <p class="page-sub">{{ $t('settings.sub') }}</p>
        <section class="panel">
          <div class="pad" style="border-bottom: 1px solid var(--border)">
            <label class="setting-name" for="folder-input">{{ $t('settings.folder') }}</label>
            <div class="small muted mb-2">{{ $t('settings.folderHint') }}</div>
            <div class="folder-path mobile-only">{{ folder }}</div>
            <v-text-field id="folder-input" v-model="folder" class="desktop-only" outlined dense hide-details></v-text-field>
            <div class="actions desktop-only" style="margin-top: 12px">
              <v-btn depressed color="primary" @click="save">{{ $t('settings.save') }}</v-btn>
              <v-btn v-if="canChoose" outlined class="btn-quiet" @click="choose">{{ $t('settings.choose') }}</v-btn>
              <v-btn outlined class="btn-quiet" @click="openFolder">{{ $t('settings.open') }}</v-btn>
            </div>
          </div>
          <div class="setting-block">
            <div class="setting-name">{{ $t('settings.theme') }}</div>
            <div class="small muted">{{ $t('settings.themeHint') }}</div>
            <div class="theme-grid" role="group" :aria-label="$t('settings.theme')">
              <button v-for="t in themes" :key="t.id" type="button" class="theme-card" :data-theme-option="t.id"
                      :aria-pressed="String(settings.theme === t.id)" @click="pickTheme(t.id)">
                <span class="swatch" aria-hidden="true">
                  <span :style="{ background: t.bg }"></span>
                  <span :style="{ background: t.surface }"></span>
                  <span :style="{ background: t.accent }"></span>
                </span>
                <span class="theme-name">{{ $t('themes.' + t.id) }}</span>
                <v-icon v-if="settings.theme === t.id" class="theme-check" aria-hidden="true">check_circle</v-icon>
              </button>
            </div>
          </div>
          <div class="setting">
            <div class="setting-text"><div class="setting-name">{{ $t('settings.language') }}</div><div class="small muted">{{ $t('settings.languageHint') }}</div></div>
            <segmented v-model="locale" :options="locales" :label="$t('settings.language')"></segmented>
          </div>
          <div class="setting">
            <div class="setting-text"><div class="setting-name">{{ $t('settings.autoUpdate') }}</div><div class="small muted">{{ $t('settings.autoUpdateHint') }}</div></div>
            <segmented v-model="autoUpdate" :options="onOff" :label="$t('settings.autoUpdate')"></segmented>
          </div>
          <div class="setting">
            <div class="setting-text">
              <div class="setting-name">{{ $t('settings.about') }}</div>
              <div class="small muted">{{ $t('settings.version', { version: settings.version, engine: update ? update.version : '' }) }}</div>
              <div v-if="updateText" class="small muted" role="status" data-update-status>{{ updateText }}</div>
            </div>
            <v-btn outlined class="btn-quiet" :loading="checking" @click="checkNow">{{ $t('settings.checkNow') }}</v-btn>
          </div>
        </section>
      </div>`,
  };

  /* Çizim grafik işlemcisi yerine yazılımla yapılıyorsa (sürücüsüz Linux, sanal makine, WSL) her
     kıpırtı bütün pencerenin yeniden çizilmesine yol açar: ölçümde ışınlar tek başına dört çekirdeği
     dolduruyordu. Bunu WebGL'in bildirdiği çiziciden anlarız; WebGL hiç yoksa da yazılım sayılır.
     Linux'taki WebKitGTK gerçek çiziciyi gizler (her zaman "Apple GPU" der), o yüzden Linux'ta ışınlar
     hep durağandır; orada sürücü sorunları ve yazılımla çizim yaygındır. */
  function softwareRendering() {
    try {
      const gl = document.createElement('canvas').getContext('webgl');
      if (!gl) return true;
      const info = gl.getExtension('WEBGL_debug_renderer_info');
      const renderer = String(gl.getParameter(info ? info.UNMASKED_RENDERER_WEBGL : gl.RENDERER));
      const lose = gl.getExtension('WEBGL_lose_context');
      if (lose) lose.loseContext();
      return /llvmpipe|softpipe|swiftshader|software|basic render/i.test(renderer);
    } catch (e) {
      return true;
    }
  }

  /* Arka plan: ince bir ızgara ve çizgileri boyunca kayan renkli ışınlar (GridBeam etkisinin
     karşılığı). Hafif kalması için: ızgara bir kez boyanan sabit bir CSS degradesidir, ışınlar
     yalnızca transform ile hareket eden küçük öğelerdir (çizimi GPU birleştirici yapar, her karede
     yeniden boyama ya da bulanıklaştırma yoktur). Pencere gizliyken ışınlar durur; çizim yazılımla
     yapılıyorsa ışınlar çizgilerin üzerinde durağan kalır. */
  const GridBeamBackground = {
    template: '<div class="grid-beam-bg" aria-hidden="true"></div>',
    mounted() {
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
      const CELL = 72; // style.css içindeki --grid-cell ile aynı olmalı
      const COUNT = mobile ? 4 : 6; // Telefonda daha az ışın
      const COLORS = ['#22d3ee', '#a78bfa', '#f472b6', '#fbbf24', '#34d399', '#60a5fa'];
      const still = linux || softwareRendering();
      this.animations = [];
      this.timers = [];
      const launch = (beam, index) => {
        if (this.stopped) return;
        const horizontal = Math.random() < 0.5;
        const forward = Math.random() < 0.5;
        const length = 90 + Math.random() * 90;
        const span = horizontal ? window.innerWidth : window.innerHeight;
        const lines = Math.max(1, Math.floor((horizontal ? window.innerHeight : window.innerWidth) / CELL));
        const offset = (1 + Math.floor(Math.random() * lines)) * CELL;
        const color = COLORS[index % COLORS.length];
        beam.className = `beam ${horizontal ? 'h' : 'v'}${forward ? '' : ' rev'}`;
        beam.style.setProperty('--beam', color);
        beam.style.width = horizontal ? `${length}px` : '';
        beam.style.height = horizontal ? '' : `${length}px`;
        beam.style.left = horizontal ? '0' : `${offset}px`;
        beam.style.top = horizontal ? `${offset}px` : '0';
        const from = forward ? -length : span;
        const to = forward ? span : -length;
        const axis = horizontal ? 'X' : 'Y';
        if (still) {
          beam.style.transform = `translate${axis}(${Math.round(Math.random() * (span - length))}px)`;
          return;
        }
        const animation = beam.animate(
          [{ transform: `translate${axis}(${from}px)` }, { transform: `translate${axis}(${to}px)` }],
          { duration: (span + length) / (0.18 + Math.random() * 0.14), easing: 'linear' },
        );
        this.animations[index] = animation;
        // Bir ışın bitince kısa bir aradan sonra başka bir çizgide yeniden doğar.
        animation.onfinish = () => {
          beam.style.transform = `translate${axis}(${to}px)`;
          this.timers[index] = setTimeout(() => launch(beam, index), 400 + Math.random() * 2600);
        };
      };
      for (let i = 0; i < COUNT; i += 1) {
        const beam = document.createElement('span');
        beam.className = 'beam';
        beam.style.transform = 'translateX(-9999px)';
        this.$el.appendChild(beam);
        if (still) launch(beam, i);
        else this.timers[i] = setTimeout(() => launch(beam, i), i * 900);
      }
      // Yalnızca çalışan ışın duraklatılır ve yalnızca duraklatılan sürdürülür: bitmiş bir animasyonda
      // play() onu baştan başlatır ve bitiş olayı ikinci kez gelince o ışının döngüsü çoğalır.
      this.visibility = () => {
        this.animations.forEach((a) => {
          if (!a) return;
          if (document.hidden && a.playState === 'running') a.pause();
          else if (!document.hidden && a.playState === 'paused') a.play();
        });
      };
      document.addEventListener('visibilitychange', this.visibility);
      // Durağan ışınlar pencere boyutuna göre yerleştirilir; boyut değişince yeniden dağıtılır.
      if (still) {
        this.resize = () => {
          clearTimeout(this.resizeTimer);
          this.resizeTimer = setTimeout(() => Array.from(this.$el.children).forEach(launch), 200);
        };
        window.addEventListener('resize', this.resize);
      }
    },
    beforeDestroy() {
      this.stopped = true;
      (this.timers || []).forEach(clearTimeout);
      clearTimeout(this.resizeTimer);
      (this.animations || []).forEach((a) => a && a.cancel());
      document.removeEventListener('visibilitychange', this.visibility);
      if (this.resize) window.removeEventListener('resize', this.resize);
    },
  };

  // Android'de başka bir uygulamadan "Paylaş" ile gelen bağlantıyı uygulama bu işlevle iletir.
  window.receiveSharedLink = (link) => {
    store.commit('url', String(link || '').trim());
    if (router.currentRoute.path !== '/') router.push('/');
  };

  const router = new VueRouter({
    mode: 'hash',
    routes: [
      { path: '/', component: Home },
      { path: '/files', component: Files },
      { path: '/sites', component: Sites },
      { path: '/guide', component: Guide },
      { path: '/settings', component: Settings },
    ],
  });

  new Vue({
    el: '#app',
    i18n,
    store,
    router,
    vuetify,
    components: { GridBeamBackground },
    data() { return { showToast: false, ready: false, mobile }; },
    computed: {
      toast() { return this.$store.state.toast; },
      theme() { return this.$store.state.settings.theme; },
      locale() { return this.$store.state.settings.locale; },
      folder() { return this.$store.state.settings.download_dir; },
      compact() { return this.$vuetify.breakpoint.width < 920; },
      fileCount() { return this.$store.state.files.length; },
      navItems() {
        return [
          { to: '/', icon: 'subtitles', label: this.$t('nav.download'), exact: true },
          { to: '/files', icon: 'folder_open', label: this.$t('nav.files'), count: this.fileCount },
          { to: '/sites', icon: 'public', label: this.$t('nav.sites') },
          { to: '/guide', icon: 'menu_book', label: this.$t('nav.guide') },
          { to: '/settings', icon: 'settings', label: this.$t('nav.settings') },
        ];
      },
      toastIcon() {
        const kind = this.toast && this.toast.kind;
        return kind === 'error' ? 'error_outline' : kind === 'warning' ? 'warning_amber' : 'check_circle_outline';
      },
    },
    watch: {
      toast(value) { this.showToast = !!value; },
      theme: { immediate: true, handler(value) { applyTheme(value); } },
      locale: { immediate: true, handler(value) { this.$i18n.locale = value; document.documentElement.lang = value; } },
      $route() { this.focusMain(); },
    },
    created() {
      // Ayarlar gelene kadar arayüz gizli kalır; böylece açılışta yanlış tema görünmez.
      this.$store.dispatch('loadSettings').catch(notifyError).finally(() => { this.ready = true; });
      refreshFiles();
    },
    methods: {
      reveal,
      focusMain() { if (this.$refs.main) this.$refs.main.focus({ preventScroll: false }); },
    },
    template: `
      <v-app :class="{ compact }" :style="{ visibility: ready ? 'visible' : 'hidden' }">
        <grid-beam-background></grid-beam-background>
        <button class="skip" type="button" @click="focusMain">{{ $t('nav.skip') }}</button>
        <v-navigation-drawer app permanent class="sidebar" width="224" mini-variant-width="64" :mini-variant="compact">
          <div class="brand">
            <span class="emblem" aria-hidden="true"></span>
            <span v-if="!compact" class="brand-name">Altyazı İndirici</span>
          </div>
          <nav :aria-label="$t('nav.main')">
            <v-list class="nav" dense nav>
              <v-list-item v-for="item in navItems" :key="item.to" :to="item.to" :exact="item.exact" :aria-label="item.label" :title="compact ? item.label : null" :data-nav="item.to">
                <v-list-item-icon><v-icon aria-hidden="true">{{ item.icon }}</v-icon></v-list-item-icon>
                <v-list-item-content><v-list-item-title>{{ item.label }}</v-list-item-title></v-list-item-content>
                <span v-if="item.count && !compact" class="nav-count">{{ item.count }}</span>
              </v-list-item>
            </v-list>
          </nav>
          <template v-slot:append>
            <div v-if="!compact" class="sidebar-foot">
              <div class="label">{{ $t('settings.folder') }}</div>
              <div class="path" :title="folder">{{ folder }}</div>
              <v-btn small text class="px-1 desktop-only" @click="reveal()">{{ $t('settings.open') }}</v-btn>
            </div>
          </template>
        </v-navigation-drawer>
        <v-main>
          <div ref="main" tabindex="-1">
            <keep-alive><router-view></router-view></keep-alive>
          </div>
        </v-main>
        <v-snackbar v-model="showToast" color="#24292f" :timeout="toast && toast.kind === 'error' ? 8000 : 5000" bottom>
          <div class="d-flex align-center">
            <v-icon class="toast-icon" dark aria-hidden="true">{{ toastIcon }}</v-icon>
            <span id="snack-text" class="break">{{ toast && toast.text }}</span>
          </div>
          <template v-slot:action="{ attrs }">
            <v-btn v-if="toast && toast.path" class="desktop-only" text small dark v-bind="attrs" @click="reveal(toast.path)">{{ $t('show') }}</v-btn>
            <v-btn icon small dark v-bind="attrs" :aria-label="$t('close')" @click="showToast = false"><v-icon small aria-hidden="true">close</v-icon></v-btn>
          </template>
        </v-snackbar>
      </v-app>`,
  });
})();
