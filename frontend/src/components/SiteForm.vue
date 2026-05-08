<script setup lang="ts">
import { computed, ref } from 'vue';
import type { Site, TaskStatus } from '@/types';

interface SiteStateShape {
  taskId: string | null;
  status: TaskStatus;
}

const props = defineProps<{
  site: Site;
  outputDir: string;
  state: SiteStateShape;
}>();

const emit = defineEmits<{
  'update:outputDir': [string];
  start: [{ query: string; outputDir: string; includeDeleted: boolean }];
  'toggle-pause': [];
  stop: [];
}>();

const query = ref('');
const includeDeleted = ref(false);

const dir = computed({
  get: () => props.outputDir,
  set: (v: string) => emit('update:outputDir', v),
});

const isRunning = computed(() => props.state.status === 'running');
const isPaused = computed(() => props.state.status === 'paused');
const isStopping = computed(() => props.state.status === 'stopping');
const isActive = computed(() => isRunning.value || isPaused.value || isStopping.value);

const startLabel = computed(() => {
  if (isStopping.value) return '⏳ 正在中止...';
  if (isActive.value) return '⏳ 运行中...';
  return '▶ 开始下载';
});

function onStart() {
  emit('start', {
    query: query.value.trim(),
    outputDir: dir.value.trim(),
    includeDeleted: props.site === 'danbooru' && includeDeleted.value,
  });
}

const placeholder = computed(() =>
  props.site === 'danbooru' ? '例: shingeki_no_kyojin' : '例: hatsune_miku',
);

const primaryClass = computed(() =>
  props.site === 'danbooru' ? 'btn-primary-d' : 'btn-primary-y',
);
</script>

<template>
  <div class="form-body">
    <div class="field">
      <label>搜索词</label>
      <el-input v-model="query" :placeholder="placeholder" clearable />
    </div>
    <div class="field">
      <label>保存目录</label>
      <el-input v-model="dir" placeholder="D:\\crawler\\images" />
    </div>
    <div v-if="site === 'danbooru'" class="toggle-row">
      <span class="toggle-label">同时下载已删除图片</span>
      <el-switch v-model="includeDeleted" />
    </div>
    <div class="btn-row">
      <button class="btn" :class="primaryClass" :disabled="isActive" @click="onStart">
        {{ startLabel }}
      </button>
      <button
        v-if="isRunning || isPaused"
        class="btn btn-pause"
        :title="isPaused ? '继续' : '暂停'"
        @click="emit('toggle-pause')"
      >
        {{ isPaused ? '▶' : '⏸' }}
      </button>
      <button
        v-if="isActive"
        class="btn btn-stop"
        :disabled="isStopping"
        :title="isStopping ? '正在中止...' : '中止'"
        @click="emit('stop')"
      >
        ⏹
      </button>
    </div>
  </div>
</template>

<style scoped>
.form-body {
  display: flex;
  flex-direction: column;
  padding: 18px 18px 16px;
  gap: 14px;
}
.field label {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 6px;
  font-weight: 500;
}
.toggle-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--card);
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
}
.toggle-label {
  font-size: 13px;
  color: var(--text);
}
.btn-row {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}
.btn {
  flex: 1;
  padding: 11px 14px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-weight: 600;
  font-size: 13px;
  border: none;
  transition:
    filter 0.18s,
    transform 0.08s,
    background 0.2s,
    color 0.2s;
}
.btn:active:not(:disabled) {
  transform: scale(0.97);
}
.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.btn-primary-d {
  background: var(--accent-d);
  color: #fff;
}
.btn-primary-d:hover:not(:disabled) {
  filter: brightness(1.1);
}
.btn-primary-y {
  background: var(--accent-y);
  color: #fff;
}
.btn-primary-y:hover:not(:disabled) {
  filter: brightness(1.1);
}
.btn-pause,
.btn-stop {
  flex: 0 0 42px;
  font-size: 15px;
}
.btn-pause {
  background: var(--accent-pause);
  color: #fff;
}
.btn-pause:hover:not(:disabled) {
  filter: brightness(1.1);
}
.btn-stop {
  background: var(--accent-err);
  color: #fff;
}
.btn-stop:hover:not(:disabled) {
  filter: brightness(1.1);
}
</style>