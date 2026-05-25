import type { RecordsResponse, StartPayload, TaskStatus, AppConfig, DanbooruCredentials } from '@/types';

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { error?: string };
      if (body.error) msg = body.error;
    } catch {
      // ignore
    }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

export async function getConfig(): Promise<AppConfig> {
  const res = await fetch('/api/config');
  return asJson<AppConfig>(res);
}

export interface ActiveTask {
  task_id: string;
  site: 'danbooru' | 'yande';
  query: string;
  raw_query?: string;
  status: TaskStatus;
  log_count: number;
  progress?: { current: number; total: number };
  failed_count?: number;
}

export async function listActiveTasks(): Promise<ActiveTask[]> {
  const res = await fetch('/api/tasks');
  return asJson<ActiveTask[]>(res);
}

export async function sendHeartbeat(): Promise<void> {
  // 用 keepalive 让浏览器关闭瞬间发出的请求也能送到后端
  await fetch('/api/heartbeat', { method: 'POST', keepalive: true }).catch(() => {});
}

export interface TemplatePreviewResult {
  ok: boolean;
  preview?: string;
  error?: string;
}

export async function previewTemplate(
  site: 'danbooru' | 'yande',
  pathTemplate: string,
  fileTemplate: string,
): Promise<TemplatePreviewResult> {
  const res = await fetch('/api/preview_template', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ site, path_template: pathTemplate, file_template: fileTemplate }),
  });
  return asJson<TemplatePreviewResult>(res);
}

export interface ImportResult {
  ok: boolean;
  danbooru: { new_queries: number; new_ids: number; total_queries: number };
  yande: { new_queries: number; new_ids: number; total_queries: number };
}

/**
 * 触发浏览器下载导出文件。
 * 后端会返回 Content-Disposition: attachment，文件名形如 gazo-records-YYYYMMDD-HHMMSS.json。
 */
export function downloadRecordsExport(outputDir: string): void {
  const url = `/api/export_records?output_dir=${encodeURIComponent(outputDir)}`;
  const a = document.createElement('a');
  a.href = url;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  a.remove();
}

export async function importRecords(file: File, outputDir: string): Promise<ImportResult> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(
    `/api/import_records?output_dir=${encodeURIComponent(outputDir)}`,
    { method: 'POST', body: formData },
  );
  return asJson<ImportResult>(res);
}

export async function startTask(payload: StartPayload): Promise<{ task_id: string }> {
  const res = await fetch('/api/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return asJson<{ task_id: string }>(res);
}

export async function pauseTask(taskId: string): Promise<{ status: TaskStatus }> {
  const res = await fetch('/api/pause', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_id: taskId }),
  });
  return asJson<{ status: TaskStatus }>(res);
}

export async function resumeTask(taskId: string): Promise<{ status: TaskStatus }> {
  const res = await fetch('/api/resume', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_id: taskId }),
  });
  return asJson<{ status: TaskStatus }>(res);
}

export async function retryFailed(taskId: string): Promise<{ ok: boolean; retry_count: number }> {
  const res = await fetch('/api/retry_failed', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_id: taskId }),
  });
  return asJson<{ ok: boolean; retry_count: number }>(res);
}

export async function stopTask(taskId: string): Promise<{ status: TaskStatus }> {
  const res = await fetch('/api/stop', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_id: taskId }),
  });
  return asJson<{ status: TaskStatus }>(res);
}

export async function fetchRecords(outputDir: string): Promise<RecordsResponse> {
  const res = await fetch(`/api/records?output_dir=${encodeURIComponent(outputDir)}`);
  return asJson<RecordsResponse>(res);
}

export async function resetRecord(
  site: 'danbooru' | 'yande',
  query: string,
  outputDir: string,
): Promise<{ ok: boolean }> {
  const res = await fetch('/api/reset', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ site, query, output_dir: outputDir }),
  });
  return asJson<{ ok: boolean }>(res);
}

export async function saveConfig(creds: DanbooruCredentials): Promise<{ ok: boolean }> {
  const res = await fetch('/api/save_config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(creds),
  });
  return asJson<{ ok: boolean }>(res);
}

export async function testDanbooru(
  creds: DanbooruCredentials,
): Promise<{ ok: boolean; username?: string; error?: string }> {
  const res = await fetch('/api/test_danbooru', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(creds),
  });
  return asJson<{ ok: boolean; username?: string; error?: string }>(res);
}
