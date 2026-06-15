<script setup lang="ts">
import { useI18n } from 'vue-i18n';

const model = defineModel<boolean>({ required: true });
const { t, tm } = useI18n();

const versions = tm('changelog.versions') as { version: string; date: string; changes: string[] }[];
</script>

<template>
  <el-dialog
    v-model="model"
    :title="t('changelog.title')"
    width="560px"
    align-center
    :close-on-click-modal="false"
  >
    <div class="changelog-body">
      <section v-for="(v, idx) in versions" :key="idx">
        <div class="version-header">
          <span class="version-tag">{{ v.version }}</span>
          <span class="version-date">{{ v.date }}</span>
        </div>
        <ul>
          <li v-for="(line, li) in v.changes" :key="li">{{ line }}</li>
        </ul>
      </section>
    </div>
  </el-dialog>
</template>

<style scoped>
.changelog-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 8px;
}

.changelog-body section {
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 16px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent 70%),
    rgba(255, 255, 255, 0.025);
}

.version-header {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 8px;
}

.version-tag {
  font-size: 15px;
  font-weight: 800;
  color: var(--accent);
}

.version-date {
  font-size: 12px;
  color: var(--text-muted);
}

.changelog-body li {
  font-size: 13px;
  line-height: 1.7;
  color: var(--text);
}

.changelog-body ul {
  padding-left: 20px;
}
</style>
