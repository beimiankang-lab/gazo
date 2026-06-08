<script setup lang="ts">
import { useI18n } from 'vue-i18n';

const model = defineModel<boolean>({ required: true });
const { t, tm } = useI18n();

const s1 = tm('help.s1') as string[];
const s3 = tm('help.s3') as string[];
const s6 = tm('help.s6') as string[];
const s7 = tm('help.s7') as string[];
const s9 = tm('help.s9') as string[];
const s10 = tm('help.s10') as string[];
const s11 = tm('help.s11') as string[];
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
      <section>
        <h3>{{ t('help.h5') }}</h3>
        <p>{{ t('help.s5') }}</p>
      </section>
      <section>
        <h3>{{ t('help.h6') }}</h3>
        <ul>
          <li v-for="(line, idx) in s6" :key="idx">{{ line }}</li>
        </ul>
      </section>
      <section>
        <h3>{{ t('help.h7') }}</h3>
        <ul>
          <li v-for="(line, idx) in s7" :key="idx">{{ line }}</li>
        </ul>
      </section>
      <section>
        <h3>{{ t('help.h8') }}</h3>
        <p>{{ t('help.s8') }}</p>
      </section>
      <section>
        <h3>{{ t('help.h9') }}</h3>
        <ul>
          <li v-for="(line, idx) in s9" :key="idx">{{ line }}</li>
        </ul>
      </section>
      <section>
        <h3>{{ t('help.h10') }}</h3>
        <ul>
          <li v-for="(line, idx) in s10" :key="idx">{{ line }}</li>
        </ul>
      </section>
      <section>
        <h3>{{ t('help.h11') }}</h3>
        <ul>
          <li v-for="(line, idx) in s11" :key="idx">{{ line }}</li>
        </ul>
      </section>
    </div>
  </el-dialog>
</template>

<style scoped>
.help-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 8px;
}

.help-body section {
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 16px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent 70%),
    rgba(255, 255, 255, 0.025);
}

.help-body h3 {
  font-size: 14px;
  color: var(--accent);
  margin-bottom: 8px;
  font-weight: 800;
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
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 12px;
  color: var(--accent-y);
  margin: 6px 0;
  overflow-x: auto;
  font-family: "Cascadia Mono", Consolas, "Courier New", monospace;
}
</style>
