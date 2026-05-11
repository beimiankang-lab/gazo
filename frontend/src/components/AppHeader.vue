<script setup lang="ts">
import { useI18n } from 'vue-i18n';

const logoUrl = '/logo/logo.png';
const { t } = useI18n();

defineEmits<{ 'open-help': []; 'open-settings': [] }>();
</script>

<template>
  <header class="app-header">
    <div class="logo">
      <img :src="logoUrl" alt="Gazō" />
    </div>
    <h1>
      Gazō
      <span class="subtitle">{{ t('header.subtitle') }}</span>
    </h1>
    <div class="flex-spacer" />
    <button class="help-btn" @click="$emit('open-help')">{{ t('header.help') }}</button>
    <button class="icon-btn gear" :title="t('header.settings')" @click="$emit('open-settings')">⚙</button>
    <span class="badge">{{ t('header.badge') }}</span>
  </header>
</template>

<style scoped>
.app-header {
  background: var(--panel);
  border-bottom: 1px solid var(--border);
  padding: 0 32px;
  height: 56px;
  display: flex;
  align-items: center;
  gap: 12px;
  position: sticky;
  top: 0;
  z-index: 100;
}
.logo {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: var(--card);
}
.logo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
h1 {
  font-size: 17px;
  font-weight: 600;
  letter-spacing: 0.3px;
}
.subtitle {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 400;
  margin-left: 6px;
}
.flex-spacer {
  flex: 1;
}
.help-btn {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--card);
  border: 1px solid var(--border);
  padding: 5px 13px;
  border-radius: 20px;
  cursor: pointer;
  transition:
    color 0.2s,
    border-color 0.2s;
}
.help-btn:hover {
  color: var(--text);
  border-color: var(--text-muted);
}
.icon-btn {
  background: var(--card);
  border: 1px solid var(--border);
  color: var(--text-muted);
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    color 0.2s,
    border-color 0.2s,
    transform 0.3s;
}
.icon-btn:hover {
  color: var(--text);
  border-color: var(--accent);
  transform: rotate(60deg);
}
.badge {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--card);
  border: 1px solid var(--border);
  padding: 3px 10px;
  border-radius: 20px;
}
</style>
