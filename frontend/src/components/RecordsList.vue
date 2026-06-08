<script setup lang="ts">
import { nextTick, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage, ElMessageBox } from 'element-plus';
import type { RecordsResponse, Site } from '@/types';
import { downloadRecordsExport, fetchRecords, importRecords, resetRecord } from '@/api';

const { t } = useI18n();

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
  const siteName = t(`site.${site}`);
  try {
    await ElMessageBox.confirm(
      t('records.resetConfirmMsg', { site: siteName, query }),
      t('records.resetConfirmTitle'),
      {
        confirmButtonText: t('common.reset'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      },
    );
  } catch {
    return;
  }

  try {
    await resetRecord(site, query, props.outputDir);
    ElMessage.success(t('records.resetSuccess', { query }));
    refresh();
  } catch (e) {
    ElMessage.error(t('records.resetFailed', { msg: (e as Error).message }));
  }
}

function onExport() {
  if (items.value.length === 0) {
    ElMessage.warning(t('records.exportEmpty'));
    return;
  }
  downloadRecordsExport(props.outputDir);
  ElMessage.success(t('records.exportSuccess'));
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
    ElMessage.success(t('records.importSuccess', { ids: totalIds, queries: totalQueries }));
    refresh();
  } catch (e) {
    ElMessage.error(t('records.importFailed', { msg: (e as Error).message }));
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
        <div class="title">{{ t('records.title') }}</div>
        <div class="subtitle">{{ props.outputDir || t('records.noDir') }}</div>
      </div>
      <div class="actions">
        <button class="tool-btn" @click="onExport">{{ t('records.exportBtn') }}</button>
        <button class="tool-btn" :disabled="importing" @click="triggerImport">
          {{ importing ? t('records.importing') : t('records.importBtn') }}
        </button>
        <button class="tool-btn" @click="refresh">{{ t('common.refresh') }}</button>
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
      <div v-if="items.length === 0" class="empty">{{ t('records.empty') }}</div>
      <div v-for="item in items" :key="`${item.site}-${item.query}`" class="record-item">
        <span class="site-pill" :class="item.site">
          {{ item.site === 'danbooru' ? 'D' : 'Y' }}
        </span>
        <div class="record-main">
          <div class="record-query" :title="item.query">{{ item.query }}</div>
          <div class="record-meta">{{ t('records.items', { n: item.count }) }}</div>
        </div>
        <button class="reset-btn" @click="onReset(item.site, item.query)">{{ t('common.reset') }}</button>
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
  font-size: 14px;
  font-weight: 600;
  color: var(--text-muted);
  text-align: center;
  padding: 24px 12px;
}

.record-item {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 12px;
  transition: border-color 0.18s;
}

.record-item:hover {
  border-color: var(--border-strong);
}

.site-pill {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 800;
  color: #fff;
}

.site-pill.danbooru {
  background: #8e6bbf;
}

.site-pill.yande {
  background: #fa97b0;
}

.record-main {
  flex: 1;
  min-width: 0;
}

.record-query {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-meta {
  margin-top: 2px;
  font-size: 11px;
  color: var(--text-muted);
}

.reset-btn {
  flex-shrink: 0;
}
</style>
