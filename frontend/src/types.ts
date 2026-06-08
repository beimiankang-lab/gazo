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
  raw_query?: string;
  output_dir: string;
  download_concurrency?: number;
  include_deleted?: boolean;
  template_preset?: string;
  template_custom?: string;
  path_template?: string;
  file_template?: string;
  max_posts?: number | null;
  ratings?: string[];
  whitelist_tags?: string[];
  whitelist_mode?: 'and' | 'or';
  include_no_author?: boolean;
  auto_retry?: boolean;
  dedup_mode?: string;
  filters?: {
    allow_image: boolean;
    allow_animated: boolean;
    allow_video: boolean;
    max_size_mb: number | null;
  };
}

export interface ProgressData {
  current: number;
  total: number;
}

export interface FailedItem {
  post_id: number;
  file_url: string;
  filepath: string;
  error: string;
}

export interface AppConfig {
  default_dir: string;
  danbooru_login_set: boolean;
}

export interface DanbooruCredentials {
  danbooru_login: string;
  danbooru_api_key: string;
}
