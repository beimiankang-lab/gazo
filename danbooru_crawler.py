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
import requests
from pathlib import Path
from naming import PostCtx, Filters, render_path

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

# Danbooru API 认证（Basic Auth）
# 在 https://danbooru.donmai.us/users/home 的 API key 页面获取
# 推荐方式：在项目根目录创建 .env 文件（已被 .gitignore 排除）或通过系统环境变量设置
# 留空则以匿名方式请求（部分内容受限）
DANBOORU_LOGIN = os.environ.get("DANBOORU_LOGIN", "")
DANBOORU_API_KEY = os.environ.get("DANBOORU_API_KEY", "")


def get_auth() -> tuple[str, str] | None:
    """返回 requests 的 auth 参数，未配置则返回 None"""
    if DANBOORU_LOGIN and DANBOORU_API_KEY:
        return (DANBOORU_LOGIN, DANBOORU_API_KEY)
    return None


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

def fetch_posts_page(query: str, page: int, limit: int = 200) -> list[dict]:
    """
    获取一页搜索结果。
    Danbooru 免费账号每页最多 200 条，Gold+ 账号可更高。
    """
    url = f"{BASE_URL}/posts.json"
    params = {"tags": query, "page": page, "limit": limit}
    resp = requests.get(url, params=params, headers=HEADERS, auth=get_auth(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_all_posts(query: str, include_deleted: bool,
                    log_fn=print, pause_event=None, stop_event=None) -> list[dict]:
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

    for q in queries:
        if stop_event is not None and stop_event.is_set():
            log_fn("收到中止信号，停止搜索")
            return all_posts

        is_deleted_query = "status:deleted" in q and "-status:deleted" not in q
        label = "(已删除)" if is_deleted_query else "(正常)"
        page = 1
        log_fn(f"正在搜索 {label}: {q}")
        while True:
            # 中止优先于暂停：中止时直接退出，不等暂停解除
            if stop_event is not None and stop_event.is_set():
                log_fn("收到中止信号，停止搜索")
                return all_posts
            # 暂停检查：event 被清除时此处阻塞，直到 resume 重新 set
            if pause_event is not None:
                pause_event.wait()

            log_fn(f"  获取第 {page} 页...")
            try:
                posts = fetch_posts_page(q, page)
            except Exception as e:
                log_fn(f"请求失败: {e}")
                break

            if not posts:
                log_fn("无更多结果")
                break

            # 过滤掉已见帖子，实现跨查询去重
            new_posts = [p for p in posts if p.get("id") not in seen_ids]
            for p in new_posts:
                seen_ids.add(p["id"])
            all_posts.extend(new_posts)

            # 按查询类型累计计数
            if is_deleted_query:
                deleted_count += len(new_posts)
            else:
                normal_count += len(new_posts)

            log_fn(f"  获取到 {len(posts)} 条，新增 {len(new_posts)} 条")

            # 返回条数不足一页说明已到末尾
            if len(posts) < 200:
                break
            page += 1
            time.sleep(1)   # 遵守 API 速率限制

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


# ── 下载 ──────────────────────────────────────────────────────────────────────

def download_image(url: str, filepath: Path, logger: logging.Logger,
                   retries: int = 3) -> bool:
    """
    下载单张图片到指定路径，失败时自动重试。
    返回 True 表示成功，False 表示彻底失败。
    """
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, auth=get_auth(),
                                timeout=60, stream=True)
            resp.raise_for_status()
            # 确保父目录存在
            filepath.parent.mkdir(parents=True, exist_ok=True)
            # 分块写入，避免大文件占用过多内存
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            if attempt < retries:
                logger.debug(f"重试 {attempt}/{retries} — {filepath.name}: {e}")
                time.sleep(1)
            else:
                logger.error(f"下载失败 — {filepath.name} | URL: {url} | 原因: {e}")
    return False


# ── 主流程 ────────────────────────────────────────────────────────────────────

def process_posts(posts: list[dict], query: str, output_dir: Path,
                  extra_handler: logging.Handler | None = None,
                  pause_event=None, stop_event=None,
                  template_preset: str = "default",
                  template_custom: str = "",
                  filters=None) -> None:
    """
    处理帖子列表：跳过已下载、命名、下载图片并更新记录。
    按 is_deleted 分组处理，先下载正常图片再下载已删除图片，日志分类展示。
    extra_handler: 可选，前端实时日志 Handler。
    pause_event: threading.Event，被清除时在每张图片下载前阻塞（暂停）。
    stop_event: threading.Event，被 set 时在每张图片下载前退出（中止）。
    """
    logger = setup_logger(output_dir, extra_handler)

    # 按是否已删除分组
    normal_posts  = [p for p in posts if not p.get("is_deleted", False)]
    deleted_posts = [p for p in posts if     p.get("is_deleted", False)]

    logger.info(f"开始下载，搜索词: {query}")
    logger.info(f"待处理：正常 {len(normal_posts)} 张，已删除 {len(deleted_posts)} 张")

    record_path = output_dir / RECORD_FILENAME
    downloaded = load_downloaded(record_path, query)  # 读取历史下载记录

    folder_counters: dict[str, int] = {}  # 各作者文件夹当前序号缓存

    # 分组统计
    stats = {
        "normal":  {"success": 0, "skip": 0, "fail": 0},
        "deleted": {"success": 0, "skip": 0, "fail": 0},
    }

    def is_stopped() -> bool:
        return stop_event is not None and stop_event.is_set()

    def process_group(group_posts: list[dict], group_label: str, stat_key: str):
        """处理一组帖子，group_label 用于日志前缀区分（正常/已删除）"""
        group_total = len(group_posts)
        if group_total == 0:
            return
        logger.info(f"── 开始下载 [{group_label}] 图片，共 {group_total} 张 ──")

        for i, post in enumerate(group_posts, 1):
            if is_stopped():
                logger.info(f"[{group_label}] 收到中止信号，停止下载")
                return

            post_id = post.get("id")
            prefix = f"[{group_label} {i}/{group_total}]"

            # 已在记录中 → 跳过
            if post_id in downloaded:
                logger.debug(f"{prefix} 已下载，跳过 (id={post_id})")
                stats[stat_key]["skip"] += 1
                continue

            file_url = post.get("file_url") or post.get("large_file_url", "")
            file_ext = post.get("file_ext", "jpg")
            file_size = post.get("file_size")

            if not file_url:
                logger.warning(f"{prefix} 帖子 {post_id}: 无下载链接，跳过")
                stats[stat_key]["skip"] += 1
                continue

            if filters is not None:
                reason = filters.rejects(file_ext, file_size)
                if reason:
                    logger.info(f"{prefix} {reason}")
                    stats[stat_key]["skip"] += 1
                    continue

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
            )
            folder_key = ctx.artist_name
            if folder_key not in folder_counters:
                # 预估起始序号（仅 default 预设有意义）
                probe = render_path(template_preset, template_custom, ctx, 1, output_dir)
                folder_counters[folder_key] = get_next_index(probe.parent)

            index = folder_counters[folder_key]
            filepath = render_path(template_preset, template_custom, ctx, index, output_dir)

            logger.info(f"{prefix} 下载: {filepath.name}")
            # 中止优先于暂停：中止时直接退出当前组
            if is_stopped():
                logger.info(f"[{group_label}] 收到中止信号，停止下载")
                return
            if pause_event is not None:
                pause_event.wait()
            if is_stopped():
                logger.info(f"[{group_label}] 收到中止信号，停止下载")
                return

            success = download_image(file_url, filepath, logger)
            if success:
                folder_counters[folder_key] += 1
                stats[stat_key]["success"] += 1
                downloaded.add(post_id)
                save_downloaded(record_path, query, downloaded)
                logger.debug(f"{prefix} 成功: {filepath.name}")
            else:
                stats[stat_key]["fail"] += 1

            time.sleep(1)   # 每张图片下载间隔

    # 先下载正常图片，再下载已删除图片
    process_group(normal_posts,  "正常",   "normal")
    if not is_stopped():
        process_group(deleted_posts, "已删除", "deleted")

    # 分开汇报
    ns, ds = stats["normal"], stats["deleted"]
    logger.info("─" * 40)
    if is_stopped():
        logger.info("任务已被用户中止（以下为中止前已完成的统计）")
    logger.info(f"[正常]   成功 {ns['success']}，跳过 {ns['skip']}，失败 {ns['fail']}")
    logger.info(f"[已删除] 成功 {ds['success']}，跳过 {ds['skip']}，失败 {ds['fail']}")
    logger.info(f"合计成功 {ns['success'] + ds['success']} / {len(posts)}")


def run(query: str, include_deleted: bool, output_dir: Path,
        extra_handler: logging.Handler | None = None,
        pause_event=None, stop_event=None) -> None:
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
    process_posts(posts, query, output_dir, extra_handler,
                  pause_event=pause_event, stop_event=stop_event)


def main():
    print("=== danbooru.donmai.us 图片爬虫 ===")
    if not DANBOORU_LOGIN or not DANBOORU_API_KEY:
        print("\n[提示] 未配置 API 认证，可能遇到 403 错误。")
        print("  请在脚本顶部填写 DANBOORU_LOGIN 和 DANBOORU_API_KEY。")
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
