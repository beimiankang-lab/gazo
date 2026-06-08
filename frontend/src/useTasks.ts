import { reactive } from 'vue';
import type { FailedItem, LogEntry, LogLevel, ProgressData, Site, TaskStatus } from '@/types';
import { listActiveTasks, pauseTask, resumeTask, retryFailed, startTask, stopTask } from '@/api';
import { i18n } from '@/locales';
import { getSiteSettings, useSettings } from '@/useSettings';

const tt = i18n.global.t as (key: string, params?: Record<string, unknown>) => string;

interface SiteState {
  taskId: string | null;
  status: TaskStatus;
  query: string;
  logs: LogEntry[];
  logCount: number;
  evtSrc: EventSource | null;
  reconnectTimer: number | null;
  progress: ProgressData;
  failedItems: FailedItem[];
}

function makeSiteState(): SiteState {
  return {
    taskId: null,
    status: 'idle',
    query: '',
    logs: [],
    logCount: 0,
    evtSrc: null,
    reconnectTimer: null,
    progress: { current: 0, total: 0 },
    failedItems: [],
  };
}

const state = reactive<Record<Site, SiteState>>({
  danbooru: makeSiteState(),
  yande: makeSiteState(),
});

let nextLogId = 1;

function classify(text: string): LogLevel {
  if (text.includes('[DEBUG]')) return 'debug';
  if (text.includes('[WARNING]')) return 'warn';
  if (text.includes('[ERROR]')) return 'error';
  if (text.includes('警告')) return 'warn';
  if (text.includes('失败') || text.includes('错误')) return 'error';
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
    let data: {
      heartbeat?: number;
      done?: boolean;
      status?: TaskStatus;
      log?: string;
      type?: string;
      current?: number;
      total?: number;
      failed_posts?: FailedItem[];
    };

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
      if (Array.isArray(data.failed_posts)) s.failedItems = data.failed_posts;
      appendSysLog(site, finalStatus === 'stopped' ? tt('log.taskStop') : tt('log.taskDone'));
      return;
    }

    if (data.type === 'progress' && data.current !== undefined && data.total !== undefined) {
      s.progress = { current: data.current, total: data.total };
      return;
    }

    if (data.type === 'fail') return;

    if (data.log) {
      appendLog(site, data.log, classify(data.log));
      s.logCount += 1;
    }
  };

  evtSrc.onerror = () => {
    closeStream(site);
    if (['running', 'paused', 'stopping'].includes(s.status)) {
      s.reconnectTimer = window.setTimeout(() => {
        if (s.taskId === taskId) listenLogs(site, taskId, s.logCount);
      }, 2000);
    }
  };
}

export function useTasks() {
  async function start(
    site: Site,
    query: string,
    rawQuery: string,
    outputDir: string,
    includeDeleted = false,
    maxPosts: number | null = null,
    ratings?: string[],
  ) {
    const s = state[site];
    const settings = useSettings();
    const siteSettings = getSiteSettings(site);
    closeStream(site);
    s.logs = [];
    s.logCount = 0;
    s.progress = { current: 0, total: 0 };
    s.failedItems = [];
    s.status = 'running';
    s.query = rawQuery;
    appendSysLog(
      site,
      tt('log.taskStart', {
        site: site === 'danbooru' ? 'Danbooru' : 'Yande.re',
        query: rawQuery,
      }),
    );

    try {
      const basePayload = {
        site,
        query,
        raw_query: rawQuery,
        output_dir: outputDir,
        include_deleted: includeDeleted,
        template_preset: settings.templatePreset,
        template_custom: settings.templateCustom,
        path_template: settings.pathTemplate,
        file_template: settings.fileTemplate,
        max_posts: maxPosts,
        ratings,
        whitelist_tags: siteSettings.whitelist,
        whitelist_mode: siteSettings.whitelistMode,
        include_no_author: siteSettings.includeNoAuthor,
        auto_retry: siteSettings.autoRetry,
        dedup_mode: siteSettings.dedupMode,
        filters: {
          allow_image: siteSettings.fileTypes.image,
          allow_animated: siteSettings.fileTypes.animated,
          allow_video: siteSettings.fileTypes.video,
          max_size_mb: siteSettings.maxSizeMb,
        },
      };
      const { task_id } = await startTask({
        ...basePayload,
        download_concurrency:
          site === 'danbooru'
            ? settings.danbooruDownloadConcurrency
            : settings.yandeDownloadConcurrency,
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
    if (!s.taskId || s.status === 'stopping') return;
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

  async function retryFailedDownloads(site: Site) {
    const s = state[site];
    if (!s.taskId) return;
    s.status = 'running';
    s.progress = { current: 0, total: s.failedItems.length };
    s.failedItems = [];
    appendSysLog(site, tt('log.retryStart', { n: s.progress.total }));
    try {
      await retryFailed(s.taskId);
      listenLogs(site, s.taskId, s.logCount);
    } catch (e) {
      s.status = 'error';
      appendLog(site, tt('log.retryFailed', { msg: (e as Error).message }), 'error');
    }
  }

  async function reattachActiveTasks() {
    try {
      const tasks = await listActiveTasks();
      for (const task of tasks) {
        const s = state[task.site];
        if (s.taskId === task.task_id && s.evtSrc) continue;
        closeStream(task.site);
        s.taskId = task.task_id;
        s.status = task.status;
        s.query = task.raw_query || task.query;
        s.logs = [];
        s.logCount = 0;
        s.progress = task.progress || { current: 0, total: 0 };
        s.failedItems = [];
        appendSysLog(
          task.site,
          tt('log.taskReattach', {
            site: task.site === 'danbooru' ? 'Danbooru' : 'Yande.re',
            query: s.query,
          }),
        );
        listenLogs(task.site, task.task_id, 0);
      }
    } catch {
      // Ignore reconnect failures when backend is unavailable.
    }
  }

  return {
    state,
    start,
    togglePause,
    requestStop,
    reattachActiveTasks,
    retryFailedDownloads,
  };
}
