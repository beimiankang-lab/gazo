<script setup lang="ts">
import { nextTick, ref, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import type { RecordsResponse, Site } from '@/types';
import { downloadRecordsExport, fetchRecords, importRecords, resetRecord } from '@/api';

const props = defineProps<{ outputDir: string }>();

const records = ref<RecordsResponse>({ danbooru: {}, yande: {} });
const items = ref<{ site: Site; query: string; count: number }[]>([]);
const fileInputRef = ref<HTMLInputElement | null>(null);
const importing = ref(false);

async function refresh() {
  try {
    const data = await fetchRecords(props.outputDir);
    records.value = data;
    flatten();
  } catch {
    items.value = [];
  }
}

function flatten() {
  const list: { site: Site; query: string; count: number }[] = [];
  for (const [query, count] of Object.entries(records.value.danbooru ?? {})) {
    list.push({ site: 'danbooru', query, count: count as number });
  }
  for (const [query, count] of Object.entries(records.value.yande ?? {})) {
    list.push({ site: 'yande', query, count: count as number });
  }
  items.value = list;
}

async function onReset(site: Site, query: string) {
  try {
    await ElMessageBox.confirm(
      `确定清除 ${site === 'danbooru' ? 'Danbooru' : 'Yande.re'} 里 “${query}” 的下载记录吗？`,
      '清除记录',
      {
        confirmButtonText: '清除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    );
  } catch {
    return;
  }

  try {
    await resetRecord(site, query, props.outputDir);
    ElMessage.success(`已清除 “${query}” 的记录`);
    refresh();
  } catch (e) {
    ElMessage.error(`清除失败: ${(e as Error).message}`);
  }
}

function onExport() {
  if (items.value.length === 0) {
    ElMessage.warning('当前没有可导出的下载记录');
    return;
  }
  downloadRecordsExport(props.outputDir);
  ElMessage.success('已开始导出下载记录');
}

function triggerImport() {
  fileInputRef.value?.click();
}

async function onFilePicked(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file) return;

  importing.value = true;
  try {
    const result = await importRecords(file, props.outputDir);
    const totalIds = result.danbooru.new_ids + result.yande.new_ids;
    const totalQueries = result.danbooru.new_queries + result.yande.new_queries;
    ElMessage.success(`导入成功：新增 ${totalIds} 个 ID，新增 ${totalQueries} 个搜索词`);
    refresh();
  } catch (e) {
    ElMessage.error(`导入失败: ${(e as Error).message}`);
  } finally {
    importing.value = false;
  }
}

watch(
  () => props.outputDir,
  () => nextTick(refresh),
);

refresh();

defineExpose({ refresh });
</script>

<template>
  <section class="records">
    <div class="records-header">
      <div>
        <div class="title">已下载记录</div>
        <div class="subtitle">{{ props.outputDir || '当前目录未设置' }}</div>
      </div>
      <div class="actions">
        <button class="tool-btn" @click="onExport">导出</button>
        <button class="tool-btn" :disabled="importing" @click="triggerImport">
          {{ importing ? '导入中...' : '导入' }}
        </button>
        <button class="tool-btn" @click="refresh">刷新</button>
      </div>
      <input
        ref="fileInputRef"
        type="file"
        accept="application/json,.json"
        style="display: none"
        @change="onFilePicked"
      />
    </div>

    <div class="records-list">
      <div v-if="items.length === 0" class="empty">当前目录还没有下载记录</div>
      <div v-for="item in items" :key="`${item.site}-${item.query}`" class="record-item">
        <span class="site-pill" :class="item.site">
          {{ item.site === 'danbooru' ? 'D' : 'Y' }}
        </span>
        <div class="record-main">
          <div class="record-query" :title="item.query">{{ item.query }}</div>
          <div class="record-meta">{{ item.count }} 张</div>
        </div>
        <button class="reset-btn" @click="onReset(item.site, item.query)">清除</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.records {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.records-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border);
}

.title {
  font-size: 16px;
  font-weight: 800;
  color: var(--text);
}

.subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-muted);
  word-break: break-all;
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.tool-btn,
.reset-btn {
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-muted);
  border-radius: 10px;
  padding: 7px 10px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition:
    border-color 0.18s,
    color 0.18s,
    background 0.18s,
    transform 0.12s;
}

.tool-btn:disabled {
  opacity: 0.6;
  cursor: wait;
}

.tool-btn:hover:not(:disabled),
.reset-btn:hover {
  color: var(--text);
  border-color: var(--border-strong);
  background: rgba(255, 255, 255, 0.07);
  transform: translateY(-1px);
}

.records-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  min-height: 0;
}

.empty {
  padding: 24px 0;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
  border: 1px dashed var(--border);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.025);
}

.record-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent),
    var(--panel);
  border: 1px solid var(--border);
  border-radius: 14px;
  transition:
    border-color 0.18s,
    background 0.18s;
}

.record-item:hover {
  border-color: var(--border-strong);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.065), transparent),
    var(--panel);
}

.site-pill {
  width: 28px;
  height: 28px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 11px;
  font-weight: 800;
}

.site-pill.danbooru {
  background: var(--accent-d);
}

.site-pill.yande {
  background: var(--accent-y);
}

.record-main {
  flex: 1;
  min-width: 0;
}

.record-query {
  color: var(--text);
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.record-meta {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
}

@media (max-width: 520px) {
  .records-header {
    flex-direction: column;
  }

  .actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
