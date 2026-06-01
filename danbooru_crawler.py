"""
danbooru.donmai.us 图片爬虫
用法: python danbooru_crawler.py
或通过 app.py 前端界面调用
"""

import os
import re
import time
import json
import logging
import threading
import requests
from pathlib import Path
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from naming import PostCtx, Filters, render_path
from download_runtime import AdaptiveConcurrency, wait_for_resume

# 加载项目根目录的 .env 文件到环境变量（若存在）
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

# ── 站点基础配置 ──────────────────────────────────────────────────────────────
BASE_URL = "https://danbooru.donmai.us"
HEADERS = {
    # Danbooru 要求 User-Agent 包含联系方式
    "User-Agent": "danbooru-crawler/1.0 (personal use)"
}

# 下载记录文件名（与 yande 分开，防止互相覆盖）
RECORD_FILENAME = ".downloaded_danbooru.json"
LOG_FILENAME = "download.log"

def get_auth() -> tuple[str, str] | None:
    """读取凭据：gazo_config.json > 环境变量，每次调用时读取以支持运行时更新"""
    try:
        cfg_path = Path(__file__).parent / "gazo_config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
        login   = cfg.get("danbooru_login")   or os.environ.get("DANBOORU_LOGIN", "")
        api_key = cfg.get("danbooru_api_key") or os.environ.get("DANBOORU_API_KEY", "")
    except Exception:
        login   = os.environ.get("DANBOORU_LOGIN", "")
        api_key = os.environ.get("DANBOORU_API_KEY", "")
    return (login, api_key) if login and api_key else None


# ── 日志 ──────────────────────────────────────────────────────────────────────

def setup_logger(output_dir: Path, extra_handler: logging.Handler | None = None) -> logging.Logger:
    """
    初始化日志，同时输出到控制台和文件。
    extra_handler: 可传入额外的 Handler（如前端实时日志队列 Handler）。
    """
    logger = logging.getLogger("danbooru")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    # 写入日志文件，记录所有级别
    fh = logging.FileHandler(output_dir / LOG_FILENAME, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # 控制台只显示 INFO 及以上
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # 前端实时日志 Handler（可选）
    if extra_handler:
        extra_handler.setLevel(logging.DEBUG)
        extra_handler.setFormatter(fmt)
        logger.addHandler(extra_handler)

    return logger


# ── 下载记录（按搜索词分组：{"query": [id1, id2, ...]}） ─────────────────────

def _load_record(record_path: Path) -> dict[str, list[int]]:
    """从 JSON 文件加载完整下载记录"""
    if record_path.exists():
        try:
            with open(record_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_record(record_path: Path, record: dict[str, list[int]]) -> None:
    """将完整下载记录写回 JSON 文件"""
    with open(record_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)


def load_downloaded(record_path: Path, query: str) -> set[int]:
    """加载指定搜索词已下载的帖子 ID 集合"""
    record = _load_record(record_path)
    return set(record.get(query, []))


def save_downloaded(record_path: Path, query: str, downloaded: set[int]) -> None:
    """将指定搜索词的已下载 ID 集合持久化"""
    record = _load_record(record_path)
    record[query] = sorted(downloaded)
    _save_record(record_path, record)


def reset_downloaded(record_path: Path, query: str) -> None:
    """清空指定搜索词的下载记录"""
    record = _load_record(record_path)
    if query in record:
        del record[query]
        _save_record(record_path, record)
        print(f"已清空搜索词 '{query}' 的下载记录")
    else:
        print(f"搜索词 '{query}' 没有下载记录，无需重置")
    if record:
        print(f"剩余记录的搜索词: {', '.join(record.keys())}")


def list_records(record_path: Path) -> None:
    """列出所有有记录的搜索词及已下载数量"""
    record = _load_record(record_path)
    if not record:
        print("暂无下载记录")
        return
    print("当前下载记录：")
    for q, ids in record.items():
        print(f"  {q}: {len(ids)} 张")


# ── 帖子获取 ──────────────────────────────────────────────────────────────────

_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504, 520, 522, 524}


def fetch_posts_page(query: str, page: int, limit: int = 200,
                     max_retries: int = 5, log_fn=None) -> list[dict]:
    """
    获取一页搜索结果，遇到瞬时网络错误时自动重试。
    Danbooru 免费账号每页最多 200 条，Gold+ 账号可更高。
    """
    url = f"{BASE_URL}/posts.json"
    params = {"tags": query, "page": page, "limit": limit}
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, headers=HEADERS,
                                auth=get_auth(), timeout=30)
            if resp.status_code in _RETRYABLE_STATUS:
                # 服务端瞬时错误：当作可重试异常处理
                raise requests.HTTPError(
                    f"HTTP {resp.status_code}", response=resp)
            resp.raise_for_status()
            return resp.json()
        except (requests.ConnectionError, requests.Timeout,
                requests.HTTPError) as e:
            last_exc = e
            # 非可重试的 HTTP 错误（如 401/403/404）直接抛
            if isinstance(e, requests.HTTPError):
                code = getattr(e.response, "status_code", None)
                if code is not None and code not in _RETRYABLE_STATUS:
                    raise
            if attempt >= max_retries:
                break
            # 指数退避：2s, 4s, 8s, 16s, 32s（上限）
            backoff = min(2 ** attempt, 32)
            if log_fn:
                log_fn(f"  第 {page} 页第 {attempt} 次请求失败 ({e})，{backoff}s 后重试...")
            time.sleep(backoff)
    # 重试用尽后抛出最后一次异常
    raise last_exc if last_exc else RuntimeError("fetch_posts_page failed")


def fetch_all_posts(query: str, include_deleted: bool,
                    log_fn=print, pause_event=None, stop_event=None,
                    max_posts: int | None = None) -> list[dict]:
    """
    分页获取所有搜索结果。
    若 include_deleted=True，额外搜索 'query status:deleted' 并合并去重。
    log_fn: 日志输出函数，默认 print，前端调用时可传入队列写入函数。
    pause_event: threading.Event，被清除时任务会在翻页前阻塞等待（暂停）。
    stop_event: threading.Event，被 set 时函数会尽快返回已搜索到的结果（中止）。
    """
    # 构建查询列表：
    # - 正常查询显式排除已删除（-status:deleted），避免账号设置中"显示已删除帖子"
    #   导致正常查询已包含已删除帖子，从而让第二个 status:deleted 查询被全部去重
    # - 如需下载已删除则追加 status:deleted 查询
    queries = [f"{query} -status:deleted"]
    if include_deleted:
        queries.append(f"{query} status:deleted")

    seen_ids: set[int] = set()   # 去重用的已见 ID 集合
    all_posts: list[dict] = []
    normal_count = 0             # 正常帖子计数
    deleted_count = 0            # 已删除帖子计数

    log_fn("正在准备搜索任务...")
    log_fn(f"搜索词: {query}")
    if max_posts is not None and max_posts > 0:
        log_fn(f"已开启下载上限，本次最多处理 {max_posts} 张")

    for q in queries:
        if stop_event is not None and stop_event.is_set():
            log_fn("收到中止信号，停止搜索")
            return all_posts

        is_deleted_query = "status:deleted" in q and "-status:deleted" not in q
        label = "(已删除)" if is_deleted_query else "(正常)"
        page = 1
        consecutive_fails = 0
        MAX_CONSECUTIVE_FAILS = 3
        log_fn(f"正在搜索 {label}: {q}")
        while True:
            # 中止优先于暂停：中止时直接退出，不等暂停解除
            if stop_event is not None and stop_event.is_set():
                log_fn("收到中止信号，停止搜索")
                return all_posts
            # 暂停检查：event 被清除时此处阻塞，直到 resume 重新 set
            if pause_event is not None and not wait_for_resume(pause_event, stop_event):
                log_fn("收到中止信号，停止搜索")
                return all_posts

            log_fn(f"  获取第 {page} 页...")
            try:
                posts = fetch_posts_page(q, page, log_fn=log_fn)
                consecutive_fails = 0
            except Exception as e:
                consecutive_fails += 1
                log_fn(f"  第 {page} 页重试用尽 ({e})，跳过该页继续 (连续失败 {consecutive_fails}/{MAX_CONSECUTIVE_FAILS})")
                if consecutive_fails >= MAX_CONSECUTIVE_FAILS:
                    log_fn(f"  连续 {MAX_CONSECUTIVE_FAILS} 页全部失败，疑似网络/节点问题，停止当前查询。建议更换网络后重试。")
                    break
                page += 1
                time.sleep(3)
                continue

            if not posts:
                log_fn("无更多结果")
                break

            # 过滤掉已见帖子，实现跨查询去重
            new_posts = [p for p in posts if p.get("id") not in seen_ids]
            if max_posts is not None:
                remain = max_posts - len(all_posts)
                if remain <= 0:
                    log_fn(f"已达到上限 {max_posts} 张，停止继续翻页")
                    break
                if len(new_posts) > remain:
                    new_posts = new_posts[:remain]
            for p in new_posts:
                seen_ids.add(p["id"])
            all_posts.extend(new_posts)

            # 按查询类型累计计数
            if is_deleted_query:
                deleted_count += len(new_posts)
            else:
                normal_count += len(new_posts)

            log_fn(f"  获取到 {len(posts)} 条，新增 {len(new_posts)} 条")

            if max_posts is not None and len(all_posts) >= max_posts:
                log_fn(f"已累计 {len(all_posts)} 张，达到上限，准备进入下载")
                break

            # 返回条数不足一页说明已到末尾
            if len(posts) < 200:
                break
            page += 1
            time.sleep(1)   # 遵守 API 速率限制

        if max_posts is not None and len(all_posts) >= max_posts:
            break

    log_fn(f"搜索完成：正常图片 {normal_count} 张")
    log_fn(f"搜索完成：已删除图片 {deleted_count} 张")
    log_fn(f"合计 {len(all_posts)} 张")
    return all_posts


# ── 标签解析 ──────────────────────────────────────────────────────────────────

def classify_tags(post: dict) -> tuple[list[str], list[str]]:
    """
    从帖子字段直接提取 artist / character 标签。
    Danbooru API 返回的帖子已包含 tag_string_artist 和 tag_string_character 字段，
    无需额外发起标签查询请求。
    """
    artists = post.get("tag_string_artist", "").strip().split()
    characters = post.get("tag_string_character", "").strip().split()
    return [a for a in artists if a], [c for c in characters if c]


# ── 文件命名 ──────────────────────────────────────────────────────────────────

def sanitize_name(name: str) -> str:
    """移除文件名/文件夹名中 Windows 不允许的特殊字符"""
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def build_filename(query: str, artists: list[str], characters: list[str],
                   index: int, ext: str) -> str:
    """
    构建文件名格式：搜索词(作者)_角色{序号}.ext
    示例：shingeki_no_kyojin(artist_a)_eren_yeager01.jpg
    """
    artist_part = "&".join(artists) if artists else "unknown"
    base = f"{query}({artist_part})"

    if characters:
        base = f"{base}_{'&'.join(characters)}"

    seq = str(index).zfill(2)   # 序号补零，保证排序一致
    return sanitize_name(f"{base}{seq}.{ext}")


def get_folder_name(artists: list[str]) -> str:
    """根据作者列表确定子文件夹名，无作者时归入 unknown"""
    if not artists:
        return "unknown"
    return sanitize_name("&".join(artists))


def get_next_index(folder_path: Path) -> int:
    """扫描已有文件，返回下一个可用序号（从 1 开始）"""
    if not folder_path.exists():
        return 1
    return len(list(folder_path.iterdir())) + 1


def download_image(url: str, filepath: Path, logger: logging.Logger,
                   pause_event=None, stop_event=None,
                   timeout: float = 60) -> bool:
    """
    下载单张图片到指定路径，只尝试一次。
    返回 True 表示成功，False 表示失败。
    """
    if stop_event is not None and stop_event.is_set():
        return False
    if pause_event is not None and not pause_event.is_set():
        if not wait_for_resume(pause_event, stop_event):
            return False

    try:
        resp = requests.get(url, headers=HEADERS, auth=get_auth(), timeout=timeout, stream=True)
        resp.raise_for_status()
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if stop_event is not None and stop_event.is_set():
                    return False
                if pause_event is not None and not pause_event.is_set():
                    if not wait_for_resume(pause_event, stop_event):
                        return False
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        logger.error(f"下载失败 — {filepath.name} | URL: {url} | 原因: {e}")
        return False


# ── 主流程 ────────────────────────────────────────────────────────────────────

def process_posts(posts: list[dict], query: str, output_dir: Path,
                  record_query: str | None = None,
                  extra_handler: logging.Handler | None = None,
                  pause_event=None, stop_event=None,
                  template_preset: str = "default",
                  template_custom: str = "",
                  path_template: str = "",
                  file_template: str = "",
                  filters=None,
                  on_progress=None,
                  on_fail=None,
                  download_concurrency: int = 4) -> list[dict]:
    """
    处理帖子列表：跳过已下载、命名、下载图片并更新记录。
    按 is_deleted 分组处理，先下载正常图片再下载已删除图片，日志分类展示。
    """
    from naming import render_split_path

    use_split = bool(file_template)
    logger = setup_logger(output_dir, extra_handler)

    normal_posts = [p for p in posts if not p.get("is_deleted", False)]
    deleted_posts = [p for p in posts if p.get("is_deleted", False)]

    effective_record_query = (record_query or query).strip() or query

    logger.info(f"开始下载，搜索词: {query}")
    logger.info(f"下载目录: {output_dir}")
    logger.info(f"待处理：正常 {len(normal_posts)} 张，已删除 {len(deleted_posts)} 张")

    record_path = output_dir / RECORD_FILENAME
    downloaded = load_downloaded(record_path, effective_record_query)
    folder_counters: dict[str, int] = {}
    failed_items: list[dict] = []
    controller = AdaptiveConcurrency(initial=max(1, download_concurrency))
    counters_lock = threading.Lock()
    record_lock = threading.Lock()
    folder_lock = threading.Lock()
    active_lock = threading.Lock()
    active_downloads = 0

    stats = {
        "normal": {"success": 0, "skip": 0, "fail": 0},
        "deleted": {"success": 0, "skip": 0, "fail": 0},
    }

    total = len(posts)
    handled = 0

    def emit_progress():
        if on_progress:
            try:
                on_progress(handled, total)
            except Exception:
                pass

    def is_stopped() -> bool:
        return stop_event is not None and stop_event.is_set()

    def before_step() -> bool:
        if is_stopped():
            return False
        if pause_event is not None and not wait_for_resume(pause_event, stop_event):
            return False
        return not is_stopped()

    def current_active() -> int:
        with active_lock:
            return active_downloads

    def change_active(delta: int) -> int:
        nonlocal active_downloads
        with active_lock:
            active_downloads += delta
            return active_downloads

    def resolve_path(ctx: PostCtx, index: int) -> Path:
        if use_split:
            return render_split_path(path_template, file_template, ctx, index, output_dir)
        return render_path(template_preset, template_custom, ctx, index, output_dir)

    def finalize_skip(stat_key: str, prefix: str, message: str, level: str = "debug"):
        nonlocal handled
        getattr(logger, level)(message)
        with counters_lock:
            stats[stat_key]["skip"] += 1
            handled += 1
            emit_progress()

    def process_post(post: dict, prefix: str, stat_key: str) -> dict:
        nonlocal handled
        change_active(1)
        try:
            post_id = post.get("id")
            file_url = post.get("file_url") or post.get("large_file_url", "")
            file_ext = post.get("file_ext", "jpg")
            file_size = post.get("file_size")

            if post_id in downloaded:
                finalize_skip(stat_key, prefix, f"{prefix} 已下载，跳过 (id={post_id})")
                return {"kind": "skip"}

            if not file_url:
                finalize_skip(stat_key, prefix, f"{prefix} 帖子 {post_id}: 无下载链接，跳过", "warning")
                return {"kind": "skip"}

            if filters is not None:
                reason = filters.rejects(file_ext, file_size)
                if reason:
                    finalize_skip(stat_key, prefix, f"{prefix} {reason}", "info")
                    return {"kind": "skip"}

            artists, characters = classify_tags(post)
            rating = post.get("rating", "")

            ctx = PostCtx(
                site="danbooru",
                post_id=post_id,
                query=query,
                artists=artists,
                characters=characters,
                rating=rating,
                ext=file_ext,
                md5=post.get("md5", "") or "",
                score=int(post.get("score", 0) or 0),
            )

            with folder_lock:
                folder_key = ctx.artist_name
                if folder_key not in folder_counters:
                    probe = resolve_path(ctx, 1)
                    folder_counters[folder_key] = get_next_index(probe.parent)
                index = folder_counters[folder_key]
                filepath = resolve_path(ctx, index)
                folder_counters[folder_key] += 1

            logger.info(f"{prefix} 准备下载: {filepath.name}")
            success = download_image(
                file_url,
                filepath,
                logger,
                pause_event=pause_event,
                stop_event=stop_event,
            )

            if is_stopped():
                return {"kind": "stopped"}

            with counters_lock:
                handled += 1
                emit_progress()
                if success:
                    stats[stat_key]["success"] += 1
                else:
                    stats[stat_key]["fail"] += 1

            if success:
                with record_lock:
                    downloaded.add(post_id)
                    save_downloaded(record_path, effective_record_query, downloaded)
                logger.debug(f"{prefix} 成功: {filepath.name}")
                return {"kind": "success"}

            item = {
                "post_id": post_id,
                "file_url": file_url,
                "filepath": str(filepath),
                "error": "download failed after retries",
            }
            with counters_lock:
                failed_items.append(item)
            if on_fail:
                try:
                    on_fail(post_id, "download failed after retries")
                except Exception:
                    pass
            return {"kind": "fail"}
        finally:
            change_active(-1)

    def process_group(group_posts: list[dict], group_label: str, stat_key: str):
        nonlocal handled
        group_total = len(group_posts)
        if group_total == 0:
            return

        logger.info(f"正在建立 [{group_label}] 下载队列，共 {group_total} 张")
        logger.info(f"[{group_label}] 正在启动 {controller.target()} 路下载")
        index = 0
        active_futures: dict = {}

        with ThreadPoolExecutor(max_workers=max(1, download_concurrency)) as executor:
            while True:
                if is_stopped():
                    logger.info(f"[{group_label}] 收到中止信号，停止投放新任务；当前活动下载 {current_active()} 个")
                    break
                if pause_event is not None and not pause_event.is_set():
                    logger.info(f"[{group_label}] 已暂停，等待 {current_active()} 个活动下载进入暂停点")
                    if not wait_for_resume(pause_event, stop_event):
                        break
                    logger.info(f"[{group_label}] 已继续，恢复投放下载任务")

                target = controller.target()
                while index < group_total and len(active_futures) < target:
                    post = group_posts[index]
                    prefix = f"[{group_label} {index + 1}/{group_total}]"
                    future = executor.submit(process_post, post, prefix, stat_key)
                    active_futures[future] = prefix
                    index += 1

                if not active_futures:
                    if index >= group_total:
                        break
                    continue

                done, _ = wait(set(active_futures.keys()), timeout=0.2, return_when=FIRST_COMPLETED)
                if not done:
                    continue
                for future in done:
                    prefix = active_futures.pop(future)
                    try:
                        result = future.result()
                    except Exception as exc:
                        logger.error(f"{prefix} 任务异常: {exc}")
                        with counters_lock:
                            stats[stat_key]["fail"] += 1
                            handled += 1
                            emit_progress()
                        continue
                    if result.get("kind") == "stopped":
                        logger.info(f"[{group_label}] 下载已中止")
                        return

    logger.info("正在整理下载任务...")
    emit_progress()
    process_group(normal_posts, "正常", "normal")
    if not is_stopped():
        process_group(deleted_posts, "已删除", "deleted")

    ns, ds = stats["normal"], stats["deleted"]
    logger.info("─" * 40)
    if is_stopped():
        logger.info("任务已被用户中止（以下为中止前已完成的统计）")
    logger.info(f"[正常]   成功 {ns['success']}，跳过 {ns['skip']}，失败 {ns['fail']}")
    logger.info(f"[已删除] 成功 {ds['success']}，跳过 {ds['skip']}，失败 {ds['fail']}")
    logger.info(f"合计成功 {ns['success'] + ds['success']} / {len(posts)}")
    return failed_items


def run(query: str, include_deleted: bool, output_dir: Path,
        record_query: str | None = None,
        extra_handler: logging.Handler | None = None,
        pause_event=None, stop_event=None,
        download_concurrency: int = 4) -> None:
    """
    供外部（如 Flask app）直接调用的入口函数。
    extra_handler: 可选，用于将日志实时推送到前端。
    pause_event: threading.Event，传递给 fetch/process 实现暂停控制。
    stop_event: threading.Event，传递给 fetch/process 实现中止控制。
    """
    posts = fetch_all_posts(query, include_deleted,
                            log_fn=lambda msg: (
                                extra_handler and extra_handler.emit(
                                    logging.makeLogRecord({"msg": msg, "levelno": logging.INFO, "levelname": "INFO"})
                                ) or print(msg)
                            ),
                            pause_event=pause_event,
                            stop_event=stop_event)
    if not posts:
        print("未找到任何图片")
        return
    if stop_event is not None and stop_event.is_set():
        return
    process_posts(posts, query, output_dir, record_query, extra_handler,
                  pause_event=pause_event, stop_event=stop_event,
                  download_concurrency=download_concurrency)


def main():
    print("=== danbooru.donmai.us 图片爬虫 ===")
    if not get_auth():
        print("\n[提示] 未配置 API 认证，可能遇到 403 错误。")
        print("  请通过 Web 界面设置页面填写 Danbooru 凭据，或创建 .env 文件。")
        print("  API key 获取地址: https://danbooru.donmai.us/users/home\n")
    print("1. 开始下载")
    print("2. 重置指定搜索词的下载记录")
    print("3. 查看所有下载记录")
    choice = input("\n请选择操作 (默认 1): ").strip() or "1"

    default_dir = os.path.join(os.getcwd(), "downloads")
    output_input = input(f"请输入保存目录 (默认: {default_dir}): ").strip()
    output_dir = Path(output_input) if output_input else Path(default_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    record_path = output_dir / RECORD_FILENAME

    if choice == "3":
        list_records(record_path)
        return

    if choice == "2":
        list_records(record_path)
        query = input("\n请输入要重置的搜索词: ").strip()
        if query:
            reset_downloaded(record_path, query)
        return

    query = input("请输入搜索词 (例如: shingeki_no_kyojin): ").strip()
    if not query:
        print("搜索词不能为空")
        return

    ans = input("是否同时下载已删除的图片？(y/N): ").strip().lower()
    include_deleted = ans == "y"

    print(f"\n保存目录: {output_dir}\n")

    posts = fetch_all_posts(query, include_deleted)
    if not posts:
        print("未找到任何图片")
        return

    process_posts(posts, query, output_dir)
    print(f"\n下载完成！日志已保存至: {output_dir / LOG_FILENAME}")


if __name__ == "__main__":
    main()
