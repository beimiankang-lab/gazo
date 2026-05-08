<script setup lang="ts">
import { onMounted, ref } from 'vue';
import AppHeader from '@/components/AppHeader.vue';
import Sidebar from '@/components/Sidebar.vue';
import LogPanel from '@/components/LogPanel.vue';
import HelpModal from '@/components/HelpModal.vue';
import { getConfig } from '@/api';
import type { Site } from '@/types';

const currentSite = ref<Site>('danbooru');
const currentLog = ref<Site>('danbooru');
const helpOpen = ref(false);
const defaultDir = ref('');

function switchSite(site: Site) {
  currentSite.value = site;
  currentLog.value = site;
}

onMounted(async () => {
  try {
    const cfg = await getConfig();
    defaultDir.value = cfg.default_dir;
  } catch {
    // 后端不可用时让用户自己填
  }
});
</script>

<template>
  <div class="app-shell">
    <AppHeader @open-help="helpOpen = true" />
    <main class="layout">
      <Sidebar
        :current-site="currentSite"
        :default-dir="defaultDir"
        @switch-site="switchSite"
      />
      <LogPanel v-model:current-log="currentLog" />
    </main>
    <HelpModal v-model="helpOpen" />
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