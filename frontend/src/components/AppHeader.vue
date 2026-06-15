<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { version } from '../../package.json';

const logoUrl = '/logo/logo.png';
const { t } = useI18n();

defineEmits<{
  'open-help': [];
  'open-records': [];
  'open-changelog': [];
  'open-settings': [];
}>();
</script>

<template>
  <header class="app-header">
    <div class="brand-block">
      <div class="logo">
        <img :src="logoUrl" alt="Gazo" />
      </div>
      <div>
        <h1>Gazo</h1>
        <span class="subtitle">{{ t('header.subtitle') }}</span>
      </div>
    </div>
    <div class="flex-spacer" />
    <div class="header-actions">
      <button class="pill-btn" @click="$emit('open-help')">{{ t('header.help') }}</button>
      <button class="pill-btn" @click="$emit('open-records')">{{ t('records.title') }}</button>
      <button class="pill-btn" @click="$emit('open-changelog')">v{{ version }}</button>
      <button class="icon-btn" :title="t('header.settings')" @click="$emit('open-settings')">S</button>
      <span class="badge">{{ t('header.badge') }}</span>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  min-height: 64px;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 10px 16px 10px 18px;
  border: 1px solid var(--border);
  border-radius: 22px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.07), transparent 36%),
    linear-gradient(180deg, rgba(24, 34, 51, 0.95), rgba(15, 21, 32, 0.92));
  box-shadow: 0 18px 44px rgba(0, 0, 0, 0.24);
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.logo {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: var(--card-strong);
  border: 1px solid var(--border-strong);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.logo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  line-height: 1.05;
  letter-spacing: 0;
}

.subtitle {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.flex-spacer {
  flex: 1;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pill-btn {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid var(--border);
  padding: 8px 13px;
  border-radius: 12px;
  cursor: pointer;
  transition:
    color 0.2s,
    border-color 0.2s,
    background 0.2s;
}

.pill-btn:hover {
  color: var(--text);
  border-color: var(--border-strong);
  background: rgba(255, 255, 255, 0.07);
}

.icon-btn {
  background: var(--card);
  border: 1px solid var(--border);
  color: var(--text-muted);
  width: 36px;
  height: 36px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
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
  transform: translateY(-1px);
}

.badge {
  font-size: 11px;
  color: var(--text);
  background: color-mix(in srgb, var(--accent) 18%, transparent);
  border: 1px solid color-mix(in srgb, var(--accent) 36%, var(--border));
  padding: 7px 10px;
  border-radius: 12px;
  font-weight: 700;
}

@media (max-width: 680px) {
  .app-header {
    min-height: auto;
    align-items: flex-start;
    flex-wrap: wrap;
    border-radius: 18px;
  }

  .brand-block {
    flex: 1 1 180px;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
  }

  .badge {
    display: none;
  }
}
</style>
