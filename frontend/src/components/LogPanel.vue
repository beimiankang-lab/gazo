<script setup lang="ts">
import { computed, nextTick, onUpdated, ref, watch } from 'vue';
import type { Site } from '@/types';
import { useTasks } from '@/useTasks';

const props = defineProps<{ currentLog: Site }>();
const emit = defineEmits<{ 'update:currentLog': [Site] }>();

const { state } = useTasks();

const logView = ref<HTMLDivElement | null>(null);

const activeLogs = computed(() => state[props.currentLog].logs);
const activeStatus = computed(() => state[props.currentLog].status);

const statusText = computed(() => {
  switch (activeStatus.value) {
    case 'running':
      return '运行中';
    case 'paused':
      return '已暂停';
    case 'stopping':
      return '中止中...';
    case 'done':
      return '已完成';
    case 'stopped':
      return '已中止';
    case 'error':
      return '错误';
    default:
      return '就绪';
  }
});

const statusClass = computed(() => `status-${activeStatus.value}`);

function clearLog() {
  state[props.currentLog].logs = [];
  state[props.currentLog].logCount = 0;
}

function scrollToBottom() {
  const el = logView.value;
  if (el) el.scrollTop = el.scrollHeight;
}

onUpdated(() => {
  const el = logView.value;
  if (!el) return;
  if (el.scrollHeight - el.scrollTop - el.clientHeight < 160) {
    el.scrollTop = el.scrollHeight;
  }
});

watch(
  () => props.currentLog,
  () => nextTick(scrollToBottom),
);

function switchLog(site: Site) {
  emit('update:currentLog', site);
}

const emptyHint = computed(() =>
  props.currentLog === 'danbooru'
    ? '启动 Danbooru 任务后日志将在此显示'
    : '启动 Yande.re 任务后日志将在此显示',
);
</script>

<template>
  <section class="log-panel">
    <div class="log-header">
      <div class="log-tabs">
        <button
          v-for="site in (['danbooru', 'yande'] as Site[])"
          :key="site"
          class="log-tab"
          :class="[
            `site-${site}`,
            {
              active: currentLog === site,
              'has-task': ['running', 'paused', 'stopping'].includes(state[site].status),
              'task-paused': state[site].status === 'paused',
            },
          ]"
          @click="switchLog(site)"
        >
          {{ site === 'danbooru' ? 'Danbooru' : 'Yande.re' }} 日志
          <span class="tab-badge" />
        </button>
      </div>
      <div class="status-bar">
        <span class="status" :class="statusClass">
          <span class="status-dot" />
          {{ statusText }}
        </span>
        <button class="icon-btn" title="清空当前日志" @click="clearLog">🗑</button>
        <button class="icon-btn" title="滚动到底部" @click="scrollToBottom">⬇</button>
      </div>
    </div>
    <div ref="logView" class="log-view">
      <div v-if="activeLogs.length === 0" class="log-empty">
        <span class="icon">📋</span>
        <span>{{ emptyHint }}</span>
      </div>
      <span
        v-for="line in activeLogs"
        :key="line.id"
        class="log-line"
        :class="`log-${line.level}`"
      >{{ line.text }}</span>
    </div>
  </section>
</template>

<style scoped>
.log-panel {
  display: flex;
  flex-direction: column;
  background: var(--bg);
  overflow: hidden;
}
.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 12px 0 0;
  background: var(--panel);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.log-tabs {
  display: flex;
}
.log-tab {
  padding: 13px 24px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  transition:
    color 0.2s,
    background 0.2s;
  position: relative;
}
.log-tab:hover {
  color: var(--text);
  background: rgba(255, 255, 255, 0.03);
}
.log-tab.active.site-danbooru {
  color: var(--accent-d);
  border-color: var(--accent-d);
}
.log-tab.active.site-yande {
  color: var(--accent-y);
  border-color: var(--accent-y);
}
.tab-badge {
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
.log-tab.has-task .tab-badge {
  display: block;
}
.log-tab.task-paused .tab-badge {
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
.status-bar {
  display: flex;
  align-items: center;
  gap: 10px;
}
.status {
  font-size: 12px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 6px;
}
.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-muted);
}
.status.status-running .status-dot {
  background: var(--accent-ok);
  box-shadow: 0 0 5px var(--accent-ok);
  animation: pulse 1.2s infinite;
}
.status.status-paused .status-dot {
  background: var(--accent-pause);
}
.status.status-stopping .status-dot {
  background: var(--accent-warn);
  animation: pulse 0.8s infinite;
}
.status.status-done .status-dot {
  background: var(--accent-ok);
}
.status.status-stopped .status-dot {
  background: var(--text-muted);
}
.status.status-error .status-dot {
  background: var(--accent-err);
}
.icon-btn {
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-muted);
  padding: 4px 8px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 13px;
  transition:
    color 0.2s,
    border-color 0.2s;
}
.icon-btn:hover {
  color: var(--text);
  border-color: var(--border);
}
.log-view {
  flex: 1;
  padding: 14px 18px;
  font-family: 'Consolas', 'Menlo', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.55;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  background: var(--bg);
}
.log-empty {
  color: var(--text-muted);
  text-align: center;
  padding: 40px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.log-empty .icon {
  font-size: 28px;
  opacity: 0.4;
}
.log-line {
  display: block;
  color: var(--text);
}
.log-line.log-info {
  color: #c8d1e0;
}
.log-line.log-debug {
  color: var(--text-muted);
  opacity: 0.8;
}
.log-line.log-warn {
  color: var(--accent-warn);
}
.log-line.log-error {
  color: var(--accent-err);
}
.log-line.log-sys {
  color: var(--accent-d);
  font-weight: 600;
}
</style>