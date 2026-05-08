export type Site = 'danbooru' | 'yande';

export type TaskStatus =
  | 'idle'
  | 'running'
  | 'paused'
  | 'stopping'
  | 'stopped'
  | 'done'
  | 'error';

export type LogLevel = 'info' | 'debug' | 'warn' | 'error' | 'sys';

export interface LogEntry {
  id: number;
  text: string;
  level: LogLevel;
}

export interface RecordsResponse {
  danbooru: Record<string, number>;
  yande: Record<string, number>;
}

export interface StartPayload {
  site: Site;
  query: string;
  output_dir: string;
  include_deleted?: boolean;
}

export interface AppConfig {
  default_dir: string;
}