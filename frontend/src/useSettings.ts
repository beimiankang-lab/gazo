import { reactive, watch } from 'vue';
import type { Locale } from '@/locales';
import { setLocale } from '@/locales';
import type { Site } from '@/types';

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

export interface RatingSettings {
  safe: boolean;
  questionable: boolean;
  explicit: boolean;
}

export interface FileTypeSettings {
  image: boolean;
  animated: boolean;
  video: boolean;
}

export interface SiteFormSettings {
  query: string;
  outputDir: string;
  includeDeleted: boolean;
  rating: RatingSettings;
  fileTypes: FileTypeSettings;
  maxSizeMb: number | null;
  blacklist: string[];
  whitelist: string[];
  limitEnabled: boolean;
  maxPosts: number;
}

export interface Settings {
  locale: Locale;
  theme: ThemeKey;
  defaultDir: string;
  danbooruDownloadConcurrency: number;
  yandeDownloadConcurrency: number;
  templatePreset: TemplatePreset;
  templateCustom: string;
  pathTemplate: string;
  fileTemplate: string;
  sites: Record<Site, SiteFormSettings>;
}

const STORAGE_KEY = 'gazo:settings:v1';

function defaultRating(): RatingSettings {
  return { safe: false, questionable: false, explicit: false };
}

function defaultFileTypes(): FileTypeSettings {
  return { image: true, animated: true, video: true };
}

function makeSiteDefaults(includeDeleted = false): SiteFormSettings {
  return {
    query: '',
    outputDir: '',
    includeDeleted,
    rating: defaultRating(),
    fileTypes: defaultFileTypes(),
    maxSizeMb: null,
    blacklist: [],
    whitelist: [],
    limitEnabled: false,
    maxPosts: 100,
  };
}

function normalizeStringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.map((item) => String(item ?? '').trim()).filter(Boolean)
    : [];
}

function clampConcurrency(value: unknown, fallback: number): number {
  return typeof value === 'number'
    ? Math.min(8, Math.max(1, Math.trunc(value)))
    : fallback;
}

function normalizeSiteForm(value: unknown, fallback: SiteFormSettings): SiteFormSettings {
  const raw = (value ?? {}) as Partial<SiteFormSettings>;
  return {
    ...fallback,
    ...raw,
    query: typeof raw.query === 'string' ? raw.query : fallback.query,
    outputDir: typeof raw.outputDir === 'string' ? raw.outputDir : fallback.outputDir,
    includeDeleted: typeof raw.includeDeleted === 'boolean' ? raw.includeDeleted : fallback.includeDeleted,
    rating: { ...fallback.rating, ...(raw.rating ?? {}) },
    fileTypes: { ...fallback.fileTypes, ...(raw.fileTypes ?? {}) },
    maxSizeMb:
      typeof raw.maxSizeMb === 'number' && Number.isFinite(raw.maxSizeMb)
        ? raw.maxSizeMb
        : raw.maxSizeMb === null
          ? null
          : fallback.maxSizeMb,
    blacklist: normalizeStringList(raw.blacklist),
    whitelist: normalizeStringList(raw.whitelist),
    limitEnabled: typeof raw.limitEnabled === 'boolean' ? raw.limitEnabled : fallback.limitEnabled,
    maxPosts:
      typeof raw.maxPosts === 'number' && Number.isFinite(raw.maxPosts) && raw.maxPosts > 0
        ? Math.trunc(raw.maxPosts)
        : fallback.maxPosts,
  };
}

function load(): Settings {
  const defaults: Settings = {
    locale: (localStorage.getItem('gazo:locale') as Locale) || 'en',
    theme: 'purple',
    defaultDir: '',
    danbooruDownloadConcurrency: 4,
    yandeDownloadConcurrency: 4,
    templatePreset: 'default',
    templateCustom: '{tag}({artist})_{character}{index}.{ext}',
    pathTemplate: '{site}/{artist}',
    fileTemplate: '{query}_{id}.{ext}',
    sites: {
      danbooru: makeSiteDefaults(true),
      yande: makeSiteDefaults(false),
    },
  };

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaults;

    const parsed = JSON.parse(raw) as Partial<Settings> & {
      downloadConcurrency?: number;
      rating?: RatingSettings;
      fileTypes?: FileTypeSettings;
      maxSizeMb?: number | null;
      blacklist?: string[];
      whitelist?: string[];
    };
    const legacyConcurrency = clampConcurrency(parsed.downloadConcurrency, defaults.danbooruDownloadConcurrency);

    const legacyDanbooru = {
      query: '',
      outputDir: '',
      includeDeleted: false,
      rating: { ...defaults.sites.danbooru.rating, ...(parsed.rating ?? {}) },
      fileTypes: { ...defaults.sites.danbooru.fileTypes, ...(parsed.fileTypes ?? {}) },
      maxSizeMb:
        typeof parsed.maxSizeMb === 'number' && Number.isFinite(parsed.maxSizeMb)
          ? parsed.maxSizeMb
          : parsed.maxSizeMb === null
            ? null
            : defaults.sites.danbooru.maxSizeMb,
      blacklist: normalizeStringList(parsed.blacklist),
      whitelist: normalizeStringList(parsed.whitelist),
      limitEnabled: false,
      maxPosts: 100,
    };

    const legacyYande = {
      ...legacyDanbooru,
      includeDeleted: false,
    };

    return {
      ...defaults,
      ...parsed,
      danbooruDownloadConcurrency: clampConcurrency(
        parsed.danbooruDownloadConcurrency,
        legacyConcurrency,
      ),
      yandeDownloadConcurrency: clampConcurrency(
        parsed.yandeDownloadConcurrency,
        defaults.yandeDownloadConcurrency,
      ),
      sites: {
        danbooru: normalizeSiteForm(parsed.sites?.danbooru, {
          ...defaults.sites.danbooru,
          ...legacyDanbooru,
        }),
        yande: normalizeSiteForm(parsed.sites?.yande, {
          ...defaults.sites.yande,
          ...legacyYande,
        }),
      },
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

export function getSiteSettings(site: Site): SiteFormSettings {
  return state.sites[site];
}

export function getRatingPicks(site: Site): string[] {
  const r = state.sites[site].rating;
  const picks: string[] = [];
  if (r.safe) picks.push('s');
  if (r.questionable) picks.push('q');
  if (r.explicit) picks.push('e');
  if (picks.length === 3) return [];
  return picks;
}

export function buildRatingFragment(site: Site): string {
  const picks = getRatingPicks(site);
  if (picks.length === 0) return '';
  if (site === 'danbooru') {
    if (picks.length === 1) return `rating:${picks[0]}`;
    return `rating:${picks.join(',')}`;
  }
  // Yande.re API 不支持逗号分隔多评级，多评级时通过 ratings[] 参数分次获取
  // 单评级仍嵌入 query 中以复用缓存
  if (picks.length === 1) return `rating:${picks[0]}`;
  return '';
}

export function buildTagListFragment(site: Site): string {
  const seen = new Set<string>();
  const parts: string[] = [];
  const form = state.sites[site];

  for (const raw of form.whitelist) {
    const tag = raw.trim();
    if (tag && !seen.has(tag)) {
      seen.add(tag);
      parts.push(tag);
    }
  }

  for (const raw of form.blacklist) {
    const tag = raw.trim();
    if (!tag) continue;
    const key = `-${tag}`;
    if (!seen.has(key)) {
      seen.add(key);
      parts.push(key);
    }
  }

  return parts.join(' ');
}
