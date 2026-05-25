<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage, ElMessageBox } from 'element-plus';
import type { Site } from '@/types';
import { useTasks } from '@/useTasks';
import { buildRatingFragment, buildTagListFragment, getSiteSettings, getRatingPicks } from '@/useSettings';
import SiteForm from './SiteForm.vue';

const props = defineProps<{
  currentSite: Site;
}>();

const emit = defineEmits<{
  'switch-site': [Site];
}>();

const { t } = useI18n();
const { state, start, togglePause, requestStop } = useTasks();

const dFormRef = ref<InstanceType<typeof SiteForm> | null>(null);
const yFormRef = ref<InstanceType<typeof SiteForm> | null>(null);

defineExpose({
  triggerStart() {
    if (props.currentSite === 'danbooru') dFormRef.value?.triggerStart();
    else yFormRef.value?.triggerStart();
  },
  async triggerStop() {
    await handleStop(props.currentSite);
  },
  currentOutputDir() {
    return getSiteSettings(props.currentSite).outputDir;
  },
});

const activeForm = computed({
  get: () => props.currentSite,
  set: (value: Site) => emit('switch-site', value),
});

function isActive(site: Site) {
  const status = state[site].status;
  return status === 'running' || status === 'paused' || status === 'stopping';
}

function composeQuery(site: Site, userQuery: string): string {
  const rating = buildRatingFragment(site);
  const tagList = buildTagListFragment(site);
  const parts = [userQuery, rating, tagList].filter((text) => text && text.trim());
  return parts.join(' ').trim();
}

async function handleStart(
  site: Site,
  payload: { query: string; includeDeleted: boolean; maxPosts: number | null },
) {
  if (!payload.query) {
    ElMessage.warning(t('form.emptyTags'));
    return;
  }
  const finalQuery = composeQuery(site, payload.query);
  try {
    const outputDir = getSiteSettings(site).outputDir || '';
    const ratings = site === 'yande' ? getRatingPicks(site) : undefined;
    await start(site, finalQuery, payload.query, outputDir, payload.includeDeleted, payload.maxPosts, ratings);
  } catch (e) {
    ElMessage.error(t('form.startFailed', { msg: (e as Error).message }));
  }
}

async function handleStop(site: Site) {
  const name = site === 'danbooru' ? 'Danbooru' : 'Yande.re';
  try {
    await ElMessageBox.confirm(t('stop.confirm', { site: name }), t('stop.title'), {
      confirmButtonText: t('stop.button'),
      cancelButtonText: t('common.cancel'),
      type: 'warning',
    });
  } catch {
    return;
  }
  requestStop(site);
}
</script>

<template>
  <aside class="sidebar">
    <div class="site-tabs">
      <button
        v-for="site in (['danbooru', 'yande'] as Site[])"
        :key="site"
        class="site-tab"
        :class="[
          `site-${site}`,
          { active: currentSite === site, 'has-task': isActive(site), 'task-paused': state[site].status === 'paused' },
        ]"
        @click="emit('switch-site', site)"
      >
        <span class="dot" />
        <span>{{ t(`site.${site}`) }}</span>
        <span class="running-badge" />
      </button>
    </div>

    <div class="forms-scroll">
      <SiteForm
        v-show="activeForm === 'danbooru'"
        ref="dFormRef"
        site="danbooru"
        :state="state.danbooru"
        @start="(payload) => handleStart('danbooru', payload)"
        @toggle-pause="togglePause('danbooru')"
        @stop="handleStop('danbooru')"
      />
      <SiteForm
        v-show="activeForm === 'yande'"
        ref="yFormRef"
        site="yande"
        :state="state.yande"
        @start="(payload) => handleStart('yande', payload)"
        @toggle-pause="togglePause('yande')"
        @stop="handleStop('yande')"
      />
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: linear-gradient(180deg, color-mix(in srgb, var(--panel) 90%, #fff 10%), var(--panel));
  border-right: 1px solid var(--border);
}

.site-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.site-tab {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 15px 10px;
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition:
    color 0.2s,
    background 0.2s,
    border-color 0.2s;
}

.site-tab:hover {
  color: var(--text);
  background: rgba(255, 255, 255, 0.03);
}

.site-tab.active.site-danbooru {
  color: var(--accent-d);
  border-color: var(--accent-d);
  background: rgba(124, 106, 255, 0.08);
}

.site-tab.active.site-yande {
  color: var(--accent-y);
  border-color: var(--accent-y);
  background: rgba(255, 107, 138, 0.08);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  flex-shrink: 0;
}

.site-danbooru .dot {
  background: var(--accent-d);
}

.site-yande .dot {
  background: var(--accent-y);
}

.running-badge {
  position: absolute;
  top: 9px;
  right: 14px;
  width: 8px;
  height: 8px;
  border-radius: 999px;
  opacity: 0;
  transform: scale(0.7);
  transition:
    opacity 0.18s,
    transform 0.18s;
}

.site-danbooru.has-task .running-badge {
  opacity: 1;
  transform: scale(1);
  background: var(--accent-d);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent-d) 18%, transparent);
}

.site-yande.has-task .running-badge {
  opacity: 1;
  transform: scale(1);
  background: var(--accent-y);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent-y) 18%, transparent);
}

.task-paused .running-badge {
  animation: pulse 1.2s infinite alternate;
}

.forms-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

@keyframes pulse {
  from {
    opacity: 0.35;
  }
  to {
    opacity: 1;
  }
}
</style>
