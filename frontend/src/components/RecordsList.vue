<script setup lang="ts">
import { nextTick, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage, ElMessageBox } from 'element-plus';
import type { RecordsResponse, Site } from '@/types';
import { fetchRecords, resetRecord } from '@/api';

const props = defineProps<{ outputDir: string }>();

const { t } = useI18n();

const records = ref<RecordsResponse>({ danbooru: {}, yande: {} });
const items = ref<{ site: Site; query: string; count: number }[]>([]);

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
  for (const [q, c] of Object.entries(records.value.danbooru ?? {})) {
    list.push({ site: 'danbooru', query: q, count: c as number });
  }
  for (const [q, c] of Object.entries(records.value.yande ?? {})) {
    list.push({ site: 'yande', query: q, count: c as number });
  }
  items.value = list;
}

async function onReset(site: Site, query: string) {
  try {
    await ElMessageBox.confirm(
      t('records.resetConfirmMsg', { site: site === 'danbooru' ? 'Danbooru' : 'Yande.re', query }),
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
      <span class="title">{{ t('records.title') }}</span>
      <button class="refresh" :title="t('common.refresh')" @click="refresh">↻</button>
    </div>
    <div class="records-list">
      <div v-if="items.length === 0" class="empty">{{ t('records.empty') }}</div>
      <div v-for="item in items" v-else :key="`${item.site}-${item.query}`" class="record-item">
        <span class="pill" :class="item.site">{{ item.site === 'danbooru' ? 'D' : 'Y' }}</span>
        <span class="qname" :title="item.query">{{ item.query }}</span>
        <span class="cnt">{{ t('records.items', { n: item.count }) }}</span>
        <button
          class="del-btn"
          :title="t('records.resetTooltip')"
          @click="onReset(item.site, item.query)"
        >✕</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.records {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  padding: 14px 18px 18px;
}
.records-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.refresh {
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 16px;
  transition: color 0.2s;
}
.refresh:hover {
  color: var(--text);
}
.records-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-y: auto;
  flex: 1;
}
.empty {
  text-align: center;
  color: var(--text-muted);
  padding: 20px 0;
  font-size: 12px;
}
.record-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 12px;
  transition: border-color 0.2s;
}
.record-item:hover {
  border-color: var(--text-muted);
}
.pill {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  font-weight: 700;
  font-size: 11px;
  color: #fff;
}
.pill.danbooru {
  background: var(--accent-d);
}
.pill.yande {
  background: var(--accent-y);
}
.qname {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text);
}
.cnt {
  color: var(--text-muted);
  flex-shrink: 0;
}
.del-btn {
  background: transparent;
  color: var(--text-muted);
  border: none;
  cursor: pointer;
  font-size: 12px;
  padding: 2px 6px;
  flex-shrink: 0;
  transition: color 0.2s;
}
.del-btn:hover {
  color: var(--accent-err);
}
</style>
