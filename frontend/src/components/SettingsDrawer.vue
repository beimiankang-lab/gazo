<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { LOCALES, type Locale } from '@/locales';
import { THEMES, type ThemeKey, useSettings } from '@/useSettings';
import { getConfig, previewTemplate, saveConfig, testDanbooru } from '@/api';
import type { DanbooruCredentials } from '@/types';

const model = defineModel<boolean>({ required: true });
const props = defineProps<{ currentDir: string }>();

const { t } = useI18n();
const settings = useSettings();

const themeOptions = computed(() =>
  (Object.keys(THEMES) as ThemeKey[]).map((key) => ({
    key,
    color: THEMES[key].accent,
    label: t(`settings.theme.${key}`),
  })),
);

const PLACEHOLDERS = [
  'id', 'query', 'artist', 'character', 'copyright',
  'index', 'ext', 'site', 'rating', 'date', 'md5', 'score',
] as const;

function placeholderDesc(name: string): string {
  return t(`settings.ph.${name}`);
}

const pathInputRef = ref<HTMLInputElement | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);
const previewSite = ref<'danbooru' | 'yande'>('danbooru');
const previewText = ref('');
const previewError = ref('');

function insertPlaceholder(target: 'path' | 'file', name: string) {
  const key = `{${name}}`;
  if (target === 'path') {
    const el = pathInputRef.value;
    if (!el) {
      settings.pathTemplate += key;
      return;
    }
    const start = el.selectionStart ?? settings.pathTemplate.length;
    const end = el.selectionEnd ?? settings.pathTemplate.length;
    settings.pathTemplate =
      settings.pathTemplate.slice(0, start) + key + settings.pathTemplate.slice(end);
    setTimeout(() => {
      el.focus();
      const pos = start + key.length;
      el.setSelectionRange(pos, pos);
    }, 0);
    return;
  }

  const el = fileInputRef.value;
  if (!el) {
    settings.fileTemplate += key;
    return;
  }
  const start = el.selectionStart ?? settings.fileTemplate.length;
  const end = el.selectionEnd ?? settings.fileTemplate.length;
  settings.fileTemplate =
    settings.fileTemplate.slice(0, start) + key + settings.fileTemplate.slice(end);
  setTimeout(() => {
    el.focus();
    const pos = start + key.length;
    el.setSelectionRange(pos, pos);
  }, 0);
}

let previewTimer: number | null = null;

async function refreshPreview() {
  if (!settings.fileTemplate.trim()) {
    previewText.value = '';
    previewError.value = t('settings.previewEmpty');
    return;
  }
  try {
    const result = await previewTemplate(previewSite.value, settings.pathTemplate, settings.fileTemplate);
    if (result.ok) {
      previewText.value = result.preview ?? '';
      previewError.value = '';
    } else {
      previewText.value = '';
      previewError.value = result.error ?? '';
    }
  } catch (e) {
    previewText.value = '';
    previewError.value = (e as Error).message;
  }
}

function schedulePreview() {
  if (previewTimer !== null) window.clearTimeout(previewTimer);
  previewTimer = window.setTimeout(refreshPreview, 250);
}

watch(
  () => [settings.pathTemplate, settings.fileTemplate, previewSite.value],
  () => schedulePreview(),
);

watch(model, (open) => {
  if (open) refreshPreview();
});

function saveCurrentAsDefault() {
  settings.defaultDir = props.currentDir;
  ElMessage.success(t('common.save'));
}

const danbooruLogin = ref('');
const danbooruApiKey = ref('');
const loginSet = ref(false);
const testLoading = ref(false);

onMounted(async () => {
  try {
    const cfg = await getConfig();
    loginSet.value = cfg.danbooru_login_set;
  } catch {
    // Ignore backend-unavailable case here.
  }
  refreshPreview();
});

async function saveDanbooruCreds() {
  const creds: DanbooruCredentials = {
    danbooru_login: danbooruLogin.value.trim(),
    danbooru_api_key: danbooruApiKey.value.trim(),
  };
  await saveConfig(creds);
  loginSet.value = !!(creds.danbooru_login && creds.danbooru_api_key);
  ElMessage.success(t('common.save'));
}

async function testDanbooruCreds() {
  testLoading.value = true;
  try {
    const result = await testDanbooru({
      danbooru_login: danbooruLogin.value.trim(),
      danbooru_api_key: danbooruApiKey.value.trim(),
    });
    if (result.ok) ElMessage.success(t('settings.danbooruTestOk', { name: result.username }));
    else ElMessage.error(t('settings.danbooruTestFail', { msg: result.error }));
  } finally {
    testLoading.value = false;
  }
}
</script>

<template>
  <el-drawer v-model="model" :title="t('settings.title')" direction="rtl" size="460px">
    <el-tabs>
      <el-tab-pane :label="t('settings.tabGeneral')">
        <div class="group">
          <label>{{ t('settings.language') }}</label>
          <el-select v-model="settings.locale" style="width: 100%">
            <el-option
              v-for="locale in LOCALES"
              :key="locale.code"
              :label="locale.label"
              :value="locale.code as Locale"
            />
          </el-select>
        </div>

        <div class="group">
          <label>{{ t('settings.themeColor') }}</label>
          <div class="theme-grid">
            <button
              v-for="option in themeOptions"
              :key="option.key"
              class="theme-swatch"
              :class="{ active: settings.theme === option.key }"
              :style="{ '--sw': option.color }"
              :title="option.label"
              @click="settings.theme = option.key"
            >
              <span class="sw-dot" />
              <span class="sw-label">{{ option.label }}</span>
            </button>
          </div>
          <p class="hint">{{ t('settings.themeDesc') }}</p>
        </div>

        <div class="group shortcuts">
          <label>{{ t('settings.shortcut') }}</label>
          <div class="kbd-row"><kbd>Ctrl</kbd>+<kbd>Enter</kbd><span>{{ t('settings.shortcutStart') }}</span></div>
          <div class="kbd-row"><kbd>Esc</kbd><span>{{ t('settings.shortcutStop') }}</span></div>
          <div class="kbd-row"><kbd>F1</kbd><span>{{ t('settings.shortcutHelp') }}</span></div>
          <div class="kbd-row"><kbd>Ctrl</kbd>+<kbd>,</kbd><span>{{ t('settings.shortcutSettings') }}</span></div>
        </div>
      </el-tab-pane>

      <el-tab-pane :label="t('settings.tabDownload')">
        <div class="group">
          <label>{{ t('settings.defaultDir') }}</label>
          <el-input v-model="settings.defaultDir" :placeholder="t('form.outputDirPlaceholder')" />
          <div class="row">
            <el-button size="small" @click="saveCurrentAsDefault">
              {{ t('settings.saveAsDefault') }}
            </el-button>
          </div>
          <p class="hint">{{ t('settings.defaultDirHint') }}</p>
        </div>

        <div class="group">
          <label>{{ t('settings.downloadConcurrencyDanbooru') }}</label>
          <el-input-number
            v-model="settings.danbooruDownloadConcurrency"
            :min="1"
            :max="8"
            :step="1"
            controls-position="right"
            style="width: 100%"
          />
          <p class="hint">{{ t('settings.downloadConcurrencyHint') }}</p>
          <p class="hint">{{ t('settings.downloadConcurrencyLevels') }}</p>
        </div>

        <div class="group">
          <label>{{ t('settings.downloadConcurrencyYande') }}</label>
          <el-input-number
            v-model="settings.yandeDownloadConcurrency"
            :min="1"
            :max="8"
            :step="1"
            controls-position="right"
            style="width: 100%"
          />
          <p class="hint">{{ t('settings.downloadConcurrencyHint') }}</p>
          <p class="hint">{{ t('settings.downloadConcurrencyLevels') }}</p>
        </div>

        <div class="group">
          <label>{{ t('settings.savePath') }}</label>
          <input
            ref="pathInputRef"
            v-model="settings.pathTemplate"
            class="tpl-input"
            :placeholder="t('settings.savePathPlaceholder')"
          />
          <div class="chip-row">
            <el-tooltip
              v-for="placeholder in PLACEHOLDERS"
              :key="`p-${placeholder}`"
              :content="placeholderDesc(placeholder)"
              placement="top"
              :show-after="150"
            >
              <button type="button" class="chip" @click="insertPlaceholder('path', placeholder)">
                {{ '{' + placeholder + '}' }}
              </button>
            </el-tooltip>
          </div>
        </div>

        <div class="group">
          <label>{{ t('settings.filename') }}</label>
          <input
            ref="fileInputRef"
            v-model="settings.fileTemplate"
            class="tpl-input"
            :placeholder="t('settings.filenamePlaceholder')"
          />
          <div class="chip-row">
            <el-tooltip
              v-for="placeholder in PLACEHOLDERS"
              :key="`f-${placeholder}`"
              :content="placeholderDesc(placeholder)"
              placement="top"
              :show-after="150"
            >
              <button type="button" class="chip" @click="insertPlaceholder('file', placeholder)">
                {{ '{' + placeholder + '}' }}
              </button>
            </el-tooltip>
          </div>
          <p class="hint">{{ t('settings.filenameHint') }}</p>
        </div>

        <div class="group">
          <div class="preview-header">
            <label class="preview-label">{{ t('settings.preview') }}</label>
            <el-radio-group v-model="previewSite" size="small">
              <el-radio-button label="danbooru">Danbooru</el-radio-button>
              <el-radio-button label="yande">Yande.re</el-radio-button>
            </el-radio-group>
          </div>
          <div v-if="previewError" class="preview-box err">{{ previewError }}</div>
          <div v-else class="preview-box">{{ previewText || '-' }}</div>
        </div>
      </el-tab-pane>

      <el-tab-pane :label="t('settings.tabApiKeys')">
        <div class="group">
          <label>{{ t('settings.danbooruApi') }}</label>
          <div class="status-line" :class="loginSet ? 'ok' : 'warn'">
            {{ loginSet ? t('settings.danbooruConfigured') : t('settings.danbooruNotConfigured') }}
          </div>
          <div class="field-row">
            <span class="field-label">{{ t('settings.danbooruLogin') }}</span>
            <el-input v-model="danbooruLogin" :placeholder="t('settings.danbooruLogin')" clearable />
          </div>
          <div class="field-row">
            <span class="field-label">{{ t('settings.danbooruApiKey') }}</span>
            <el-input
              v-model="danbooruApiKey"
              type="password"
              show-password
              :placeholder="t('settings.danbooruApiKey')"
            />
          </div>
          <p class="hint">{{ t('settings.danbooruApiHint') }}</p>
          <div class="btn-row">
            <el-button @click="saveDanbooruCreds">{{ t('common.save') }}</el-button>
            <el-button :loading="testLoading" @click="testDanbooruCreds">{{ t('settings.testConnection') }}</el-button>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-drawer>
</template>

<style scoped>
.group {
  margin-bottom: 20px;
}

.group label {
  display: block;
  margin-bottom: 8px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.hint {
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.5;
}

.row {
  margin-top: 8px;
}

.tpl-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--card);
  color: var(--text);
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 13px;
  outline: none;
  transition: border-color 0.18s;
}

.tpl-input:focus {
  border-color: var(--accent);
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.chip {
  padding: 4px 10px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--card);
  color: var(--text-muted);
  cursor: pointer;
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 11px;
  transition:
    background 0.18s,
    color 0.18s,
    border-color 0.18s;
}

.chip:hover {
  border-color: var(--accent);
  background: var(--accent);
  color: #fff;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.preview-label {
  margin-bottom: 0 !important;
}

.preview-box {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--card);
  color: var(--text);
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

.preview-box.err {
  color: var(--accent-err, #f56c6c);
  border-color: var(--accent-err, #f56c6c);
}

.theme-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.theme-swatch {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px 6px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--card);
  color: var(--text);
  font-size: 11px;
  cursor: pointer;
  transition:
    border-color 0.2s,
    transform 0.08s;
}

.theme-swatch:hover {
  border-color: var(--sw);
}

.theme-swatch.active {
  border-color: var(--sw);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--sw) 25%, transparent);
}

.theme-swatch:active {
  transform: scale(0.97);
}

.sw-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--sw);
}

.kbd-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 0;
  color: var(--text);
  font-size: 12px;
}

.kbd-row span {
  margin-left: 10px;
  color: var(--text-muted);
}

kbd {
  padding: 1px 6px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--card);
  color: var(--text);
  font-family: 'Consolas', monospace;
  font-size: 11px;
}

.status-line {
  margin-bottom: 12px;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
}

.status-line.ok {
  border: 1px solid rgba(61, 220, 132, 0.25);
  background: rgba(61, 220, 132, 0.1);
  color: var(--accent-ok);
}

.status-line.warn {
  border: 1px solid var(--border);
  background: rgba(107, 122, 153, 0.1);
  color: var(--text-muted);
}

.field-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 10px;
}

.field-label {
  color: var(--text-muted);
  font-size: 12px;
}

.btn-row {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
</style>
