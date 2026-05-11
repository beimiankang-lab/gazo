import { createI18n } from 'vue-i18n';
import en from './en';
import zhCN from './zh-CN';
import zhTW from './zh-TW';
import ja from './ja';

export type Locale = 'en' | 'zh-CN' | 'zh-TW' | 'ja';

export const LOCALES: { code: Locale; label: string }[] = [
  { code: 'en', label: 'English' },
  { code: 'zh-CN', label: '简体中文' },
  { code: 'zh-TW', label: '繁體中文' },
  { code: 'ja', label: '日本語' },
];

function detectLocale(): Locale {
  const stored = localStorage.getItem('gazo:locale') as Locale | null;
  if (stored && LOCALES.some((l) => l.code === stored)) return stored;
  const nav = (navigator.language || 'en').toLowerCase();
  if (nav.startsWith('zh')) {
    if (nav.includes('tw') || nav.includes('hk') || nav.includes('mo')) return 'zh-TW';
    return 'zh-CN';
  }
  if (nav.startsWith('ja')) return 'ja';
  return 'en';
}

export const i18n = createI18n({
  legacy: false,
  locale: detectLocale(),
  fallbackLocale: 'en',
  messages: {
    en,
    'zh-CN': zhCN,
    'zh-TW': zhTW,
    ja,
  },
});

export function setLocale(locale: Locale) {
  i18n.global.locale.value = locale;
  localStorage.setItem('gazo:locale', locale);
  document.documentElement.lang = locale;
}
