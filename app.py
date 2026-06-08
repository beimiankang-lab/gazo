"""
Flask 后端 —— 为前端界面提供 API 接口
启动: python app.py
"""

import json
import logging
import os
import queue
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context

import danbooru_crawler as danbooru
import yande_crawler as yande
from naming import parse_filters

import sys as _sys

def _get_base_dir() -> Path:
    """用户数据目录：exe 旁边（开发时为 app.py 旁边）"""
    if getattr(_sys, 'frozen', False):
        return Path(_sys.executable).parent
    return Path(__file__).parent

def _get_dist_dir() -> Path:
    """前端静态文件目录：打包时在 _MEIPASS，开发时在 app.py 旁边"""
    if getattr(_sys, 'frozen', False):
        return Path(_sys._MEIPASS) / "static_dist"  # type: ignore[attr-defined]
    return Path(__file__).parent / "static_dist"

_BASE_DIR = _get_base_dir()
_DIST_DIR = _get_dist_dir()
_CONFIG_PATH = _BASE_DIR / "gazo_config.json"


def _load_gazo_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_gazo_config(data: dict) -> None:
    existing = _load_gazo_config()
    existing.update(data)
    _CONFIG_PATH.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")

if not (_DIST_DIR / "index.html").is_file():
    raise RuntimeError(
        "未找到前端构建产物 static_dist/index.html。\n"
        "请先进入 frontend/ 运行 `npm install && npm run build`。"
    )

app = Flask(
    __name__,
    static_folder=str(_DIST_DIR),
    static_url_path="",
)

# 全局任务状态字典
# 结构：{task_id: {
#   "status": "running"|"paused"|"done"|"error"|"stopped",
#   "site":   "danbooru"|"yande",
#   "query":  str,
#   "queue":  Queue,       # 实时日志行
#   "logs":   list[str],   # 全量历史日志（用于切换后回放）
#   "pause_event": Event,  # set=运行, clear=暂停
#   "stop_event":  Event,  # set=请求中止
# }}
_tasks: dict[str, dict] = {}
_tasks_lock = threading.Lock()

DEFAULT_DOWNLOAD_DIR = str(_BASE_DIR / "downloads")

# 浏览器存活心跳
_last_heartbeat = time.time()
_heartbeat_lock = threading.Lock()
_HEARTBEAT_TIMEOUT = 10  # 10 秒无心跳则认为所有浏览器已关闭，退出 exe


def _watchdog():
    """后台心跳看门狗：所有浏览器关闭后自动退出"""
    while True:
        time.sleep(1)
        with _heartbeat_lock:
            if time.time() - _last_heartbeat > _HEARTBEAT_TIMEOUT:
                # 双保险：确认是打包成 exe 才真正退出（开发时不要自动退）
                if getattr(_sys, 'frozen', False) or os.environ.get('GAZO_KILL_ON_EXIT'):
                    os._exit(0)
                # 开发模式下仅打日志不退出
                print(f"[watchdog] {_HEARTBEAT_TIMEOUT}s 无浏览器心跳，打包版已退出，开发版忽略")
                break


threading.Thread(target=_watchdog, daemon=True).start()


# ── 日志队列 Handler ──────────────────────────────────────────────────────────

class QueueHandler(logging.Handler):
    """将日志记录同时写入实时 Queue 和历史列表"""

    def __init__(self, task_id: str):
        super().__init__()
        self.task_id = task_id

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            with _tasks_lock:
                task = _tasks.get(self.task_id)
            if task:
                task["logs"].append(msg)
                task["queue"].put(msg)
        except Exception:
            pass


# ── 任务日志写入辅助 ──────────────────────────────────────────────────────────

def _task_log(task_id: str, msg: str):
    """将纯文本日志写入任务的历史列表和实时队列"""
    with _tasks_lock:
        task = _tasks.get(task_id)
    if task:
        task["logs"].append(msg)
        task["queue"].put(msg)


def _wait_for_task_resume(task: dict) -> bool:
    pause_event = task.get("pause_event")
    stop_event = task.get("stop_event")
    while pause_event is not None and not pause_event.is_set():
        if stop_event is not None and stop_event.is_set():
            return False
        time.sleep(0.2)
    return not (stop_event is not None and stop_event.is_set())


# ── 爬虫任务线程 ──────────────────────────────────────────────────────────────

def _run_danbooru(task_id: str, query: str, record_query: str, include_deleted: bool, output_dir: Path,
                  template_preset: str = "default", template_custom: str = "",
                  path_template: str = "", file_template: str = "",
                  filters_raw: dict | None = None,
                  max_posts: int | None = None,
                  download_concurrency: int = 4,
                  whitelist_tags: list[str] | None = None,
                  whitelist_mode: str = "and",
                  include_no_author: bool = False,
                  auto_retry: bool = False,
                  dedup_mode: str = "local"):
    handler = QueueHandler(task_id)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(fmt)

    pause_event = _tasks[task_id]["pause_event"]
    stop_event  = _tasks[task_id]["stop_event"]
    filters     = parse_filters(filters_raw)

    def log_fn(msg: str):
        _task_log(task_id, msg)

    def _on_progress(current, total):
        q = _tasks[task_id]["queue"]
        _tasks[task_id]["progress"] = {"current": current, "total": total}
        q.put({"type": "progress", "current": current, "total": total})

    def _on_fail(post_id, error):
        q = _tasks[task_id]["queue"]
        q.put({"type": "fail", "post_id": post_id, "error": error})

    try:
        posts = danbooru.fetch_all_posts(query, include_deleted,
                                         log_fn=log_fn,
                                         pause_event=pause_event,
                                         stop_event=stop_event,
                                         max_posts=max_posts,
                                         whitelist_tags=whitelist_tags,
                                         whitelist_mode=whitelist_mode,
                                         include_no_author=include_no_author)
        if stop_event.is_set():
            pass
        elif not posts:
            _task_log(task_id, "未找到任何图片")
        else:
            failed = danbooru.process_posts(posts, record_query, output_dir, record_query,
                                   extra_handler=handler,
                                   pause_event=pause_event,
                                   stop_event=stop_event,
                                   template_preset=template_preset,
                                   template_custom=template_custom,
                                   path_template=path_template,
                                   file_template=file_template,
                                   filters=filters,
                                   on_progress=_on_progress,
                                   on_fail=_on_fail,
                                   download_concurrency=download_concurrency,
                                   dedup_mode=dedup_mode)
            with _tasks_lock:
                _tasks[task_id]["failed_posts"] = failed
            if auto_retry and failed and not stop_event.is_set():
                still_failed = _retry_failed_posts(task_id, _tasks[task_id])
                with _tasks_lock:
                    _tasks[task_id]["failed_posts"] = still_failed
        with _tasks_lock:
            _tasks[task_id]["status"] = "stopped" if stop_event.is_set() else "done"
        _tasks[task_id]["queue"].put("__DONE__")
    except Exception as e:
        with _tasks_lock:
            _tasks[task_id]["status"] = "error"
        _task_log(task_id, f"[ERROR] 任务异常: {e}")
        _tasks[task_id]["queue"].put("__DONE__")


def _run_yande(task_id: str, query: str, record_query: str, output_dir: Path,
               template_preset: str = "default", template_custom: str = "",
               path_template: str = "", file_template: str = "",
               filters_raw: dict | None = None,
               max_posts: int | None = None,
               ratings: list[str] | None = None,
               download_concurrency: int = 4,
               whitelist_tags: list[str] | None = None,
               whitelist_mode: str = "and",
               include_no_author: bool = False,
               auto_retry: bool = False,
               dedup_mode: str = "local"):
    handler = QueueHandler(task_id)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(fmt)

    pause_event = _tasks[task_id]["pause_event"]
    stop_event  = _tasks[task_id]["stop_event"]
    filters     = parse_filters(filters_raw)

    def log_fn(msg: str):
        _task_log(task_id, msg)

    def _on_progress(current, total):
        q = _tasks[task_id]["queue"]
        _tasks[task_id]["progress"] = {"current": current, "total": total}
        q.put({"type": "progress", "current": current, "total": total})

    def _on_fail(post_id, error):
        q = _tasks[task_id]["queue"]
        q.put({"type": "fail", "post_id": post_id, "error": error})

    try:
        posts = yande.fetch_all_posts(query,
                                      log_fn=log_fn,
                                      pause_event=pause_event,
                                      stop_event=stop_event,
                                      max_posts=max_posts,
                                      ratings=ratings,
                                      whitelist_tags=whitelist_tags,
                                      whitelist_mode=whitelist_mode,
                                      include_no_author=include_no_author)
        if stop_event.is_set():
            pass
        elif not posts:
            _task_log(task_id, "未找到任何图片")
        else:
            failed = yande.process_posts(posts, record_query, output_dir, record_query,
                                extra_handler=handler,
                                pause_event=pause_event,
                                stop_event=stop_event,
                                template_preset=template_preset,
                                template_custom=template_custom,
                                path_template=path_template,
                                file_template=file_template,
                                filters=filters,
                                on_progress=_on_progress,
                                on_fail=_on_fail,
                                download_concurrency=download_concurrency,
                                dedup_mode=dedup_mode)
            with _tasks_lock:
                _tasks[task_id]["failed_posts"] = failed
            if auto_retry and failed and not stop_event.is_set():
                still_failed = _retry_failed_posts(task_id, _tasks[task_id])
                with _tasks_lock:
                    _tasks[task_id]["failed_posts"] = still_failed
        with _tasks_lock:
            _tasks[task_id]["status"] = "stopped" if stop_event.is_set() else "done"
        _tasks[task_id]["queue"].put("__DONE__")
    except Exception as e:
        with _tasks_lock:
            _tasks[task_id]["status"] = "error"
        _task_log(task_id, f"[ERROR] 任务异常: {e}")
        _tasks[task_id]["queue"].put("__DONE__")


# ── 路由 ──────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(str(_DIST_DIR), "index.html")


@app.route("/api/config")
def api_config():
    cfg = _load_gazo_config()
    return jsonify({
        "default_dir": DEFAULT_DOWNLOAD_DIR,
        "danbooru_login_set": bool(cfg.get("danbooru_login")),
    })


@app.route("/api/save_config", methods=["POST"])
def api_save_config():
    data = request.get_json(force=True)
    _save_gazo_config({
        "danbooru_login":   (data.get("danbooru_login") or "").strip(),
        "danbooru_api_key": (data.get("danbooru_api_key") or "").strip(),
    })
    return jsonify({"ok": True})


@app.route("/api/test_danbooru", methods=["POST"])
def api_test_danbooru():
    import requests as req
    data = request.get_json(force=True)
    login   = (data.get("danbooru_login") or "").strip()
    api_key = (data.get("danbooru_api_key") or "").strip()
    auth = (login, api_key) if login and api_key else None
    try:
        r = req.get(
            "https://danbooru.donmai.us/profile.json",
            auth=auth, timeout=10,
            headers={"User-Agent": "danbooru-crawler/1.0 (personal use)"},
        )
        if r.status_code == 200:
            return jsonify({"ok": True, "username": r.json().get("name", "")})
        return jsonify({"ok": False, "error": f"HTTP {r.status_code}"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/start", methods=["POST"])
def api_start():
    """启动爬虫任务，返回 task_id"""
    data = request.get_json(force=True)
    site = data.get("site", "danbooru")
    query = (data.get("query") or "").strip()
    raw_query = (data.get("raw_query") or query).strip() or query
    include_deleted = bool(data.get("include_deleted", False))
    output_dir = Path(data.get("output_dir") or DEFAULT_DOWNLOAD_DIR)
    template_preset = data.get("template_preset", "default")
    template_custom = data.get("template_custom", "")
    path_template = data.get("path_template", "") or ""
    file_template = data.get("file_template", "") or ""
    filters_raw = data.get("filters") or None
    ratings: list[str] | None = data.get("ratings")  # Yande.re 多评级分次获取
    raw_concurrency = data.get("download_concurrency", 4)
    whitelist_tags: list[str] = [t.strip() for t in (data.get("whitelist_tags") or []) if isinstance(t, str) and t.strip()]
    whitelist_mode: str = data.get("whitelist_mode", "and")
    if whitelist_mode not in ("and", "or"):
        whitelist_mode = "and"
    include_no_author: bool = bool(data.get("include_no_author", False))
    auto_retry: bool = bool(data.get("auto_retry", False))
    dedup_mode = data.get("dedup_mode", "local")
    if dedup_mode not in ("none", "local", "global"):
        dedup_mode = "local"
    # max_posts: None / 0 / 负数都视为不限制
    raw_max = data.get("max_posts")
    try:
        max_posts: int | None = int(raw_max) if raw_max not in (None, "", 0) else None
        if max_posts is not None and max_posts <= 0:
            max_posts = None
    except (TypeError, ValueError):
        max_posts = None

    download_concurrency = 0
    try:
        download_concurrency = int(raw_concurrency)
    except (TypeError, ValueError):
        return jsonify({"error": "download_concurrency must be an integer"}), 400
    if not 1 <= download_concurrency <= 8:
        return jsonify({"error": "download_concurrency must be between 1 and 8"}), 400

    if not query:
        return jsonify({"error": "搜索词不能为空"}), 400

    output_dir.mkdir(parents=True, exist_ok=True)

    task_id = uuid.uuid4().hex
    pause_event = threading.Event()
    pause_event.set()   # 默认运行状态
    stop_event = threading.Event()  # 默认未中止

    with _tasks_lock:
        for existing in _tasks.values():
            if existing["site"] == site and existing["status"] in ("running", "paused", "stopping"):
                return jsonify({"error": f"{site} already has an active task"}), 409
        _tasks[task_id] = {
            "status": "running",
            "site": site,
            "query": query,
            "raw_query": raw_query,
            "queue": queue.Queue(),
            "logs": [],
            "pause_event": pause_event,
            "stop_event": stop_event,
            "progress": {"current": 0, "total": 0},
            "failed_posts": [],
            "output_dir": str(output_dir),
            "download_concurrency": download_concurrency,
        }

    if site == "danbooru":
        t = threading.Thread(target=_run_danbooru,
                             args=(task_id, query, raw_query, include_deleted, output_dir,
                                   template_preset, template_custom,
                                   path_template, file_template, filters_raw,
                                   max_posts, download_concurrency,
                                   whitelist_tags, whitelist_mode, include_no_author, auto_retry, dedup_mode),
                             daemon=True)
    else:
        t = threading.Thread(target=_run_yande,
                             args=(task_id, query, raw_query, output_dir,
                                   template_preset, template_custom,
                                   path_template, file_template, filters_raw,
                                   max_posts, ratings, download_concurrency,
                                   whitelist_tags, whitelist_mode, include_no_author, auto_retry, dedup_mode),
                             daemon=True)

    _task_log(task_id, f"下载并发数已设置为 {download_concurrency}")

    t.start()
    return jsonify({"task_id": task_id})


@app.route("/api/logs/<task_id>")
def api_logs(task_id: str):
    """
    SSE 流：先回放历史日志，再实时推送新日志。
    客户端携带 ?offset=N 可跳过已读的前 N 条历史记录。
    """
    with _tasks_lock:
        task = _tasks.get(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404

    offset = int(request.args.get("offset", 0))

    def generate():
        # 1. 先回放请求时已有的历史日志（跳过已读部分）
        with _tasks_lock:
            history = list(task["logs"][offset:])
            already_done = task["status"] in ("done", "error", "stopped")

        for msg in history:
            yield f"data: {json.dumps({'log': msg})}\n\n"

        if already_done:
            yield f"data: {json.dumps({'done': True, 'status': task['status']})}\n\n"
            return

        # 2. 继续实时推送
        log_queue: queue.Queue = task["queue"]
        while True:
            try:
                msg = log_queue.get(timeout=30)
            except queue.Empty:
                yield "data: {\"heartbeat\":1}\n\n"
                continue

            if msg == "__DONE__":
                with _tasks_lock:
                    final_status = task["status"]
                    final_failed = task.get("failed_posts", [])
                yield f"data: {json.dumps({'done': True, 'status': final_status, 'failed_posts': final_failed})}\n\n"
                break
            if isinstance(msg, dict):
                yield f"data: {json.dumps(msg)}\n\n"
            else:
                yield f"data: {json.dumps({'log': msg})}\n\n"

    return Response(stream_with_context(generate()),
                    mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no"})


@app.route("/api/task_status/<task_id>")
def api_task_status(task_id: str):
    """查询任务状态和日志条数（用于重连时确定 offset）"""
    with _tasks_lock:
        task = _tasks.get(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    return jsonify({
        "status": task["status"],
        "log_count": len(task["logs"]),
        "site": task["site"],
        "query": task["query"],
        "raw_query": task.get("raw_query", task["query"]),
        "progress": task.get("progress", {"current": 0, "total": 0}),
        "failed_posts": task.get("failed_posts", []),
    })


@app.route("/api/pause", methods=["POST"])
def api_pause():
    """暂停指定任务"""
    data = request.get_json(force=True)
    task_id = data.get("task_id", "")
    with _tasks_lock:
        task = _tasks.get(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    if task["status"] == "running":
        task["pause_event"].clear()   # 清除 event → 爬虫在下一个 wait() 处阻塞
        task["status"] = "paused"
        _task_log(task_id, "已暂停，新的下载任务不会再启动，进行中的下载会在下一个检查点停下")
    return jsonify({"status": task["status"]})


@app.route("/api/resume", methods=["POST"])
def api_resume():
    """继续指定任务"""
    data = request.get_json(force=True)
    task_id = data.get("task_id", "")
    with _tasks_lock:
        task = _tasks.get(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    if task["status"] == "paused":
        task["status"] = "running"
        task["pause_event"].set()     # 重新 set → 爬虫从 wait() 处继续
        _task_log(task_id, "已继续，恢复投放下载任务")
    return jsonify({"status": task["status"]})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    """
    中止指定任务。set stop_event；
    若任务处于暂停状态，同时 set pause_event 唤醒，避免卡在 wait() 无法退出。
    """
    data = request.get_json(force=True)
    task_id = data.get("task_id", "")
    with _tasks_lock:
        task = _tasks.get(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    if task["status"] in ("running", "paused"):
        task["stop_event"].set()
        task["pause_event"].set()   # 确保暂停中的任务能立即看到 stop 信号
        task["status"] = "stopping"
        _task_log(task_id, "已发送中止信号，等待进行中的下载退出，不会再启动新的下载任务")
    return jsonify({"status": task["status"]})


def _retry_failed_posts(task_id: str, task: dict) -> list[dict]:
    """重试任务中所有失败帖子，返回仍失败的列表。同步执行，不创建线程。"""
    import danbooru_crawler as dc
    import yande_crawler as yc

    failed_posts = task.get("failed_posts", [])
    if not failed_posts:
        return []

    site = task["site"]
    output_dir = Path(task["output_dir"])
    pause_event = task["pause_event"]
    stop_event = task["stop_event"]
    crawler = dc if site == "danbooru" else yc

    record_path = output_dir / crawler.RECORD_FILENAME
    raw_query = task.get("raw_query", "")
    downloaded = crawler.load_downloaded(record_path, raw_query)

    total = len(failed_posts)
    _task_log(task_id, f"[自动重试] 开始重试 {total} 张失败的下载...")
    task["progress"] = {"current": 0, "total": total}
    new_failed: list[dict] = []

    for i, item in enumerate(failed_posts):
        if not _wait_for_task_resume(task):
            new_failed.extend(failed_posts[i:])
            break
        if stop_event.is_set():
            new_failed.append(item)
            continue

        post_id = item["post_id"]
        file_url = item["file_url"]
        filepath = Path(item["filepath"])
        _task_log(task_id, f"[自动重试 {i+1}/{total}] id={post_id} — {filepath.name}")

        retry_kwargs = {"timeout": 120} if site == "yande" else {}
        success = False
        for attempt in range(1, 4):
            if stop_event.is_set():
                break
            success = crawler.download_image(
                file_url, filepath, logging.getLogger(site),
                pause_event=pause_event, stop_event=stop_event,
                **retry_kwargs,
            )
            if success:
                break
            if attempt < 3:
                _task_log(task_id, f"[自动重试 {i+1}/{total}] 第{attempt}次失败，1s后重试...")
                time.sleep(1)

        current = i + 1
        task["progress"] = {"current": current, "total": total}
        task["queue"].put({"type": "progress", "current": current, "total": total})

        if stop_event.is_set():
            new_failed.append(item)
            continue
        if not success:
            new_failed.append(item)
            task["queue"].put({"type": "fail", "post_id": post_id, "error": "retry failed"})
            _task_log(task_id, f"[自动重试 {current}/{total}] 仍失败 — {filepath.name}")
        else:
            downloaded.add(post_id)
            crawler.save_downloaded(record_path, raw_query, post_id)
            _task_log(task_id, f"[自动重试 {current}/{total}] 成功 — {filepath.name}")

    _task_log(task_id, f"[自动重试] 完成：成功 {total - len(new_failed)}，仍失败 {len(new_failed)}")
    return new_failed


@app.route("/api/retry_failed", methods=["POST"])
def api_retry_failed():
    """
    重试下载当前任务中所有失败的帖子（手动触发）。
    异步执行，在单独线程中通过 _retry_failed_posts 完成。
    """
    data = request.get_json(force=True)
    task_id = data.get("task_id", "")
    with _tasks_lock:
        task = _tasks.get(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404

    failed_posts = task.get("failed_posts", [])
    if not failed_posts:
        return jsonify({"error": "没有失败的下载"}), 400

    task["status"] = "running"
    task["failed_posts"] = []
    task["stop_event"].clear()
    task["pause_event"].set()
    total = len(failed_posts)

    def _retry_thread():
        still_failed = _retry_failed_posts(task_id, task)
        with _tasks_lock:
            task["failed_posts"] = still_failed
            task["status"] = "stopped" if task["stop_event"].is_set() else "done"
        task["queue"].put("__DONE__")

    threading.Thread(target=_retry_thread, daemon=True).start()
    return jsonify({"ok": True, "retry_count": total})


@app.route("/api/records", methods=["GET"])
def api_records():
    """获取两个爬虫的下载记录"""
    output_dir = Path(request.args.get("output_dir") or DEFAULT_DOWNLOAD_DIR)
    danbooru_record = danbooru._load_record(output_dir / danbooru.RECORD_FILENAME)
    yande_record = yande._load_record(output_dir / yande.RECORD_FILENAME)
    return jsonify({
        "danbooru": {q: len(ids) for q, ids in danbooru_record.items()},
        "yande": {q: len(ids) for q, ids in yande_record.items()},
    })


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """重置指定爬虫的某个搜索词记录"""
    data = request.get_json(force=True)
    site = data.get("site", "danbooru")
    query = (data.get("query") or "").strip()
    output_dir = Path(data.get("output_dir") or DEFAULT_DOWNLOAD_DIR)

    if not query:
        return jsonify({"error": "搜索词不能为空"}), 400

    if site == "danbooru":
        record_path = output_dir / danbooru.RECORD_FILENAME
        danbooru.reset_downloaded(record_path, query)
    else:
        record_path = output_dir / yande.RECORD_FILENAME
        yande.reset_downloaded(record_path, query)

    return jsonify({"ok": True})


@app.route("/api/tasks")
def api_tasks():
    """获取所有活跃任务列表，用于网页刷新后自动重连"""
    with _tasks_lock:
        result = []
        for task_id, task in _tasks.items():
            if task["status"] not in ("running", "paused", "stopping"):
                continue
            result.append({
                "task_id": task_id,
                "site": task["site"],
                "query": task["query"],
                "raw_query": task.get("raw_query", task["query"]),
                "status": task["status"],
                "log_count": len(task["logs"]),
                "progress": task.get("progress", {"current": 0, "total": 0}),
                "failed_count": len(task.get("failed_posts", [])),
            })
        return jsonify(result)


@app.route("/api/heartbeat", methods=["POST"])
def api_heartbeat():
    """浏览器存活心跳：前端定期上报，超时则 exe 自动退出"""
    global _last_heartbeat
    with _heartbeat_lock:
        _last_heartbeat = time.time()
    return jsonify({"ok": True})


@app.route("/api/preview_template", methods=["POST"])
def api_preview_template():
    """
    用一个示例 PostCtx 渲染拆分模板，返回相对路径字符串。
    前端编辑模板时实时调用，确保和服务端渲染结果一致。
    """
    from naming import PostCtx, render_split_path
    data = request.get_json(force=True)
    site = data.get("site") or "danbooru"
    path_tpl = data.get("path_template", "") or ""
    file_tpl = data.get("file_template", "") or ""

    ctx = PostCtx(
        site=site,
        post_id=1234567,
        query="touhou",
        artists=["zun"],
        characters=["hakurei_reimu"],
        rating="s",
        ext="jpg",
        date="2025-04-15",
        md5="abcdef0123456789abcdef0123456789",
        copyrights=["touhou"],
        score=42,
    )

    try:
        full = render_split_path(path_tpl, file_tpl, ctx, 1, Path("downloads"))
        # 转成 POSIX 风格，跨平台展示一致
        return jsonify({"ok": True, "preview": full.as_posix()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ── 下载历史导出 / 导入 ────────────────────────────────────────────────────────

_EXPORT_FORMAT_VERSION = 1


@app.route("/api/export_records")
def api_export_records():
    """
    导出两个站点的下载记录合并为一个 JSON 文件。
    格式：
      { "version": 1, "exported_at": "...", "danbooru": {...}, "yande": {...} }
    """
    output_dir = Path(request.args.get("output_dir") or DEFAULT_DOWNLOAD_DIR)
    danbooru_record = danbooru._load_record(output_dir / danbooru.RECORD_FILENAME)
    yande_record = yande._load_record(output_dir / yande.RECORD_FILENAME)

    payload = {
        "version": _EXPORT_FORMAT_VERSION,
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "danbooru": danbooru_record,
        "yande": yande_record,
    }
    filename = f"gazo-records-{time.strftime('%Y%m%d-%H%M%S')}.json"
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return Response(
        body,
        mimetype="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _merge_records(existing: dict[str, list[int]], incoming: dict) -> tuple[dict[str, list[int]], int, int]:
    """
    将 incoming 合并到 existing（按搜索词分组，ID 取并集去重）。
    返回 (merged, added_queries, added_ids)。
    """
    merged = {q: list(ids) for q, ids in existing.items()}
    added_queries = 0
    added_ids = 0
    for query, raw_ids in (incoming or {}).items():
        if not isinstance(query, str) or not isinstance(raw_ids, list):
            continue
        # 过滤非整数 ID（防御外部数据）
        new_ids = {int(x) for x in raw_ids if isinstance(x, (int, float)) and int(x) > 0}
        if not new_ids:
            continue
        if query not in merged:
            merged[query] = []
            added_queries += 1
        before = set(merged[query])
        delta = new_ids - before
        added_ids += len(delta)
        merged[query] = sorted(before | new_ids)
    return merged, added_queries, added_ids


@app.route("/api/import_records", methods=["POST"])
def api_import_records():
    """
    导入下载记录，合并到现有 `.downloaded_*.json`。
    Body: 直接上传 JSON 文件内容（multipart/form-data 字段名 file）。
    或: { "data": {...}, "output_dir": "..." } 形式的 JSON。
    """
    output_dir = Path(request.args.get("output_dir") or DEFAULT_DOWNLOAD_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    payload: dict | None = None
    if "file" in request.files:
        try:
            payload = json.loads(request.files["file"].read().decode("utf-8"))
        except Exception as e:
            return jsonify({"error": f"无法解析文件: {e}"}), 400
    else:
        try:
            body = request.get_json(force=True) or {}
            payload = body.get("data") or body
            if body.get("output_dir"):
                output_dir = Path(body["output_dir"])
                output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return jsonify({"error": f"无法解析请求体: {e}"}), 400

    if not isinstance(payload, dict):
        return jsonify({"error": "导入数据格式错误"}), 400

    incoming_d = payload.get("danbooru", {})
    incoming_y = payload.get("yande", {})
    if not isinstance(incoming_d, dict) or not isinstance(incoming_y, dict):
        return jsonify({"error": "导入数据缺少 danbooru / yande 字段或格式错误"}), 400

    d_path = output_dir / danbooru.RECORD_FILENAME
    y_path = output_dir / yande.RECORD_FILENAME
    d_existing = danbooru._load_record(d_path)
    y_existing = yande._load_record(y_path)

    d_merged, d_new_q, d_new_id = _merge_records(d_existing, incoming_d)
    y_merged, y_new_q, y_new_id = _merge_records(y_existing, incoming_y)

    danbooru._save_record(d_path, d_merged)
    yande._save_record(y_path, y_merged)

    return jsonify({
        "ok": True,
        "danbooru": {"new_queries": d_new_q, "new_ids": d_new_id, "total_queries": len(d_merged)},
        "yande":    {"new_queries": y_new_q, "new_ids": y_new_id, "total_queries": len(y_merged)},
    })


if __name__ == "__main__":
    import sys
    import webbrowser
    import threading as _t

    port = int(os.environ.get("GAZO_PORT", "5173"))
    url = f"http://127.0.0.1:{port}"
    print(f"启动 Web 界面: {url}")

    # 打包成 exe 时 debug=True 会导致重启循环，必须关掉
    is_frozen = getattr(sys, 'frozen', False)

    def _open_browser():
        import time
        time.sleep(1.2)
        webbrowser.open(url)

    if is_frozen:
        _t.Thread(target=_open_browser, daemon=True).start()

    app.run(debug=not is_frozen, threaded=True, port=port)
