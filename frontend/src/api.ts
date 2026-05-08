import type { RecordsResponse, StartPayload, TaskStatus, AppConfig } from '@/types';

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