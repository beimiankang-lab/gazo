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
  template_preset?: string;
  template_custom?: string;
  filters?: {
    allow_image: boolean;
    allow_animated: boolean;
    allow_video: boolean;
    max_size_mb: number | null;
  };
}

export interface AppConfig {
  default_dir: string;
  danbooru_login_set: boolean;
}

export interface DanbooruCredentials {
  danbooru_login: string;
  danbooru_api_key: string;
}