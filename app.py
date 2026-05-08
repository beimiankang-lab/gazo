"""
Flask 后端 —— 为前端界面提供 API 接口
启动: python app.py
"""

import json
import logging
import queue
import threading
import uuid
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context

import danbooru_crawler as danbooru
import yande_crawler as yande

_BASE_DIR = Path(__file__).parent
_DIST_DIR = _BASE_DIR / "static_dist"

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

DEFAULT_DOWNLOAD_DIR = str(Path(__file__).parent / "downloads")


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


# ── 爬虫任务线程 ──────────────────────────────────────────────────────────────

def _run_danbooru(task_id: str, query: str, include_deleted: bool, output_dir: Path):
    handler = QueueHandler(task_id)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(fmt)

    pause_event = _tasks[task_id]["pause_event"]
    stop_event  = _tasks[task_id]["stop_event"]

    def log_fn(msg: str):
        _task_log(task_id, msg)

    try:
        posts = danbooru.fetch_all_posts(query, include_deleted,
                                         log_fn=log_fn,
                                         pause_event=pause_event,
                                         stop_event=stop_event)
        if stop_event.is_set():
            pass
        elif not posts:
            _task_log(task_id, "未找到任何图片")
        else:
            danbooru.process_posts(posts, query, output_dir,
                                   extra_handler=handler,
                                   pause_event=pause_event,
                                   stop_event=stop_event)
        with _tasks_lock:
            _tasks[task_id]["status"] = "stopped" if stop_event.is_set() else "done"
        _tasks[task_id]["queue"].put("__DONE__")
    except Exception as e:
        with _tasks_lock:
            _tasks[task_id]["status"] = "error"
        _task_log(task_id, f"[ERROR] 任务异常: {e}")
        _tasks[task_id]["queue"].put("__DONE__")


def _run_yande(task_id: str, query: str, output_dir: Path):
    handler = QueueHandler(task_id)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(fmt)

    pause_event = _tasks[task_id]["pause_event"]
    stop_event  = _tasks[task_id]["stop_event"]

    def log_fn(msg: str):
        _task_log(task_id, msg)

    try:
        posts = yande.fetch_all_posts(query,
                                      log_fn=log_fn,
                                      pause_event=pause_event,
                                      stop_event=stop_event)
        if stop_event.is_set():
            pass
        elif not posts:
            _task_log(task_id, "未找到任何图片")
        else:
            yande.process_posts(posts, query, output_dir,
                                extra_handler=handler,
                                pause_event=pause_event,
                                stop_event=stop_event)
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
    return jsonify({"default_dir": DEFAULT_DOWNLOAD_DIR})


@app.route("/api/start", methods=["POST"])
def api_start():
    """启动爬虫任务，返回 task_id"""
    data = request.get_json(force=True)
    site = data.get("site", "danbooru")
    query = (data.get("query") or "").strip()
    include_deleted = bool(data.get("include_deleted", False))
    output_dir = Path(data.get("output_dir") or DEFAULT_DOWNLOAD_DIR)

    if not query:
        return jsonify({"error": "搜索词不能为空"}), 400

    output_dir.mkdir(parents=True, exist_ok=True)

    task_id = uuid.uuid4().hex
    pause_event = threading.Event()
    pause_event.set()   # 默认运行状态
    stop_event = threading.Event()  # 默认未中止

    with _tasks_lock:
        _tasks[task_id] = {
            "status": "running",
            "site": site,
            "query": query,
            "queue": queue.Queue(),
            "logs": [],
            "pause_event": pause_event,
            "stop_event": stop_event,
        }

    if site == "danbooru":
        t = threading.Thread(target=_run_danbooru,
                             args=(task_id, query, include_deleted, output_dir),
                             daemon=True)
    else:
        t = threading.Thread(target=_run_yande,
                             args=(task_id, query, output_dir),
                             daemon=True)

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
            already_done = task["status"] in ("done", "error")

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
                yield f"data: {json.dumps({'done': True, 'status': final_status})}\n\n"
                break
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
        _task_log(task_id, "⏸ 任务已暂停")
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
        _task_log(task_id, "▶ 任务已继续")
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
        _task_log(task_id, "⏹ 任务正在中止...")
    return jsonify({"status": task["status"]})


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


if __name__ == "__main__":
    print("启动 Web 界面: http://127.0.0.1:5000")
    app.run(debug=True, threaded=True)
