<script setup lang="ts">
const logoUrl = '/logo/logo.png';
defineEmits<{ 'open-help': [] }>();
</script>

<template>
  <header class="app-header">
    <div class="logo">
      <img :src="logoUrl" alt="Gazō" />
    </div>
    <h1>
      Gazō
      <span class="subtitle">画像を集める</span>
    </h1>
    <div class="flex-spacer" />
    <button class="help-btn" @click="$emit('open-help')">? 使用教程</button>
    <span class="badge">Danbooru &amp; Yande.re</span>
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
.badge {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--card);
  border: 1px solid var(--border);
  padding: 3px 10px;
  border-radius: 20px;
}
</style>