import { reactive, watch } from 'vue';
import type { Locale } from '@/locales';
import { setLocale } from '@/locales';

export type ThemeKey = 'purple' | 'sky' | 'pink' | 'mint' | 'amber' | 'coral';

export interface ThemeSpec {
  key: ThemeKey;
  accent: string;
  accentLight: string;
  accentDark: string;
}

export const THEMES: Record<ThemeKey, ThemeSpec> = {
  purple: { key: 'purple', accent: '#7c6aff', accentLight: '#9486ff', accentDark: '#6352e8' },
  sky: { key: 'sky', accent: '#38bdf8', accentLight: '#7dd3fc', accentDark: '#0284c7' },
  pink: { key: 'pink', accent: '#ec4899', accentLight: '#f472b6', accentDark: '#be185d' },
  mint: { key: 'mint', accent: '#34d399', accentLight: '#6ee7b7', accentDark: '#059669' },
  amber: { key: 'amber', accent: '#f59e0b', accentLight: '#fbbf24', accentDark: '#b45309' },
  coral: { key: 'coral', accent: '#fb7185', accentLight: '#fda4af', accentDark: '#e11d48' },
};

export type TemplatePreset = 'default' | 'byId' | 'byArtist' | 'flat' | 'custom';

export interface Settings {
  locale: Locale;
  theme: ThemeKey;
  defaultDir: string;
  templatePreset: TemplatePreset;
  templateCustom: string;
  rating: { safe: boolean; questionable: boolean; explicit: boolean };
  fileTypes: { image: boolean; animated: boolean; video: boolean };
  maxSizeMb: number | null;
}

const STORAGE_KEY = 'gazo:settings:v1';

function load(): Settings {
  const defaults: Settings = {
    locale: (localStorage.getItem('gazo:locale') as Locale) || 'en',
    theme: 'purple',
    defaultDir: '',
    templatePreset: 'default',
    templateCustom: '{tag}({artist})_{character}{index}.{ext}',
    rating: { safe: false, questionable: false, explicit: false },
    fileTypes: { image: true, animated: true, video: true },
    maxSizeMb: null,
  };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaults;
    const parsed = JSON.parse(raw) as Partial<Settings>;
    return {
      ...defaults,
      ...parsed,
      rating: { ...defaults.rating, ...(parsed.rating ?? {}) },
      fileTypes: { ...defaults.fileTypes, ...(parsed.fileTypes ?? {}) },
    };
  } catch {
    return defaults;
  }
}

const state = reactive<Settings>(load());

function applyTheme(key: ThemeKey) {
  const spec = THEMES[key];
  const root = document.documentElement.style;
  root.setProperty('--accent', spec.accent);
  root.setProperty('--accent-light', spec.accentLight);
  root.setProperty('--accent-dark', spec.accentDark);
  root.setProperty('--el-color-primary', spec.accent);
  root.setProperty('--el-color-primary-light-3', spec.accentLight);
  root.setProperty('--el-color-primary-dark-2', spec.accentDark);
}

applyTheme(state.theme);
setLocale(state.locale);

watch(
  () => state.theme,
  (key) => applyTheme(key),
);

watch(
  () => state.locale,
  (loc) => setLocale(loc),
);

watch(
  state,
  (val) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(val));
  },
  { deep: true },
);

export function useSettings() {
  return state;
}

export function buildRatingFragment(site: 'danbooru' | 'yande'): string {
  const r = state.rating;
  const picks: string[] = [];
  if (r.safe) picks.push('s');
  if (r.questionable) picks.push('q');
  if (r.explicit) picks.push('e');
  if (picks.length === 0 || picks.length === 3) return '';
  if (site === 'danbooru') {
    if (picks.length === 1) return `rating:${picks[0]}`;
    return `rating:${picks.join(',')}`;
  }
  if (picks.length === 1) return `rating:${picks[0]}`;
  return `(${picks.map((p) => `rating:${p}`).join(' OR ')})`;
}
