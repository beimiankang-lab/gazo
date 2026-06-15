<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import AppHeader from '@/components/AppHeader.vue';
import Sidebar from '@/components/Sidebar.vue';
import LogPanel from '@/components/LogPanel.vue';
import HelpModal from '@/components/HelpModal.vue';
import ChangelogModal from '@/components/ChangelogModal.vue';
import SettingsDrawer from '@/components/SettingsDrawer.vue';
import RecordsList from '@/components/RecordsList.vue';
import { getConfig, sendHeartbeat } from '@/api';
import { getSiteSettings, useSettings } from '@/useSettings';
import { useTasks } from '@/useTasks';
import type { Site } from '@/types';

const currentSite = ref<Site>('danbooru');
const currentLog = ref<Site>('danbooru');
const helpOpen = ref(false);
const changelogOpen = ref(false);
const settingsOpen = ref(false);
const recordsOpen = ref(false);

const settings = useSettings();
const { reattachActiveTasks, state } = useTasks();

let heartbeatTimer: number | null = null;

const sidebarRef = ref<InstanceType<typeof Sidebar> | null>(null);
const recordsRef = ref<InstanceType<typeof RecordsList> | null>(null);

const activeDir = computed(() => settings.defaultDir || getSiteSettings(currentSite.value).outputDir);

watch(
  () => settings.defaultDir,
  (value) => {
    if (value) {
      getSiteSettings('danbooru').outputDir = value;
      getSiteSettings('yande').outputDir = value;
    }
  },
  { immediate: true },
);

watch(
  () => [state.danbooru.status, state.yande.status],
  () => {
    recordsRef.value?.refresh();
  },
);

function switchSite(site: Site) {
  currentSite.value = site;
  currentLog.value = site;
}

function switchLog(site: Site) {
  currentLog.value = site;
  currentSite.value = site;
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
    const resolvedDir = settings.defaultDir || cfg.default_dir;
    getSiteSettings('danbooru').outputDir = resolvedDir;
    getSiteSettings('yande').outputDir = resolvedDir;
  } catch {
    // Ignore config bootstrap errors when backend is unavailable.
  }

  reattachActiveTasks();
  sendHeartbeat();
  heartbeatTimer = window.setInterval(sendHeartbeat, 5000);
});

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey);
  if (heartbeatTimer !== null) window.clearInterval(heartbeatTimer);
});
</script>

<template>
  <div class="app-shell">
    <AppHeader
      @open-help="helpOpen = true"
      @open-records="recordsOpen = true"
      @open-changelog="changelogOpen = true"
      @open-settings="settingsOpen = true"
    />
    <main class="layout">
      <Sidebar ref="sidebarRef" :current-site="currentSite" @switch-site="switchSite" />
      <LogPanel :current-log="currentLog" @update:current-log="switchLog" />
    </main>
    <el-drawer v-model="recordsOpen" size="420px" :title="' '" class="records-drawer">
      <RecordsList ref="recordsRef" :output-dir="activeDir" />
    </el-drawer>
    <HelpModal v-model="helpOpen" />
    <ChangelogModal v-model="changelogOpen" />
    <SettingsDrawer v-model="settingsOpen" :current-dir="activeDir" />
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  padding: 12px;
  gap: 12px;
}

.layout {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(370px, 430px) minmax(0, 1fr);
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 24px;
  background: rgba(9, 13, 19, 0.72);
  box-shadow: var(--shadow);
}

@media (max-width: 680px) {
  .app-shell {
    padding: 8px;
    gap: 8px;
  }

  .layout {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(0, 1fr) minmax(300px, 44vh);
    border-radius: 18px;
  }
}
</style>
