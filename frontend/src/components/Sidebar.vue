<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import type { Site } from '@/types';
import { useTasks } from '@/useTasks';
import SiteForm from './SiteForm.vue';
import RecordsList from './RecordsList.vue';

const props = defineProps<{
  currentSite: Site;
  defaultDir: string;
}>();

const emit = defineEmits<{ 'switch-site': [Site] }>();

const { state, start, togglePause, requestStop } = useTasks();

const dDir = ref(props.defaultDir);
const yDir = ref(props.defaultDir);

watch(
  () => props.defaultDir,
  (val) => {
    if (!dDir.value) dDir.value = val;
    if (!yDir.value) yDir.value = val;
  },
);

const activeForm = computed({
  get: () => props.currentSite,
  set: (value: Site) => emit('switch-site', value),
});

function isActive(site: Site) {
  const s = state[site].status;
  return s === 'running' || s === 'paused' || s === 'stopping';
}

async function handleStart(site: Site, payload: { query: string; outputDir: string; includeDeleted: boolean }) {
  if (!payload.query) {
    ElMessage.warning('请填写搜索词');
    return;
  }
  try {
    await start(site, payload.query, payload.outputDir, payload.includeDeleted);
    recordsRef.value?.refresh();
  } catch (e) {
    ElMessage.error(`启动失败: ${(e as Error).message}`);
  }
}

async function handleStop(site: Site) {
  const name = site === 'danbooru' ? 'Danbooru' : 'Yande.re';
  try {
    await ElMessageBox.confirm(
      `确定要中止当前 ${name} 任务吗？已下载的图片会保留，未完成的图片将停止下载。`,
      '中止任务',
      {
        confirmButtonText: '中止',
        cancelButtonText: '取消',
        type: 'warning',
      },
    );
  } catch {
    return;
  }
  requestStop(site);
}

const recordsRef = ref<InstanceType<typeof RecordsList> | null>(null);

watch(
  () => state.danbooru.status,
  (s) => {
    if (s === 'done' || s === 'stopped' || s === 'error') recordsRef.value?.refresh();
  },
);
watch(
  () => state.yande.status,
  (s) => {
    if (s === 'done' || s === 'stopped' || s === 'error') recordsRef.value?.refresh();
  },
);
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
        <span>{{ site === 'danbooru' ? 'Danbooru' : 'Yande.re' }}</span>
        <span class="running-badge" />
      </button>
    </div>

    <SiteForm
      v-show="activeForm === 'danbooru'"
      site="danbooru"
      v-model:output-dir="dDir"
      :state="state.danbooru"
      @start="(p) => handleStart('danbooru', p)"
      @toggle-pause="togglePause('danbooru')"
      @stop="handleStop('danbooru')"
    />
    <SiteForm
      v-show="activeForm === 'yande'"
      site="yande"
      v-model:output-dir="yDir"
      :state="state.yande"
      @start="(p) => handleStart('yande', p)"
      @toggle-pause="togglePause('yande')"
      @stop="handleStop('yande')"
    />

    <div class="divider" />

    <RecordsList ref="recordsRef" :output-dir="dDir || yDir" />
  </aside>
</template>

<style scoped>
.sidebar {
  background: var(--panel);
  border-right: 1px solid var(--border);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.site-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.site-tab {
  padding: 14px 0;
  text-align: center;
  cursor: pointer;
  font-weight: 600;
  font-size: 13px;
  color: var(--text-muted);
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  user-select: none;
  transition:
    color 0.2s,
    background 0.2s;
  position: relative;
}
.site-tab:hover {
  color: var(--text);
  background: rgba(255, 255, 255, 0.03);
}
.site-tab.active.site-danbooru {
  color: var(--accent-d);
  border-color: var(--accent-d);
  background: rgba(124, 106, 255, 0.06);
}
.site-tab.active.site-yande {
  color: var(--accent-y);
  border-color: var(--accent-y);
  background: rgba(255, 107, 138, 0.06);
}
.dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}
.site-danbooru .dot {
  background: var(--accent-d);
}
.site-yande .dot {
  background: var(--accent-y);
}
.running-badge {
  display: none;
  position: absolute;
  top: 6px;
  right: 10px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent-ok);
  box-shadow: 0 0 5px var(--accent-ok);
  animation: pulse 1.2s infinite;
}
.site-tab.has-task .running-badge {
  display: block;
}
.site-tab.task-paused .running-badge {
  background: var(--accent-pause);
  box-shadow: 0 0 5px var(--accent-pause);
  animation: none;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.4;
    transform: scale(1.3);
  }
}
.divider {
  height: 1px;
  background: var(--border);
  margin: 4px 0;
}
</style>