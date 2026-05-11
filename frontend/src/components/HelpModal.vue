<script setup lang="ts">
import { useI18n } from 'vue-i18n';

const model = defineModel<boolean>({ required: true });
const { t, tm } = useI18n();

const s1 = tm('help.s1') as string[];
const s3 = tm('help.s3') as string[];
</script>

<template>
  <el-dialog
    v-model="model"
    :title="t('help.title')"
    width="640px"
    align-center
    :close-on-click-modal="false"
  >
    <div class="help-body">
      <section>
        <h3>{{ t('help.h1') }}</h3>
        <ol>
          <li v-for="(line, idx) in s1" :key="idx">{{ line }}</li>
        </ol>
      </section>
      <section>
        <h3>{{ t('help.h2') }}</h3>
        <p>{{ t('help.s2') }}</p>
        <pre>{{ t('help.s2ex') }}</pre>
        <p>{{ t('help.s2note') }}</p>
      </section>
      <section>
        <h3>{{ t('help.h3') }}</h3>
        <ul>
          <li v-for="(line, idx) in s3" :key="idx">{{ line }}</li>
        </ul>
      </section>
      <section>
        <h3>{{ t('help.h4') }}</h3>
        <p>{{ t('help.s4') }}</p>
      </section>
    </div>
  </el-dialog>
</template>

<style scoped>
.help-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 8px;
}
.help-body h3 {
  font-size: 14px;
  color: var(--accent);
  margin-bottom: 6px;
}
.help-body p,
.help-body li {
  font-size: 13px;
  line-height: 1.7;
  color: var(--text);
}
.help-body ol,
.help-body ul {
  padding-left: 20px;
}
.help-body pre {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--accent-y);
  margin: 6px 0;
  overflow-x: auto;
}
</style>
