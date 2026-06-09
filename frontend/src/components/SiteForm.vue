<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { getSiteSettings } from '@/useSettings';
import type { Site, TaskStatus } from '@/types';

interface SiteStateShape {
  taskId: string | null;
  status: TaskStatus;
  query?: string;
}

const props = defineProps<{
  site: Site;
  state: SiteStateShape;
}>();

const emit = defineEmits<{
  start: [{ query: string; includeDeleted: boolean; maxPosts: number | null }];
  'toggle-pause': [];
  stop: [];
}>();

const { t } = useI18n();
const form = getSiteSettings(props.site);
const showRatingHint = ref(false);
const showTagRules = ref(form.whitelist.length > 0 || form.blacklist.length > 0);

defineExpose({ triggerStart: () => onStart() });

const isRunning = computed(() => props.state.status === 'running');
const isPaused = computed(() => props.state.status === 'paused');
const isStopping = computed(() => props.state.status === 'stopping');
const isActive = computed(() => isRunning.value || isPaused.value || isStopping.value);

const displayQuery = computed(() =>
  isActive.value && props.state.query ? props.state.query : form.query,
);

const placeholder = computed(() =>
  props.site === 'danbooru' ? t('form.tagsPlaceholderD') : t('form.tagsPlaceholderY'),
);

const primaryClass = computed(() =>
  props.site === 'danbooru' ? 'btn-primary-d' : 'btn-primary-y',
);

const tagSummary = computed(() =>
  t('form.tagRuleSummary', {
    wl: form.whitelist.length,
    bl: form.blacklist.length,
  }),
);

watch(
  () => [form.whitelist.length, form.blacklist.length],
  ([wl, bl]) => {
    if (wl > 0 || bl > 0) showTagRules.value = true;
  },
);

watch(
  () => form.whitelist.length,
  (len) => {
    if (len === 0) form.includeNoAuthor = false;
  },
);

function onQueryInput(value: string | number | undefined) {
  if (!isActive.value) form.query = String(value ?? '');
}

function onStart() {
  emit('start', {
    query: form.query.trim(),
    includeDeleted: props.site === 'danbooru' && form.includeDeleted,
    maxPosts: form.limitEnabled && form.maxPosts > 0 ? form.maxPosts : null,
  });
}
</script>

<template>
  <div class="form-shell">
    <div class="form-body">
      <section class="panel-section hero-section">
        <div class="section-head">
          <div>
            <p class="eyebrow">{{ t(`site.${site}`) }}</p>
            <h2 class="section-title">{{ t('form.tags') }}</h2>
          </div>
        </div>
        <el-input
          :model-value="displayQuery"
          :placeholder="placeholder"
          :clearable="!isActive"
          :disabled="isActive"
          size="large"
          @update:model-value="onQueryInput"
          @keyup.ctrl.enter="onStart"
        />
        <p class="section-note">{{ isActive ? t('form.queryLocked') : t('form.queryHint') }}</p>
        <template v-if="!isActive">
          <button class="btn start-btn" :class="primaryClass" @click="onStart">
            {{ t('form.startDownload') }}
          </button>
        </template>
        <div v-else class="control-row">
          <button
            v-if="isRunning || isPaused"
            class="btn btn-pause"
            :title="isPaused ? t('common.resume') : t('common.pause')"
            @click="emit('toggle-pause')"
          >
            {{ isPaused ? t('common.resume') : t('common.pause') }}
          </button>
          <button
            class="btn btn-stop"
            :disabled="isStopping"
            :title="isStopping ? t('form.stoppingEllipsis') : t('common.stop')"
            @click="emit('stop')"
          >
            {{ t('common.stop') }}
          </button>
        </div>
      </section>

      <section v-if="site === 'danbooru'" class="panel-section compact">
        <div class="switch-row">
          <div>
            <h3 class="section-title small">{{ t('form.includeDeleted') }}</h3>
            <p class="section-note">{{ t('form.includeDeletedHint') }}</p>
          </div>
          <el-switch v-model="form.includeDeleted" :disabled="isActive" />
        </div>
      </section>

      <section class="panel-section">
        <div class="section-head">
          <div>
            <p class="eyebrow">{{ t('form.filterTitle') }}</p>
            <h3 class="section-title small">{{ t('form.filterTitle') }}</h3>
          </div>
        </div>

        <div class="sub-section">
          <div class="sub-head">
            <label class="sub-title">{{ t('form.rating') }}</label>
            <button
              type="button"
              class="help-chip"
              :title="t('form.ratingHelp')"
              @click="showRatingHint = !showRatingHint"
            >
              ?
            </button>
          </div>
          <div class="checkbox-grid">
            <label class="check-card" v-if="props.site === 'danbooru'">
              <el-checkbox v-model="form.rating.general" :disabled="isActive" />
              <span>{{ t('form.ratingGeneral') }}</span>
            </label>
            <label class="check-card">
              <el-checkbox v-model="form.rating.safe" :disabled="isActive" />
              <span>{{ t('form.ratingSafe') }}</span>
            </label>
            <label class="check-card">
              <el-checkbox v-model="form.rating.questionable" :disabled="isActive" />
              <span>{{ t('form.ratingQuestionable') }}</span>
            </label>
            <label class="check-card">
              <el-checkbox v-model="form.rating.explicit" :disabled="isActive" />
              <span>{{ t('form.ratingExplicit') }}</span>
            </label>
          </div>
          <p v-if="showRatingHint" class="section-note">{{ t('form.ratingHint') }}</p>
        </div>

        <div class="sub-section">
          <label class="sub-title">{{ t('form.fileTypes') }}</label>
          <div class="checkbox-grid tight">
            <label class="check-card">
              <el-checkbox v-model="form.fileTypes.image" :disabled="isActive" />
              <span>{{ t('settings.fileTypeImage') }}</span>
            </label>
            <label class="check-card">
              <el-checkbox v-model="form.fileTypes.animated" :disabled="isActive" />
              <span>{{ t('settings.fileTypeAnimated') }}</span>
            </label>
            <label class="check-card">
              <el-checkbox v-model="form.fileTypes.video" :disabled="isActive" />
              <span>{{ t('settings.fileTypeVideo') }}</span>
            </label>
          </div>
          <p class="section-note">{{ t('form.fileTypesHint') }}</p>
        </div>

        <div class="sub-section">
          <label class="sub-title">{{ t('form.maxSize') }}</label>
          <div class="size-row">
            <el-input-number
              v-model="form.maxSizeMb"
              :min="1"
              :max="9999"
              :step="10"
              :disabled="isActive"
              controls-position="right"
              style="width: 100%"
            />
            <span class="size-unit">MB</span>
          </div>
          <p class="section-note">{{ t('form.maxSizeHint') }}</p>
        </div>
      </section>

      <section class="panel-section">
        <div class="section-head">
          <div>
            <p class="eyebrow">{{ t('form.tagRulesTitle') }}</p>
            <h3 class="section-title small">{{ t('form.tagRulesTitle') }}</h3>
          </div>
          <el-switch
            v-model="showTagRules"
            :disabled="isActive"
            @change="(value) => { if (!value) { form.whitelist = []; form.blacklist = []; } }"
          />
        </div>
        <div class="tag-count">{{ tagSummary }}</div>

        <template v-if="showTagRules">
          <div class="tag-card">
            <label class="sub-title">{{ t('form.whitelist') }}</label>
            <el-select
              v-model="form.whitelist"
              multiple
              filterable
              allow-create
              default-first-option
              :reserve-keyword="false"
              :disabled="isActive"
              :placeholder="t('form.whitelistPlaceholder')"
              style="width: 100%"
            />
            <p class="section-note">{{ t('form.whitelistHint') }}</p>

            <div class="whitelist-options">
              <label class="sub-title">{{ t('form.whitelistMode') }}</label>
              <el-radio-group v-model="form.whitelistMode" :disabled="isActive" size="small">
                <el-radio-button value="and">{{ t('form.whitelistModeAnd') }}</el-radio-button>
                <el-radio-button value="or">{{ t('form.whitelistModeOr') }}</el-radio-button>
              </el-radio-group>
              <p class="section-note">{{ t('form.whitelistModeHint') }}</p>
            </div>

            <div class="switch-row" style="margin-top: 4px;">
              <div>
                <label class="sub-title">{{ t('form.includeNoAuthor') }}</label>
                <p class="section-note">{{ t('form.includeNoAuthorHint') }}</p>
              </div>
              <el-switch v-model="form.includeNoAuthor" :disabled="isActive || form.whitelist.length === 0" />
            </div>
          </div>

          <div class="tag-card">
            <label class="sub-title">{{ t('form.blacklist') }}</label>
            <el-select
              v-model="form.blacklist"
              multiple
              filterable
              allow-create
              default-first-option
              :reserve-keyword="false"
              :disabled="isActive"
              :placeholder="t('form.blacklistPlaceholder')"
              style="width: 100%"
            />
            <p class="section-note">{{ t('form.blacklistHint') }}</p>
          </div>
        </template>
      </section>

      <section class="panel-section">
        <div class="switch-row">
          <div>
            <h3 class="section-title small">{{ t('form.autoRetry') }}</h3>
            <p class="section-note">{{ t('form.autoRetryHint') }}</p>
          </div>
          <el-switch v-model="form.autoRetry" :disabled="isActive" />
        </div>
      </section>

      <section class="panel-section">
        <label class="sub-title">{{ t('form.dedupMode') }}</label>
        <el-radio-group v-model="form.dedupMode" :disabled="isActive" size="small">
          <el-radio-button value="none">{{ t('form.dedupModeNone') }}</el-radio-button>
          <el-radio-button value="local">{{ t('form.dedupModeLocal') }}</el-radio-button>
          <el-radio-button value="global">{{ t('form.dedupModeGlobal') }}</el-radio-button>
        </el-radio-group>
        <p class="section-note">{{ t('form.dedupModeHint') }}</p>
      </section>

      <section class="panel-section">
        <div class="switch-row">
          <div>
            <h3 class="section-title small">{{ t('form.limitPosts') }}</h3>
            <p class="section-note">{{ t('form.limitPostsHint') }}</p>
          </div>
          <el-switch v-model="form.limitEnabled" :disabled="isActive" />
        </div>
        <el-input-number
          v-if="form.limitEnabled"
          v-model="form.maxPosts"
          :min="1"
          :max="999999"
          :step="100"
          :disabled="isActive"
          controls-position="right"
          style="width: 100%"
        />
      </section>
    </div>
  </div>
</template>

<style scoped>
.form-shell {
  height: 100%;
  min-height: 0;
}

.form-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 100%;
  padding: 14px;
}

.panel-section {
  display: flex;
  flex-direction: column;
  gap: 11px;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 16px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.045), transparent 70%),
    var(--card);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.12);
}

.panel-section.compact {
  gap: 10px;
}

.hero-section {
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--accent) 24%, transparent), transparent 56%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.08), transparent 64%),
    var(--card-strong);
  border-color: color-mix(in srgb, var(--accent) 34%, var(--border));
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.eyebrow {
  margin: 0 0 4px;
  font-size: 11px;
  letter-spacing: 0;
  text-transform: uppercase;
  color: var(--text-muted);
  font-weight: 800;
}

.section-title {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: 0;
}

.section-title.small {
  font-size: 14px;
}

.section-note {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--text-muted);
  white-space: pre-line;
}

.start-btn {
  width: 100%;
  justify-content: center;
}

.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.sub-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sub-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.sub-title {
  font-size: 12px;
  font-weight: 800;
  color: var(--text);
}

.help-chip {
  width: 26px;
  height: 26px;
  border: 1px solid var(--border);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-muted);
  cursor: pointer;
}

.checkbox-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 10px;
}

.checkbox-grid.tight {
  grid-template-columns: 1fr;
}

.check-card {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  color: var(--text);
  font-size: 12px;
  transition:
    border-color 0.18s,
    background 0.18s;
}

.check-card:hover {
  border-color: var(--border-strong);
  background: rgba(255, 255, 255, 0.055);
}

.size-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.size-unit {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
}

.tag-count {
  flex-shrink: 0;
  padding: 6px 10px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.055);
  border: 1px solid var(--border);
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
}

.tag-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.02);
}

.whitelist-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 4px;
}

.control-row {
  display: flex;
  gap: 10px;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 42px;
  padding: 11px 16px;
  border: 1px solid transparent;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  transition:
    transform 0.12s,
    filter 0.18s,
    opacity 0.18s,
    box-shadow 0.18s;
}

.btn:hover:not(:disabled) {
  filter: brightness(1.05);
  transform: translateY(-1px);
}

.btn:active:not(:disabled) {
  transform: scale(0.985);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary-d {
  background: linear-gradient(135deg, var(--accent-d), color-mix(in srgb, var(--accent-d) 72%, #fff 28%));
  color: #fff;
  box-shadow: 0 14px 28px color-mix(in srgb, var(--accent-d) 24%, transparent);
}

.btn-primary-y {
  background: linear-gradient(135deg, var(--accent-y), color-mix(in srgb, var(--accent-y) 68%, #fff 32%));
  color: #fff;
  box-shadow: 0 14px 28px color-mix(in srgb, var(--accent-y) 24%, transparent);
}

.btn-pause {
  flex: 1;
  background: rgba(255, 255, 255, 0.055);
  border-color: var(--border);
  color: var(--text);
}

.btn-stop {
  flex: 1;
  background: rgba(245, 108, 108, 0.12);
  border-color: rgba(245, 108, 108, 0.35);
  color: #ffb4b4;
}

@media (max-width: 960px) {
  .checkbox-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 680px) {
  .form-body {
    padding: 12px;
  }

  .panel-section {
    border-radius: 14px;
  }
}
</style>
