import { reactive } from 'vue';
import type { LogEntry, LogLevel, Site, TaskStatus } from '@/types';
import { pauseTask, resumeTask, startTask, stopTask } from '@/api';
import { i18n } from '@/locales';
import { useSettings } from '@/useSettings';

const tt = i18n.global.t as (key: string, params?: Record<string, unknown>) => string;

interface SiteState {
  taskId: string | null;
  status: TaskStatus;
  logs: LogEntry[];
  logCount: number;
  evtSrc: EventSource | null;
  reconnectTimer: number | null;
}

function makeSiteState(): SiteState {
  return {
    taskId: null,
    status: 'idle',
    logs: [],
    logCount: 0,
    evtSrc: null,
    reconnectTimer: null,
  };
}

const state = reactive<Record<Site, SiteState>>({
  danbooru: makeSiteState(),
  yande: makeSiteState(),
});

let nextLogId = 1;

function classify(text: string): LogLevel {
  if (text.includes('[DEBUG]')) return 'debug';
  if (text.includes('[WARNING]') || text.includes('[警告]')) return 'warn';
  if (text.includes('[ERROR]') || text.includes('失败')) return 'error';
  return 'info';
}

function appendLog(site: Site, text: string, level: LogLevel = 'info') {
  state[site].logs.push({ id: nextLogId++, text, level });
}

function appendSysLog(site: Site, text: string) {
  appendLog(site, text, 'sys');
}

function closeStream(site: Site) {
  const s = state[site];
  if (s.evtSrc) {
    s.evtSrc.close();
    s.evtSrc = null;
  }
  if (s.reconnectTimer !== null) {
    window.clearTimeout(s.reconnectTimer);
    s.reconnectTimer = null;
  }
}

function listenLogs(site: Site, taskId: string, offset: number) {
  const s = state[site];
  closeStream(site);

  const evtSrc = new EventSource(`/api/logs/${taskId}?offset=${offset}`);
  s.evtSrc = evtSrc;

  evtSrc.onmessage = (e) => {
    let data: { heartbeat?: number; done?: boolean; status?: TaskStatus; log?: string };
    try {
      data = JSON.parse(e.data);
    } catch {
      return;
    }

    if (data.heartbeat) return;

    if (data.done) {
      closeStream(site);
      const finalStatus: TaskStatus =
        data.status === 'error'
          ? 'error'
          : data.status === 'stopped'
            ? 'stopped'
            : 'done';
      s.status = finalStatus;
      appendSysLog(site, finalStatus === 'stopped' ? tt('log.taskStop') : tt('log.taskDone'));
      return;
    }

    if (data.log) {
      appendLog(site, data.log, classify(data.log));
      s.logCount += 1;
    }
  };

  evtSrc.onerror = () => {
    closeStream(site);
    if (s.status === 'running' || s.status === 'paused' || s.status === 'stopping') {
      s.reconnectTimer = window.setTimeout(() => {
        if (s.taskId === taskId) listenLogs(site, taskId, s.logCount);
      }, 2000);
    }
  };
}

export function useTasks() {
  async function start(site: Site, query: string, outputDir: string, includeDeleted = false) {
    const s = state[site];
    const settings = useSettings();
    closeStream(site);
    s.logs = [];
    s.logCount = 0;
    s.status = 'running';
    appendSysLog(site, tt('log.taskStart', { site: site === 'danbooru' ? 'Danbooru' : 'Yande.re', query }));

    try {
      const { task_id } = await startTask({
        site,
        query,
        output_dir: outputDir,
        include_deleted: includeDeleted,
        template_preset: settings.templatePreset,
        template_custom: settings.templateCustom,
        filters: {
          allow_image: settings.fileTypes.image,
          allow_animated: settings.fileTypes.animated,
          allow_video: settings.fileTypes.video,
          max_size_mb: settings.maxSizeMb,
        },
      });
      s.taskId = task_id;
      listenLogs(site, task_id, 0);
    } catch (e) {
      s.status = 'error';
      appendLog(site, tt('log.networkError', { msg: (e as Error).message }), 'error');
      throw e;
    }
  }

  async function togglePause(site: Site) {
    const s = state[site];
    if (!s.taskId) return;
    const fn = s.status === 'paused' ? resumeTask : pauseTask;
    const { status } = await fn(s.taskId);
    s.status = status;
  }

  async function requestStop(site: Site) {
    const s = state[site];
    if (!s.taskId) return;
    s.status = 'stopping';
    try {
      await stopTask(s.taskId);
    } catch (e) {
      appendLog(site, tt('form.stopFailed', { msg: (e as Error).message }), 'error');
    }
  }

  return {
    state,
    start,
    togglePause,
    requestStop,
  };
}