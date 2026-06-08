<p align="center">
  <img src="frontend/public/logo/logo.png" alt="Gazō" width="140">
</p>

<h1 align="center">Gazō — Booru Image Crawler</h1>

<p align="center">
  <strong>English</strong> ·
  <a href="README.zh-CN.md">简体中文</a> ·
  <a href="README.zh-TW.md">繁體中文</a> ·
  <a href="README.ja.md">日本語</a>
</p>

<p align="center"><em>画像を集める — a batch image downloader for <a href="https://danbooru.donmai.us">Danbooru</a> and <a href="https://yande.re">Yande.re</a>. Ships with a Web UI that streams live logs and supports pause / resume / stop and download-history management.</em></p>

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Running](#running)
- [UI Overview](#ui-overview)
- [Danbooru Guide](#danbooru-guide)
- [Yande.re Guide](#yandere-guide)
- [Rating & Tag Filters](#rating--tag-filters)
- [Download Deduplication](#download-deduplication)
- [Auto Retry](#auto-retry)
- [Download History](#download-history)
- [Import / Export Records](#import--export-records)
- [Settings](#settings)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Project Layout](#project-layout)
- [CLI Usage](#cli-usage)
- [FAQ](#faq)

---

## Requirements

- Python 3.10 or newer
- Node.js 20+ and npm (for building the frontend; not required if you only run a pre-built artifact)
- Network access to Danbooru / Yande.re (a proxy may be needed in some regions)

---

## Installation

```bash
# 1. Enter the project directory
cd D:\crawler

# 2. Create a virtual environment (optional but recommended)
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running

### Production mode (single port)

The frontend lives under `frontend/` and is built with Vue 3 + Vite. Build the static assets once before the first run:

```bash
# 1. Build the frontend (first clone, or whenever you change frontend code)
cd frontend
npm install
npm run build
cd ..

# 2. Start the backend — Flask serves the built assets
python app.py
```

Then open:

```
http://127.0.0.1:5173
```

> If the frontend has never been built, `python app.py` exits with an error asking you to run `npm run build`.

### Development mode (hot reload)

When working on the frontend, run the two servers separately. Vite proxies `/api` to Flask:

```bash
# Terminal A — Flask (default port 5173)
python app.py

# Terminal B — Vite dev server (port 5174, hot reload)
cd frontend
npm run dev
```

Open the URL printed by Vite (defaults to `http://127.0.0.1:5174`). Changes to Vue files refresh automatically.

---

## UI Overview

```
┌──────────────────────────────────────────────────────────┐
│  Gazō 画像を集める         [?Help]  Danbooru & Yande    │
├─────────────────────┬────────────────────────────────────┤
│  Danbooru │ Yande   │  Danbooru log │ Yande.re log       │
│─────────────────────│───────────────────────────────────-│
│  Search tags        │  [status] idle/run/pause/stop      │
│  Save directory     │                                     │
│                     │  2026-05-07 [INFO] searching...    │
│  ▼ Rating filter   │  2026-05-07 [INFO] get: xxx.jpg    │
│  ☑ General ☑ Safe  │                                     │
│  ☑ Questionable    │                                     │
│  ☑ Explicit        │                                     │
│                     │                                     │
│  ▼ Tag rules       │                                     │
│  Whitelist [AND|OR]│                                     │
│  Blacklist         │                                     │
│  ☐ No-author posts │                                     │
│                     │                                     │
│  ▼ File type/size  │                                     │
│  ☑Images ☑GIF ☑Vid│                                     │
│  Max size: [___] MB│                                     │
│                     │                                     │
│  ☑ Auto-retry      │                                     │
│  ◉ Dedup: local    │                                     │
│                     │                                     │
│  [▶ Start][⏸][⏹]  │                                     │
│─────────────────────│                                     │
│  Download history   │                                     │
│  [Export][Import]   │                                     │
│  D hatsune_miku   N │                                     │
│  Y shingeki ...   N │                                     │
└─────────────────────┴────────────────────────────────────┘
```

| Area | Description |
|------|-------------|
| Left tabs | Switch between Danbooru / Yande.re config forms |
| Right log tabs | View each site's log independently — switching never interrupts a running task |
| Control buttons | ▶ Start, ⏸ Pause / Resume, ⏹ Stop (with confirmation) |
| Status dot | Green pulse = running, orange = paused, red pulse = stopping, red = stopped/error, solid green = done |
| Tab corner dot | Small dot on the top-right of a tab while its task is active — handy for tracking state across tabs |
| Help button | The "? Help" button in the top-right opens a full in-app guide |
| Rating filter | Checkboxes for General / Sensitive / Questionable / Explicit — only checked ratings are downloaded |
| Tag rules | Whitelist (AND/OR mode) and Blacklist to include or exclude posts by tags. "No-author posts" checkbox for downloading authorless images |
| File type/size | Toggle image / GIF / video types, optional max file size limit |
| Auto-retry | Automatically retry failed downloads once after completion |
| Dedup mode | Three options: no skip / current query only / global (all queries) |
| Download history | Left panel showing download counts per query, with Export / Import / Reset buttons |

---

## Danbooru Guide

### 1. Configure the API credentials

Anonymous Danbooru access is limited (safe-rated content only, 20 posts per page). Configure an API key:

1. Register and log in at [danbooru.donmai.us](https://danbooru.donmai.us)
2. Open your profile → **API Key** page and generate a key
   - **Permissions**: picking `All` is the easy path. For least-privilege, pick `Scoped` and tick only `posts:index` — this project only hits `/posts.json`.
   - Downloading "deleted" posts depends on your **account level** (Gold+ is typically required). This is unrelated to API-key scopes.
3. Copy `.env.example` at the project root to `.env` and fill in your credentials:

```bash
DANBOORU_LOGIN=your-username
DANBOORU_API_KEY=your-api-key
```

> `.env` is already in `.gitignore` and will not be pushed to GitHub. It is loaded automatically on startup.

### 2. Search syntax

Danbooru searches by tag combinations separated by spaces:

| Example | Description |
|---------|-------------|
| `hatsune_miku` | Search for Hatsune Miku |
| `shingeki_no_kyojin` | Search for Attack on Titan |
| `hatsune_miku solo` | Combine multiple tags |

> Tag names can be verified in the Danbooru search box. Words inside a tag are joined with underscores.

### 3. Include deleted posts

Enabling this switch performs an extra search for `status:deleted` posts and downloads them as well. Deleted posts may have no accessible original URL — those are skipped automatically.

### 4. File layout

```
downloads/
└── {tag}/
    └── danbooru/
        └── {artist}/
            ├── shingeki_no_kyojin(artist_a)_eren_yeager01.jpg
            └── shingeki_no_kyojin(artist_b)_unknown02.png
```

---

## Yande.re Guide

### 1. Search syntax

Yande.re also uses tag-based search:

| Example | Description |
|---------|-------------|
| `hatsune_miku` | Search for Hatsune Miku |
| `hatsune_miku rating:s` | Only safe-rated posts |

### 2. Tag-type lookup

The first time you download a given query, the tool batches a lookup for every tag's type (artist / character / copyright / ...) so it can auto-group files and directories. The first run is therefore slower; subsequent runs reuse the cache.

### 3. File layout

```
downloads/
└── {tag}/
    └── yande/
        └── {artist}/
            ├── hatsune_miku(artist_a)_hatsune_miku01.jpg
            └── hatsune_miku(unknown)02.jpg
```

---

## Rating & Tag Filters

### Rating filter

Each site supports checkboxes for four rating levels:

| Rating | Description |
|--------|-------------|
| General | All-ages content |
| Sensitive | Mild suggestive content |
| Questionable | Explicit but not extreme |
| Explicit | Adult / explicit content |

Check only the ratings you want — unchecked ratings are filtered out server-side before download. Checking all or none disables the filter.

### Tag rules — Blacklist & Whitelist

Both sites support tag-based filtering in addition to the main search tags:

- **Blacklist**: posts containing *any* of these tags are excluded. Blacklisted tags are prepended with `-` in the API query, which means filtering happens server-side — saving time and bandwidth.
- **Whitelist**: only posts matching whitelist tags are kept. Two modes:
  - **AND** — the post must contain *all* whitelist tags
  - **OR** — the post must contain *at least one* whitelist tag
- **Include posts without authors**: when whitelist is active, checking this also downloads posts that match the main query but have no artist tag.

Whitelist tags are sent as structured filters to the backend, not embedded in the search box. The search box always shows your original query.

### File type & size filter

- Toggle **images** (jpg/png/webp), **animated** (gif), and **video** (mp4/webm/swf) independently. Unchecked types are skipped at download time.
- **Max file size**: set a megabyte cap — files exceeding it are skipped. Leave empty for no limit.

### Limit posts

Set a maximum number of posts to fetch. When OFF, all matching results are downloaded.

---
## Download Deduplication

Three modes control whether already-downloaded posts are skipped:

| Mode | Behavior |
|------|----------|
| **No skip** | Always re-download, regardless of history |
| **Current query only** (default) | Skip IDs that were already downloaded under the *same* search query |
| **Global** | Skip IDs that were downloaded under *any* search query on this site |

History records are always saved per-query regardless of mode. The default `local` mode preserves the original behavior.

---
## Auto Retry

When enabled, after the main download pass completes the backend automatically retries every failed download once (up to 3 attempts per file). No need to click the manual retry button — progress is logged in real time.

---
## Download History

Two JSON files live under `downloads/`:

| File | Description |
|------|-------------|
| `.downloaded_danbooru.json` | IDs of posts already downloaded from Danbooru |
| `.downloaded_yande.json` | IDs of posts already downloaded from Yande.re |

The two sites' histories are fully independent — resetting one does not affect the other.

### Managing history in the UI

- **Reset**: click the **Reset** button next to any query to clear its history. The next run will re-download everything for that query.
- **Refresh**: re-read history from disk (useful if files changed externally).
- See [Import / Export Records](#import--export-records) below for bulk backup and merge.

Files are written atomically (temp file + `os.replace`) to prevent data loss on unexpected shutdown.

---
## Import / Export Records

The Download History panel includes **Export** and **Import** buttons:

- **Export**: downloads a JSON snapshot of all download records (both sites, all queries) — useful for backup or migration.
- **Import**: select a previously-exported JSON file to merge its records into the current history. Duplicate IDs are automatically skipped.

Format:
```json
{
  "version": 1,
  "exported_at": "2026-06-08T12:00:00",
  "danbooru": { "query_name": [123, 456] },
  "yande": { "query_name": [789, 101] }
}
```

---
## Settings

Click the **gear icon** (top-right) to open the settings drawer. Changes are saved to `localStorage` and persist across sessions.

| Tab | Options |
|-----|---------|
| **General** | Interface language (EN / 简体中文 / 繁體中文 / 日本語), theme color (purple / sky / pink / mint / amber / coral) |
| **Downloads** | Concurrency per site (1–8), default save directory, filename templates with placeholders (`{id}`, `{artist}`, `{query}`, `{ext}`, `{md5}`, `{date}`, `{rating}`, etc.) |
| **Filter** | Default rating / file-type / max-size presets applied to new tasks |
| **API Keys** | Danbooru login + API key — test connection button to verify credentials |

---
## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + Enter` | Start download |
| `Ctrl + .` | Stop current task |
| `?` | Open help guide |
| `,` | Open settings |

---
## Project Layout

```
D:\crawler\
├── app.py                      # Flask backend, serves the Web API
├── danbooru_crawler.py         # Danbooru crawler core
├── yande_crawler.py            # Yande.re crawler core
├── requirements.txt            # Python dependencies
├── README.md                   # This file (English)
├── README.zh-CN.md             # 简体中文
├── README.zh-TW.md             # 繁體中文
├── README.ja.md                # 日本語
├── LICENSE                     # MIT License
├── .env.example                # Env-var template
├── .gitignore                  # Git ignore rules
├── frontend/                   # Vue 3 + Vite frontend
│   ├── public/
│   │   └── logo/               # Project logo (served as /logo/ after build)
│   ├── src/
│   │   ├── components/         # Header, form, log panel, history, help modal
│   │   ├── api.ts              # HTTP calls to /api
│   │   ├── useTasks.ts         # Task state + SSE stream
│   │   └── App.vue
│   ├── index.html
│   ├── vite.config.ts          # Dev proxy /api → 5173
│   └── package.json
├── static_dist/                # Build output (generated by npm run build; gitignored)
├── downloads/                  # Image output directory (gitignored)
│   ├── .downloaded_danbooru.json
│   └── .downloaded_yande.json
└── venv/                       # Python virtualenv (gitignored)
```

---

## CLI Usage

You can also run the crawlers without the Web UI:

```bash
# Danbooru
python danbooru_crawler.py

# Yande.re
python yande_crawler.py
```

Follow the prompts:
- `1` — Start downloading
- `2` — Reset the history for a given query
- `3` — List all download history

---

## FAQ

**Q: I get a 403 at runtime.**
A: Anonymous Danbooru access is limited. Create `.env` in the project root and fill in credentials (see `.env.example`).

**Q: Downloads feel slow.**
A: There is a 0.5–1 s delay between images to stay under the sites' rate limits. This is intentional.

**Q: Some images have no download link.**
A: Deleted posts may have had their original removed from the server. The tool skips them and logs a message.

**Q: If I switch tabs, does the task keep running?**
A: Yes. Tabs are purely a view switch — background tasks are unaffected. The right-hand log panel can flip between each site's live feed at any time.

**Q: How do I pause a task?**
A: Click **⏸** next to Start. The task pauses after the current image finishes downloading (files are never truncated). Click **▶** to resume.

**Q: How do I stop a task?**
A: Click **⏹**, confirm, and the task exits after the current image finishes. Files and history are kept, so the next run resumes from where you left off. Stopping Danbooru does not affect a running Yande.re task — they are fully independent.

**Q: How do I change the search tag?**
A: Click **⏹** to stop, wait until the status shows "Stopped", edit the tag, and hit Start again. No page reload is needed, and the other site's task is not affected.

**Q: I closed the browser tab — is the task still running?**
A: Closing the browser only drops the frontend connection. Flask and the download threads continue to run. Reopening the page shows current state. Killing `app.py` (Ctrl+C) does stop everything.

**Q: Can I run both sites at the same time?**
A: Yes. Danbooru and Yande.re are independent domains — running one task on each is fine. Running multiple concurrent tasks on the *same* site is discouraged (combined request rates will likely trip throttling).

**Q: How do I filter by rating?**
A: Use the rating checkboxes under the filter section. Only checked ratings are downloaded. Uncheck all or check all to disable the filter.

**Q: How do blacklist and whitelist work?**
A: Blacklist excludes posts with *any* listed tag. Whitelist keeps only posts matching the listed tags — use the AND/OR toggle to control whether *all* or *any* whitelist tags must match. Both work server-side to save bandwidth.

**Q: What is download deduplication?**
A: The Dedup mode setting controls whether posts you already downloaded are skipped. "Current query only" (default) skips posts downloaded under the same search. "Global" skips posts downloaded under any search on that site. "No skip" always re-downloads.

**Q: How do I back up my download history?**
A: Use the **Export** button in the Download History panel — it downloads a JSON file with all records. Use **Import** to restore or merge records on another machine.

**Q: Can I customize how files are named and organized?**
A: Yes. Open Settings → Downloads tab to configure path and filename templates with placeholders like `{artist}`, `{query}`, `{id}`, `{md5}`, `{date}`, `{rating}`, etc.

**Q: How do I use keyboard shortcuts?**
A: `Ctrl+Enter` to start, `Ctrl+.` to stop, `?` for help, `,` for settings. These work anywhere in the app.

---

## License

This project is released under the [MIT License](LICENSE). You are free to use, modify, and distribute it, provided that the original copyright notice is retained.

Copyright © 2026 ChuUNiMuggle
