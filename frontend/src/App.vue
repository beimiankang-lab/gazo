<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import AppHeader from '@/components/AppHeader.vue';
import Sidebar from '@/components/Sidebar.vue';
import LogPanel from '@/components/LogPanel.vue';
import HelpModal from '@/components/HelpModal.vue';
import SettingsDrawer from '@/components/SettingsDrawer.vue';
import { getConfig } from '@/api';
import { useSettings } from '@/useSettings';
import type { Site } from '@/types';

const currentSite = ref<Site>('danbooru');
const currentLog = ref<Site>('danbooru');
const helpOpen = ref(false);
const settingsOpen = ref(false);
const settings = useSettings();

const sidebarRef = ref<InstanceType<typeof Sidebar> | null>(null);

const activeDir = computed(() => settings.defaultDir);

function switchSite(site: Site) {
  currentSite.value = site;
  currentLog.value = site;
}

function onKey(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    sidebarRef.value?.triggerStart();
    return;
  }
  if (e.key === 'Escape') {
    sidebarRef.value?.triggerStop();
    return;
  }
  if (e.key === 'F1') {
    e.preventDefault();
    helpOpen.value = true;
    return;
  }
  if ((e.ctrlKey || e.metaKey) && e.key === ',') {
    e.preventDefault();
    settingsOpen.value = true;
  }
}

onMounted(async () => {
  window.addEventListener('keydown', onKey);
  try {
    const cfg = await getConfig();
    if (!settings.defaultDir) settings.defaultDir = cfg.default_dir;
  } catch {
    // 后端不可用时让用户自己填
  }
});

onBeforeUnmount(() => window.removeEventListener('keydown', onKey));
</script>

<template>
  <div class="app-shell">
    <AppHeader
      @open-help="helpOpen = true"
      @open-settings="settingsOpen = true"
    />
    <main class="layout">
      <Sidebar
        ref="sidebarRef"
        :current-site="currentSite"
        :default-dir="activeDir"
        @switch-site="switchSite"
      />
      <LogPanel v-model:current-log="currentLog" />
    </main>
    <HelpModal v-model="helpOpen" />
    <SettingsDrawer v-model="settingsOpen" :current-dir="activeDir" />
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
.layout {
  flex: 1;
  display: grid;
  grid-template-columns: 340px 1fr;
  height: calc(100vh - 56px);
  overflow: hidden;
}
@media (max-width: 680px) {
  .layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }
}
</style>
