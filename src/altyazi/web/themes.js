/* Renk temaları. Yeni tema eklerken kimliğini server.py içindeki THEMES kümesine de ekleyin. */
(function () {
  'use strict';

  const light = (id, c) => Object.assign({ id, dark: false, surface: '#ffffff' }, c);
  const dark = (id, c) => Object.assign({ id, dark: true }, c);

  const themes = [
    light('ocean', { bg: '#f4f5f7', surface2: '#eef0f3', sidebar: '#fbfbfc', border: '#dfe2e6', frame: '#868f99', text: '#1b1f24', muted: '#57606a', accent: '#0f6cbd', onAccent: '#ffffff', accentSoft: '#e6f1fa', accentText: '#0c5a9e' }),
    light('emerald', { bg: '#f2f6f3', surface2: '#ebf1ed', sidebar: '#f9fbf9', border: '#dbe5de', frame: '#84958a', text: '#17231c', muted: '#4f6157', accent: '#0b7a4b', onAccent: '#ffffff', accentSoft: '#e3f4ea', accentText: '#08623c' }),
    light('amethyst', { bg: '#f5f3f9', surface2: '#eeebf4', sidebar: '#fbfafd', border: '#e3deee', frame: '#8f88a3', text: '#1f1a2b', muted: '#5c5570', accent: '#6b3fc4', onAccent: '#ffffff', accentSoft: '#efe9fb', accentText: '#5631a3' }),
    light('rose', { bg: '#f9f3f5', surface2: '#f3eaee', sidebar: '#fdfafb', border: '#eedde3', frame: '#9f8890', text: '#2a1a20', muted: '#6b525b', accent: '#c2255c', onAccent: '#ffffff', accentSoft: '#fbe8ef', accentText: '#a31d4c' }),
    light('amber', { bg: '#f8f5ee', surface2: '#f2ede2', sidebar: '#fdfbf6', border: '#e8e1d0', frame: '#98907c', text: '#261f12', muted: '#635a47', accent: '#a85b00', onAccent: '#ffffff', accentSoft: '#fbefd9', accentText: '#8a4b00' }),
    dark('graphite', { bg: '#15171a', surface: '#1e2125', surface2: '#2a2e33', sidebar: '#1a1c20', border: '#33383e', frame: '#7d8590', text: '#e8eaed', muted: '#adb5bd', accent: '#5cb0f2', onAccent: '#0b1a26', accentSoft: '#1b3347', accentText: '#8cc8f7' }),
    dark('midnight', { bg: '#0e1525', surface: '#162036', surface2: '#1e2a45', sidebar: '#121a2e', border: '#2c3a58', frame: '#7686a6', text: '#e6ebf5', muted: '#a6b2c9', accent: '#6ea8fe', onAccent: '#0a1628', accentSoft: '#1c2f52', accentText: '#9cc4ff' }),
    dark('forest', { bg: '#101814', surface: '#18231d', surface2: '#203029', sidebar: '#141d18', border: '#2f4238', frame: '#76917f', text: '#e4efe8', muted: '#a3b8ab', accent: '#4cc38a', onAccent: '#07190f', accentSoft: '#1a3a2b', accentText: '#7fdcae' }),
    dark('wine', { bg: '#1a1016', surface: '#251820', surface2: '#32202b', sidebar: '#1f131a', border: '#46303c', frame: '#99808c', text: '#f2e7ec', muted: '#bda8b2', accent: '#f277a8', onAccent: '#2a0a18', accentSoft: '#47202f', accentText: '#f7a3c4' }),
  ];

  const mix = (a, b, amount) => {
    const channel = (hex, i) => parseInt(hex.slice(1 + i * 2, 3 + i * 2), 16);
    const out = [0, 1, 2].map((i) => Math.round(channel(a, i) * (1 - amount) + channel(b, i) * amount));
    return `#${out.map((v) => v.toString(16).padStart(2, '0')).join('')}`;
  };

  /* Bir temanın CSS değişkenlerini üretir. 3B yüzeyler temel renklerden türetilir. */
  const tokens = (t) => ({
    bg: t.bg,
    surface: t.surface,
    'surface-2': t.surface2,
    sidebar: t.sidebar,
    border: t.border,
    frame: t.frame,
    text: t.text,
    muted: t.muted,
    accent: t.accent,
    'on-accent': t.onAccent,
    'accent-soft': t.accentSoft,
    'accent-text': t.accentText,
    // Metin kontrastı en zayıf noktada bile korunsun diye vurgu geçişi, yazıdan uzaklaşan yöne gider.
    'accent-top': t.dark ? mix(t.accent, '#ffffff', 0.18) : t.accent,
    'accent-bottom': t.dark ? t.accent : mix(t.accent, '#000000', 0.18),
    'accent-edge': mix(t.accent, '#000000', 0.4),
    'face-top': t.dark ? mix(t.surface2, '#ffffff', 0.1) : '#ffffff',
    'face-bottom': t.dark ? t.surface2 : mix(t.bg, '#000000', 0.05),
    'face-edge': t.dark ? mix(t.bg, '#000000', 0.35) : mix(t.frame, '#000000', 0.15),
    bevel: t.dark ? 'rgba(255, 255, 255, .14)' : 'rgba(255, 255, 255, .95)',
    drop: t.dark ? 'rgba(0, 0, 0, .5)' : 'rgba(0, 0, 0, .18)',
    hover: t.dark ? 'rgba(255, 255, 255, .06)' : 'rgba(0, 0, 0, .04)',
    danger: t.dark ? '#ff8fa0' : '#b4233c',
    'danger-top': t.dark ? '#ffa6b4' : '#c42a45',
    'danger-bottom': t.dark ? '#ff8fa0' : '#a01e35',
    'danger-edge': t.dark ? '#b8505f' : '#7a1628',
    'on-danger': t.dark ? '#2a0a12' : '#ffffff',
    'danger-soft': t.dark ? mix(t.surface, '#ff3b5c', 0.14) : '#fbecee',
    skeleton: t.dark ? t.surface2 : t.border,
  });

  window.APP_THEMES = themes;
  window.APP_THEME_TOKENS = tokens;
})();
