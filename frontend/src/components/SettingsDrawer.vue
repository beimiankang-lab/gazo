<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { LOCALES, type Locale } from '@/locales';
import { THEMES, type ThemeKey, type TemplatePreset, useSettings } from '@/useSettings';

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

const presetOptions = computed<{ value: TemplatePreset; label: string }[]>(() => [
  { value: 'default', label: t('settings.templatePresetDefault') },
  { value: 'byId', label: t('settings.templatePresetById') },
  { value: 'byArtist', label: t('settings.templatePresetByArtist') },
  { value: 'flat', label: t('settings.templatePresetFlat') },
  { value: 'custom', label: t('settings.templatePresetCustom') },
]);

const placeholders = '{id} {tag} {artist} {character} {copyright} {index} {ext} {site}';

function saveCurrentAsDefault() {
  settings.defaultDir = props.currentDir;
  ElMessage.success(t('common.save'));
}
</script>

<template>
  <el-drawer v-model="model" :title="t('settings.title')" direction="rtl" size="420px">
    <el-tabs>
      <el-tab-pane :label="t('settings.tabGeneral')">
        <div class="group">
          <label>{{ t('settings.language') }}</label>
          <el-select v-model="settings.locale" style="width: 100%">
            <el-option
              v-for="l in LOCALES"
              :key="l.code"
              :label="l.label"
              :value="l.code as Locale"
            />
          </el-select>
        </div>
        <div class="group">
          <label>{{ t('settings.themeColor') }}</label>
          <div class="theme-grid">
            <button
              v-for="opt in themeOptions"
              :key="opt.key"
              class="theme-swatch"
              :class="{ active: settings.theme === opt.key }"
              :style="{ '--sw': opt.color }"
              :title="opt.label"
              @click="settings.theme = opt.key"
            >
              <span class="sw-dot" />
              <span class="sw-label">{{ opt.label }}</span>
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
          <label>{{ t('settings.filenameTemplate') }}</label>
          <el-select v-model="settings.templatePreset" style="width: 100%">
            <el-option v-for="o in presetOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
          <div v-if="settings.templatePreset === 'custom'" class="sub">
            <el-input v-model="settings.templateCustom" type="textarea" :rows="2" />
            <p class="hint">{{ t('settings.templateHelp', { placeholders }) }}</p>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane :label="t('settings.tabFilter')">
        <div class="group">
          <label>{{ t('settings.rating') }}</label>
          <div class="check-row">
            <el-checkbox v-model="settings.rating.safe">{{ t('settings.ratingSafe') }}</el-checkbox>
            <el-checkbox v-model="settings.rating.questionable">{{ t('settings.ratingQuestionable') }}</el-checkbox>
            <el-checkbox v-model="settings.rating.explicit">{{ t('settings.ratingExplicit') }}</el-checkbox>
          </div>
          <p class="hint">{{ t('settings.ratingHint') }}</p>
        </div>
        <div class="group">
          <label>{{ t('settings.fileTypes') }}</label>
          <div class="check-col">
            <el-checkbox v-model="settings.fileTypes.image">{{ t('settings.fileTypeImage') }}</el-checkbox>
            <el-checkbox v-model="settings.fileTypes.animated">{{ t('settings.fileTypeAnimated') }}</el-checkbox>
            <el-checkbox v-model="settings.fileTypes.video">{{ t('settings.fileTypeVideo') }}</el-checkbox>
          </div>
          <p class="hint">{{ t('settings.fileTypesHint') }}</p>
        </div>
        <div class="group">
          <label>{{ t('settings.maxSize') }}</label>
          <el-input-number
            v-model="settings.maxSizeMb"
            :min="1"
            :max="9999"
            :step="10"
            controls-position="right"
            style="width: 100%"
          />
          <p class="hint">{{ t('settings.maxSizeHint') }} ({{ t('settings.maxSizeUnit') }})</p>
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
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.hint {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 6px;
  line-height: 1.5;
}
.hint.warn {
  color: var(--accent-warn);
}
.row {
  margin-top: 8px;
}
.sub {
  margin-top: 8px;
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
  cursor: pointer;
  transition:
    border-color 0.2s,
    transform 0.08s;
  font-size: 11px;
  color: var(--text);
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
.check-row {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}
.check-col {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.kbd-row {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text);
  padding: 4px 0;
}
.kbd-row span {
  margin-left: 10px;
  color: var(--text-muted);
}
kbd {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 1px 6px;
  font-family: 'Consolas', monospace;
  font-size: 11px;
  color: var(--text);
}
</style>
