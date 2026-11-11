/* global Vue, Vuex, VueRouter, VueI18n, Vuetify, axios */
(function () {
  'use strict';

  const token = new URLSearchParams(window.location.search).get('token') || '';
  const tauri = window.__TAURI__ || null; // Yalnızca Tauri kabuğunda tanımlıdır
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
  const errorMessage = (info) => i18n.t(`errors.${info.code}`, info.params);
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
      settings: { download_dir: '', theme: 'ocean', locale: 'tr', version: '', can_choose: false },
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
    notify(vm.$t('saved', { name: data.name }), 'success', data.path);
  }

  /* İndirme hatasını kullanıcının dilinde gösterir ve yenileyip yeniden denemeyi sunar. */
  const RetryNotice = {
    props: { info: Object, busy: Boolean },
    computed: { text() { return errorMessage(this.info); } },
    template: `
      <div class="retry-notice" role="alert">
        <v-icon aria-hidden="true">error_outline</v-icon>
        <div class="fill break">{{ text }}</div>
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
  const languageLabel = (track, locale, originalText) => {
    const isOriginal = track.lang.endsWith('-orig');
    const code = track.lang.replace(/-orig$/, '');
    let label = track.name;
    try {
      // Tarayıcı motorunda bu dilin verisi yoksa kaynağın verdiği ada dönülür.
      if (Intl.DisplayNames.supportedLocalesOf([locale]).length) {
        displayNames[locale] = displayNames[locale] || new Intl.DisplayNames([locale], { type: 'language' });
        const localized = displayNames[locale].of(code);
        if (localized && localized !== code) label = localized;
      }
    } catch (err) {
      label = track.name; // Geçersiz dil kodu
    }
    return isOriginal ? `${label} (${originalText})` : label;
  };

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
          <retry-notice v-if="failures[track.key]" :info="failures[track.key]" :busy="retrying || busy === track.key" @retry="refreshAndRetry(track)"></retry-notice>
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
        selected: this.video.entries.map((e) => e.url), lang: 'tr', format: 'srt', allowAuto: true,
        job: null, timer: null,
      };
    },
    computed: {
      running() { return !!this.job && this.job.state === 'running'; },
      percent() { return this.job && this.job.total ? this.job.done / this.job.total : 0; },
      failedCount() { return this.job && this.job.failures ? this.job.failures.length : 0; },
      formats() { return ['srt', 'vtt', 'txt', 'timed'].map((f) => ({ value: f, text: this.$t(`fmt.${f}`) })); },
      stateLabel() {
        if (this.running) return this.$t('playlist.running');
        if (!this.job || this.job.state !== 'finished') return this.$t('playlist.cancelled');
        if (!this.job.saved) return this.$t('playlist.nothing');
        return this.failedCount ? this.$t('playlist.partial') : this.$t('playlist.finished');
      },
    },
    beforeDestroy() { clearInterval(this.timer); },
    methods: {
      formatDuration,
      errorMessage,
      async start() {
        try {
          const { data } = await api.post('/playlist', {
            title: this.video.title, urls: this.selected, lang: this.lang, format: this.format, allow_auto: this.allowAuto,
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
              <v-text-field id="pl-lang" v-model="lang" :hint="$t('playlist.langHint')" dense outlined hide-details></v-text-field>
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
            <v-btn v-if="!running" id="playlist-start" depressed color="primary" :disabled="!selected.length || !lang.trim()" @click="start">
              <v-icon left small aria-hidden="true">file_download</v-icon>{{ $t('playlist.start', { count: selected.length }) }}
            </v-btn>
            <v-btn v-else outlined class="btn-quiet" @click="cancel">
              <v-icon left small aria-hidden="true">close</v-icon>{{ $t('playlist.cancel') }}
            </v-btn>
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
            <v-btn v-if="!running" outlined small class="btn-quiet" @click="openFolder">
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
    data() { return { loading: false, error: null }; },
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
          this.url = (await navigator.clipboard.readText()).trim();
        } catch (err) {
          notify(this.$t('home.pasteFailed'), 'warning');
        }
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
                          outlined dense hide-details clearable autofocus></v-text-field>
            <v-btn outlined height="40" class="btn-quiet" @click="paste">
              <v-icon left small aria-hidden="true">content_paste</v-icon>{{ $t('home.paste') }}
            </v-btn>
            <v-btn id="fetch-button" type="submit" depressed color="primary" height="40" :loading="loading" :disabled="!url">{{ $t('home.fetch') }}</v-btn>
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
          <video-result v-else :key="video.id" :video="video"></video-result>
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
          <v-btn @click="openFolder"><v-icon left small aria-hidden="true">folder_open</v-icon>{{ $t('files.open') }}</v-btn>
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
            <v-btn icon small class="round-button" :title="$t('files.show')" :aria-label="$t('files.show') + ': ' + file.name" @click="reveal(file.path)"><v-icon small aria-hidden="true">folder_open</v-icon></v-btn>
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

  const Settings = {
    components: { Segmented },
    data() { return { folder: this.$store.state.settings.download_dir }; },
    computed: {
      settings() { return this.$store.state.settings; },
      locale: {
        get() { return this.settings.locale; },
        set(value) { this.$store.dispatch('saveSettings', { locale: value }).catch(notifyError); },
      },
      canChoose() { return this.settings.can_choose || !!tauri; },
      themes() { return window.APP_THEMES; },
      locales() { return [{ value: 'tr', text: 'Türkçe' }, { value: 'ku', text: 'Kurdî' }, { value: 'en', text: 'English' }]; },
    },
    watch: { 'settings.download_dir'(value) { this.folder = value; } },
    methods: {
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
          if (tauri) {
            // Tauri kabuğunda klasör seçiciyi kabuk açar; seçilen yol olağan ayar olarak kaydedilir.
            const picked = await tauri.core.invoke('choose_folder', { initial: this.settings.download_dir });
            if (picked) await this.$store.dispatch('saveSettings', { download_dir: picked });
            return;
          }
          const { data } = await api.post('/choose-folder', {});
          this.$store.commit('settings', data);
          refreshFiles();
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
            <v-text-field id="folder-input" v-model="folder" outlined dense hide-details></v-text-field>
            <div class="actions" style="margin-top: 12px">
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
            <div class="setting-text"><div class="setting-name">{{ $t('settings.about') }}</div><div class="small muted">{{ $t('settings.version', { version: settings.version }) }}</div></div>
          </div>
        </section>
      </div>`,
  };

  /* Arka plan: imleç hareket ettikçe arkasında dağılan renkli lekeler, tıklayınca
     sıçrama (React Bits SplashCursor etkisinin yaklaşık karşılığı). Özgün bileşen WebGL ile tam
     bir sıvı benzetimi yapar; burada aynı izlenim, sürüklenip dönen ve sönen yumuşak lekelerle
     2B tuvalde verilir. Lekeler yokken çizim döngüsü durur. */
  const SplashBackground = {
    template: '<canvas class="splash-bg" aria-hidden="true"></canvas>',
    mounted() {
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
      const canvas = this.$el;
      const ctx = canvas.getContext('2d');
      // Özgün bileşene verilen değerler size 1.4 ve trail 1.6 idi; iz daha sakin olsun diye azaltıldı.
      const SIZE = 1, FORCE = 0.8, SWIRL = 1, TRAIL = 1.1, MOMENTUM = 0.6;
      const SCALE = 0.5; // Bulanık görüntü için yarı çözünürlük yeterlidir
      const sprites = ['#ff3d00', '#ff9100', '#ffd600'].map((color) => {
        const sprite = document.createElement('canvas');
        sprite.width = sprite.height = 128;
        const g = sprite.getContext('2d');
        const gradient = g.createRadialGradient(64, 64, 0, 64, 64, 64);
        gradient.addColorStop(0, color);
        gradient.addColorStop(0.45, `${color}99`);
        gradient.addColorStop(1, `${color}00`);
        g.fillStyle = gradient;
        g.fillRect(0, 0, 128, 128);
        return sprite;
      });
      let blobs = [];
      let last = null;
      let previous = 0;
      let next = 0;
      const frame = (now) => {
        const dt = Math.min((now - previous) / 1000, 0.05);
        previous = now;
        const dark = document.documentElement.classList.contains('dark-theme');
        const retain = Math.pow(0.05 + MOMENTUM * 0.25, dt);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        // Koyu zeminde renkler toplanarak parlar; açık zeminde toplama görünmez olduğu için üst üste boyanır.
        ctx.globalCompositeOperation = dark ? 'lighter' : 'source-over';
        blobs.forEach((b) => {
          const angle = SWIRL * b.spin * 1.5 * dt;
          const cos = Math.cos(angle), sin = Math.sin(angle);
          const vx = (b.vx * cos - b.vy * sin) * retain;
          b.vy = (b.vx * sin + b.vy * cos) * retain;
          b.vx = vx;
          b.x += b.vx * dt;
          b.y += b.vy * dt;
          b.r += 26 * SIZE * dt;
          b.life -= dt / TRAIL;
          if (b.life <= 0) return;
          ctx.globalAlpha = (dark ? 0.36 : 0.6) * b.life * b.life;
          ctx.drawImage(b.sprite, (b.x - b.r) * SCALE, (b.y - b.r) * SCALE, b.r * 2 * SCALE, b.r * 2 * SCALE);
        });
        blobs = blobs.filter((b) => b.life > 0);
        this.raf = blobs.length ? requestAnimationFrame(frame) : null;
      };
      const spawn = (x, y, vx, vy, radius) => {
        blobs.push({ x, y, vx, vy, r: radius * SIZE * (0.7 + Math.random() * 0.6), life: 1, spin: Math.random() * 2 - 1, sprite: sprites[next++ % sprites.length] });
        if (blobs.length > 220) blobs.shift();
        if (!this.raf) {
          previous = performance.now();
          this.raf = requestAnimationFrame(frame);
        }
      };
      const splash = (x, y) => {
        for (let i = 0; i < 9; i += 1) {
          const angle = (i / 9) * Math.PI * 2 + Math.random() * 0.4;
          const speed = 260 * FORCE * (0.5 + Math.random());
          spawn(x, y, Math.cos(angle) * speed, Math.sin(angle) * speed, 46);
        }
      };
      this.move = (event) => {
        const point = { x: event.clientX, y: event.clientY };
        if (!last) { last = point; return; }
        const dx = point.x - last.x, dy = point.y - last.y;
        const distance = Math.hypot(dx, dy);
        if (distance < 4) return;
        const steps = Math.min(2, Math.ceil(distance / 40));
        for (let i = 1; i <= steps; i += 1) {
          spawn(last.x + (dx * i) / steps, last.y + (dy * i) / steps,
            dx * FORCE * 10 + Math.random() * 40 - 20, dy * FORCE * 10 + Math.random() * 40 - 20, 30);
        }
        last = point;
      };
      this.down = (event) => splash(event.clientX, event.clientY);
      this.resize = () => {
        canvas.width = Math.ceil(window.innerWidth * SCALE);
        canvas.height = Math.ceil(window.innerHeight * SCALE);
      };
      window.addEventListener('pointermove', this.move, { passive: true });
      window.addEventListener('pointerdown', this.down, { passive: true });
      window.addEventListener('resize', this.resize);
      this.resize();
      splash(window.innerWidth / 2, window.innerHeight / 2); // Açılışta etkinin var olduğunu gösterir
    },
    beforeDestroy() {
      cancelAnimationFrame(this.raf);
      window.removeEventListener('pointermove', this.move);
      window.removeEventListener('pointerdown', this.down);
      window.removeEventListener('resize', this.resize);
    },
  };

  const router = new VueRouter({
    mode: 'hash',
    routes: [
      { path: '/', component: Home },
      { path: '/files', component: Files },
      { path: '/sites', component: Sites },
      { path: '/settings', component: Settings },
    ],
  });

  new Vue({
    el: '#app',
    i18n,
    store,
    router,
    vuetify,
    components: { SplashBackground },
    data() { return { showToast: false, ready: false }; },
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
        <splash-background></splash-background>
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
              <v-btn small text class="px-1" @click="reveal()">{{ $t('settings.open') }}</v-btn>
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
            <v-btn v-if="toast && toast.path" text small dark v-bind="attrs" @click="reveal(toast.path)">{{ $t('show') }}</v-btn>
            <v-btn icon small dark v-bind="attrs" :aria-label="$t('close')" @click="showToast = false"><v-icon small aria-hidden="true">close</v-icon></v-btn>
          </template>
        </v-snackbar>
      </v-app>`,
  });
})();
