<script setup lang="ts">
import { computed, ref } from 'vue';
import type { Site } from '@/types';
import { useTasks } from '@/useTasks';

const props = defineProps<{ currentLog: Site }>();
const emit = defineEmits<{ 'update:currentLog': [Site] }>();

const { state, retryFailedDownloads } = useTasks();
const showErrors = ref(true);
const showRuntime = ref(true);
const runtimeScrollRef = ref<HTMLElement | null>(null);
const errorScrollRef = ref<HTMLElement | null>(null);

function scrollToBottom(el: HTMLElement | null) {
  if (el) el.scrollTop = el.scrollHeight;
}

const activeState = computed(() => state[props.currentLog]);
const activeLogs = computed(() => activeState.value.logs);
const activeStatus = computed(() => activeState.value.status);
const activeQuery = computed(() => activeState.value.query);
const progress = computed(() => activeState.value.progress);
const failedItems = computed(() => activeState.value.failedItems);

const isActive = computed(() => ['running', 'paused', 'stopping'].includes(activeStatus.value));
const showRetry = computed(() => ['done', 'stopped', 'error'].includes(activeStatus.value) && failedItems.value.length > 0);
const progressPercent = computed(() => {
  if (!progress.value.total) return 0;
  return Math.round((progress.value.current / progress.value.total) * 100);
});
const latestLog = computed(() => activeLogs.value[activeLogs.value.length - 1]?.text || '');
const errorLogs = computed(() => activeLogs.value.filter((log) => log.level === 'error' || log.level === 'warn'));
const runtimeLogs = computed(() => activeLogs.value.filter((log) => log.level !== 'error' && log.level !== 'warn'));
const statusLabel = computed(() => {
  switch (activeStatus.value) {
    case 'running':
      return '运行中 / Running';
    case 'paused':
      return '已暂停 / Paused';
    case 'stopping':
      return '中止中 / Stopping';
    case 'done':
      return '已完成 / Done';
    case 'stopped':
      return '已中止 / Stopped';
    case 'error':
      return '出错 / Error';
    default:
      return '待命 / Idle';
  }
});

function switchLog(site: Site) {
  emit('update:currentLog', site);
}

function clearLog() {
  activeState.value.logs = [];
  activeState.value.logCount = 0;
}

function onRetry() {
  retryFailedDownloads(props.currentLog);
}
</script>

<template>
  <section class="log-panel">
    <div class="log-header">
      <div class="tabs">
        <button
          v-for="site in (['danbooru', 'yande'] as Site[])"
          :key="site"
          class="tab-btn"
          :class="{ active: currentLog === site }"
          @click="switchLog(site)"
        >
          {{ site === 'danbooru' ? 'Danbooru' : 'Yande.re' }}
        </button>
      </div>
      <div class="header-actions">
        <span class="status-pill" :class="`status-${activeStatus}`">{{ statusLabel }}</span>
        <button v-if="showRetry" class="tool-btn warn" @click="onRetry">
          Retry {{ failedItems.length }}
        </button>
        <button class="tool-btn" @click="clearLog">Clear</button>
      </div>
    </div>

    <div class="log-body">
      <div class="summary-card">
        <div class="summary-row">
          <span class="summary-label">当前搜索词 / Query</span>
          <span class="summary-value">{{ activeQuery || '-' }}</span>
        </div>
        <div class="summary-row">
          <span class="summary-label">最近状态 / Latest</span>
          <span class="summary-value">{{ latestLog || '暂无日志 / No logs yet' }}</span>
        </div>
      </div>

      <div v-if="isActive || showRetry" class="progress-section">
        <div class="progress-top">
          <span>下载进度 / Progress</span>
          <span>{{ progress.current }} / {{ progress.total }}</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: `${progressPercent}%` }" />
        </div>
        <div v-if="isActive && progress.total === 0" class="prepare-hint">
          正在准备任务，请稍候。你会在下面看到运行日志，例如正在获取页数、整理下载队列、统计图片数量。
        </div>
      </div>

      <div class="log-section">
        <div class="section-header">
          <button class="section-toggle" @click="showRuntime = !showRuntime">
            {{ showRuntime ? 'Hide' : 'Show' }} 运行日志 / Runtime Log
          </button>
          <button v-if="showRuntime && runtimeLogs.length > 0" class="scroll-btn" @click="scrollToBottom(runtimeScrollRef)">Scroll to bottom</button>
        </div>
        <div v-if="runtimeLogs.length === 0 && !isActive" class="empty-box">
          这里会显示下载前准备、抓取页数、统计数量、开始下载等实时过程。
        </div>
        <div v-else-if="showRuntime" ref="runtimeScrollRef" class="log-list runtime-scroll">
          <div
            v-for="line in runtimeLogs"
            :key="line.id"
            class="log-line"
            :class="`log-${line.level}`"
          >
            {{ line.text }}
          </div>
        </div>
      </div>

      <div v-if="errorLogs.length > 0" class="log-section error-section">
        <div class="section-header">
          <button class="section-toggle" @click="showErrors = !showErrors">
            {{ showErrors ? 'Hide' : 'Show' }} Warnings / Errors ({{ errorLogs.length }})
          </button>
          <button v-if="showErrors" class="scroll-btn" @click="scrollToBottom(errorScrollRef)">Scroll to bottom</button>
        </div>
        <div v-if="showErrors" ref="errorScrollRef" class="log-list error-scroll">
          <div
            v-for="line in errorLogs"
            :key="line.id"
            class="log-line"
            :class="`log-${line.level}`"
          >
            {{ line.text }}
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.log-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.03), transparent 22%),
    var(--bg);
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  background: rgba(19, 26, 38, 0.76);
}

.tabs {
  display: flex;
  gap: 8px;
}

.tab-btn {
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-muted);
  border-radius: 12px;
  padding: 8px 14px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
  transition:
    background 0.18s,
    border-color 0.18s,
    color 0.18s;
}

.tab-btn.active {
  color: var(--text);
  border-color: color-mix(in srgb, var(--accent) 48%, var(--border));
  background: color-mix(in srgb, var(--accent) 14%, transparent);
}

.tab-btn:hover {
  color: var(--text);
  border-color: var(--border-strong);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-pill {
  border-radius: 12px;
  padding: 7px 10px;
  font-size: 12px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-muted);
  border: 1px solid var(--border);
  font-weight: 800;
}

.status-running {
  color: var(--accent-ok);
  border-color: color-mix(in srgb, var(--accent-ok) 34%, var(--border));
  background: color-mix(in srgb, var(--accent-ok) 12%, transparent);
}

.status-paused {
  color: var(--accent-pause);
  border-color: color-mix(in srgb, var(--accent-pause) 34%, var(--border));
  background: color-mix(in srgb, var(--accent-pause) 12%, transparent);
}

.status-stopping {
  color: var(--accent-warn);
  border-color: color-mix(in srgb, var(--accent-warn) 34%, var(--border));
  background: color-mix(in srgb, var(--accent-warn) 12%, transparent);
}

.status-error {
  color: var(--accent-err);
  border-color: color-mix(in srgb, var(--accent-err) 34%, var(--border));
  background: color-mix(in srgb, var(--accent-err) 12%, transparent);
}

.tool-btn {
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-muted);
  border-radius: 8px;
  padding: 7px 10px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  transition:
    color 0.18s,
    border-color 0.18s,
    background 0.18s;
}

.tool-btn.warn {
  color: var(--accent-warn);
}

.tool-btn:hover {
  color: var(--text);
  border-color: var(--border-strong);
  background: rgba(255, 255, 255, 0.07);
}

.log-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
}

.summary-card,
.progress-section,
.log-section {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.045), transparent 70%),
    var(--panel);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 14px;
  margin-bottom: 12px;
}

.summary-row {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
}

.summary-row:last-child {
  margin-bottom: 0;
}

.summary-label {
  flex: 0 0 150px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 800;
}

.summary-value {
  color: var(--text);
  font-size: 12px;
  word-break: break-all;
}

.progress-top {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.progress-bar {
  height: 10px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 999px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.045);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), var(--accent-light));
  transition: width 0.25s ease;
  box-shadow: 0 0 18px color-mix(in srgb, var(--accent) 55%, transparent);
}

.prepare-hint {
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.6;
}

.section-title,
.section-toggle {
  font-size: 12px;
  font-weight: 800;
  color: var(--text);
  margin-bottom: 10px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.section-toggle {
  width: auto;
  text-align: left;
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
  margin-bottom: 0;
}

.scroll-btn {
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-muted);
  border-radius: 8px;
  padding: 5px 8px;
  cursor: pointer;
  font-size: 11px;
  transition: background 0.18s, color 0.18s;
}

.scroll-btn:hover {
  background: var(--accent);
  color: #fff;
}

.empty-box {
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.6;
  padding: 10px;
  border: 1px dashed var(--border);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.025);
}

.log-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.runtime-scroll {
  max-height: 320px;
  overflow-y: auto;
  padding-right: 6px;
}

.error-scroll {
  max-height: 180px;
  overflow-y: auto;
  padding-right: 6px;
}

.runtime-scroll::-webkit-scrollbar,
.error-scroll::-webkit-scrollbar {
  width: 8px;
}

.runtime-scroll::-webkit-scrollbar-thumb,
.error-scroll::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 999px;
}

.runtime-scroll::-webkit-scrollbar-thumb:hover,
.error-scroll::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}

.log-line {
  font-family: "Cascadia Mono", Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.55;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-word;
  padding: 7px 9px;
  border: 1px solid rgba(151, 172, 209, 0.08);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.025);
}

.log-sys {
  color: var(--accent);
  border-color: color-mix(in srgb, var(--accent) 20%, transparent);
}

.log-debug {
  color: var(--text-muted);
}

.log-warn {
  color: var(--accent-warn);
  border-color: color-mix(in srgb, var(--accent-warn) 20%, transparent);
}

.log-error {
  color: var(--accent-err);
  border-color: color-mix(in srgb, var(--accent-err) 24%, transparent);
  background: color-mix(in srgb, var(--accent-err) 7%, transparent);
}

.error-section {
  border-color: rgba(245, 108, 108, 0.35);
}

@media (max-width: 760px) {
  .log-header {
    align-items: stretch;
    flex-direction: column;
  }

  .header-actions {
    flex-wrap: wrap;
  }

  .summary-row {
    flex-direction: column;
    gap: 4px;
  }

  .summary-label {
    flex: none;
  }
}
</style>
