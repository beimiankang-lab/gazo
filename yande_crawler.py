"""
yande.re 图片爬虫
用法: python yande_crawler.py
或通过 app.py 前端界面调用
"""

import os
import re
import time
import json
import logging
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── 站点基础配置 ──────────────────────────────────────────────────────────────
BASE_URL = "https://yande.re"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Moebooru 标签类型常量
TAG_TYPE_GENERAL = 0    # 通用标签
TAG_TYPE_ARTIST = 1     # 作者
TAG_TYPE_COPYRIGHT = 3  # 版权/作品名
TAG_TYPE_CHARACTER = 4  # 角色
TAG_TYPE_CIRCLE = 5     # 社团

# 全局标签类型缓存，避免重复查询同一标签
_tag_type_cache: dict[str, int] = {}

# 下载记录文件名（与 danbooru 分开，防止互相覆盖）
RECORD_FILENAME = ".downloaded_yande.json"
LOG_FILENAME = "download.log"


# ── 日志 ──────────────────────────────────────────────────────────────────────

def setup_logger(output_dir: Path, extra_handler: logging.Handler | None = None) -> logging.Logger:
    """
    初始化日志，同时输出到控制台和文件。
    extra_handler: 可传入额外的 Handler（如前端实时日志队列 Handler）。
    """
    logger = logging.getLogger("yande")
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

def fetch_posts_page(query: str, page: int, limit: int = 100) -> list[dict]:
    """
    获取一页搜索结果。
    yande.re 单页最多 100 条。
    """
    url = f"{BASE_URL}/post.json"
    params = {"tags": query, "page": page, "limit": limit}
    resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_all_posts(query: str, log_fn=print, pause_event=None, stop_event=None) -> list[dict]:
    """
    分页获取所有搜索结果。
    log_fn: 日志输出函数，默认 print，前端调用时可传入队列写入函数。
    pause_event: threading.Event，被清除时任务会在翻页前阻塞等待（暂停）。
    stop_event: threading.Event，被 set 时函数会尽快返回已搜索到的结果（中止）。
    """
    all_posts = []
    page = 1
    log_fn(f"正在搜索: {query}")
    while True:
        # 中止优先于暂停：中止时直接退出，不等暂停解除
        if stop_event is not None and stop_event.is_set():
            log_fn("收到中止信号，停止搜索")
            return all_posts
        # 暂停检查：event 被清除时此处阻塞，直到 resume 重新 set
        if pause_event is not None:
            pause_event.wait()

        log_fn(f"  获取第 {page} 页...")
        posts = fetch_posts_page(query, page)
        if not posts:
            log_fn("无更多结果")
            break
        log_fn(f"  获取到 {len(posts)} 条")
        all_posts.extend(posts)
        # 返回条数不足一页说明已到末尾
        if len(posts) < 100:
            break
        page += 1
        time.sleep(0.5)   # 遵守 API 速率限制
    log_fn(f"共找到 {len(all_posts)} 张图片")
    return all_posts


# ── 标签类型查询 ──────────────────────────────────────────────────────────────

def _fetch_single_tag_type(tag: str) -> tuple[str, int]:
    """
    查询单个标签的类型，返回 (tag_name, type_int)。
    用于批量接口未覆盖到的标签的降级查询。
    """
    try:
        url = f"{BASE_URL}/tag.json"
        params = {"name": tag, "limit": 1}
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # 精确匹配标签名，避免前缀误匹配
        for item in data:
            if item.get("name") == tag:
                return tag, item["type"]
    except Exception:
        pass
    # 查询失败时默认为通用标签
    return tag, TAG_TYPE_GENERAL


def fetch_tag_types_batch(tags: list[str]) -> dict[str, int]:
    """
    批量查询标签类型，返回 {tag_name: type_int}。
    优先使用 name[] 批量接口（每批 100 个），
    批量接口未返回的标签再并发逐个查询。
    结果写入全局缓存 _tag_type_cache，避免重复查询。
    """
    # 过滤掉已缓存的标签
    uncached = [t for t in tags if t not in _tag_type_cache]
    if not uncached:
        return {t: _tag_type_cache.get(t, TAG_TYPE_GENERAL) for t in tags}

    batch_size = 100
    remaining: list[str] = []   # 批量接口未返回的标签，稍后逐个查询

    for i in range(0, len(uncached), batch_size):
        batch = uncached[i:i + batch_size]
        try:
            url = f"{BASE_URL}/tag.json"
            params = [("name[]", t) for t in batch] + [("limit", str(batch_size))]
            resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            found = {item["name"] for item in data}
            for item in data:
                _tag_type_cache[item["name"]] = item["type"]
            # 批量接口没返回的标签，加入逐个查询列表
            for t in batch:
                if t not in found:
                    remaining.append(t)
        except Exception as e:
            print(f"  [警告] 批量标签查询失败: {e}，将逐个查询")
            remaining.extend(batch)
        time.sleep(0.2)

    # 对批量接口未返回的标签，并发逐个查询（最多 5 并发）
    if remaining:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(_fetch_single_tag_type, t): t for t in remaining}
            for future in as_completed(futures):
                tag, tag_type = future.result()
                _tag_type_cache[tag] = tag_type

    return {t: _tag_type_cache.get(t, TAG_TYPE_GENERAL) for t in tags}


def classify_tags(tags_str: str) -> tuple[list[str], list[str]]:
    """
    将帖子的 tags 字符串分类为 (artist_tags, character_tags)。
    通过查询 yande.re 标签类型 API 判断每个标签所属类型。
    """
    tags = tags_str.strip().split()
    if not tags:
        return [], []
    type_map = fetch_tag_types_batch(tags)
    artists = [t for t in tags if type_map.get(t) == TAG_TYPE_ARTIST]
    characters = [t for t in tags if type_map.get(t) == TAG_TYPE_CHARACTER]
    return artists, characters


# ── 文件命名 ──────────────────────────────────────────────────────────────────

def sanitize_name(name: str) -> str:
    """移除文件名/文件夹名中 Windows 不允许的特殊字符"""
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def build_filename(query: str, artists: list[str], characters: list[str],
                   index: int, ext: str) -> str:
    """
    构建文件名格式：搜索词(作者)_角色{序号}.ext
    示例：hatsune_miku(artist_a)_hatsune_miku01.jpg
    """
    artist_part = "&".join(artists) if artists else "unknown"
    base = f"{query}({artist_part})"

    if characters:
        char_part = "&".join(characters)
        base = f"{base}_{char_part}"

    seq = str(index).zfill(2)   # 序号补零，保证文件排序一致
    filename = f"{base}{seq}.{ext}"
    return sanitize_name(filename)


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
            resp = requests.get(url, headers=HEADERS, timeout=60, stream=True)
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
                  pause_event=None, stop_event=None) -> None:
    """
    处理帖子列表：跳过已下载、查询标签类型、命名、下载图片并更新记录。
    extra_handler: 可选，前端实时日志 Handler。
    pause_event: threading.Event，被清除时在每张图片下载前阻塞（暂停）。
    stop_event: threading.Event，被 set 时在每张图片下载前退出（中止）。
    """
    logger = setup_logger(output_dir, extra_handler)
    logger.info(f"开始下载，搜索词: {query}，共 {len(posts)} 张")

    record_path = output_dir / RECORD_FILENAME
    downloaded = load_downloaded(record_path, query)  # 读取历史下载记录

    # 预先收集所有标签，一次性批量查询类型，减少后续每帖的延迟
    all_tags: set[str] = set()
    for post in posts:
        all_tags.update(post.get("tags", "").strip().split())
    if all_tags:
        print(f"正在查询 {len(all_tags)} 个标签的类型...")
        fetch_tag_types_batch(list(all_tags))
        print("标签类型查询完成\n")

    # 各作者文件夹当前序号缓存，避免每次都重新扫描磁盘
    folder_counters: dict[str, int] = {}

    total = len(posts)
    for i, post in enumerate(posts, 1):
        if stop_event is not None and stop_event.is_set():
            logger.info("收到中止信号，停止下载")
            break

        post_id = post.get("id")
        file_url = post.get("file_url", "")
        file_ext = post.get("file_ext", "jpg")
        tags_str = post.get("tags", "")

        if not file_url:
            logger.warning(f"[{i}/{total}] 帖子 {post_id}: 无下载链接，跳过")
            continue

        # 已在记录中 → 跳过，避免重复下载
        if post_id in downloaded:
            logger.debug(f"[{i}/{total}] 已下载，跳过 (id={post_id})")
            continue

        artists, characters = classify_tags(tags_str)
        folder_name = get_folder_name(artists)
        # 目录结构：output_dir/搜索词/yande/作者名/
        folder_path = output_dir / query / "yande" / folder_name

        # 首次遇到该文件夹时扫描已有文件数，确定起始序号
        if folder_name not in folder_counters:
            folder_counters[folder_name] = get_next_index(folder_path)

        index = folder_counters[folder_name]
        filename = build_filename(query, artists, characters, index, file_ext)
        filepath = folder_path / filename

        logger.info(f"[{i}/{total}] 下载: {filename}")
        # 中止优先于暂停
        if stop_event is not None and stop_event.is_set():
            logger.info("收到中止信号，停止下载")
            break
        # 暂停检查：event 被清除时此处阻塞，直到 resume 重新 set
        if pause_event is not None:
            pause_event.wait()
        # 暂停解除后可能已收到中止信号，再检查一次
        if stop_event is not None and stop_event.is_set():
            logger.info("收到中止信号，停止下载")
            break

        success = download_image(file_url, filepath, logger)
        if success:
            folder_counters[folder_name] += 1
            downloaded.add(post_id)
            # 每次成功后立即持久化，防止中途中断丢失进度
            save_downloaded(record_path, query, downloaded)
            logger.debug(f"[{i}/{total}] 成功: {filename}")

        time.sleep(0.5)   # 每张图片下载间隔，避免请求过于频繁

    failed = total - len(downloaded)
    if stop_event is not None and stop_event.is_set():
        logger.info(f"任务已中止。成功: {len(downloaded)}，失败/跳过: {failed}")
    else:
        logger.info(f"下载完成。成功: {len(downloaded)}，失败/跳过: {failed}")


def run(query: str, output_dir: Path,
        extra_handler: logging.Handler | None = None,
        pause_event=None, stop_event=None) -> None:
    """
    供外部（如 Flask app）直接调用的入口函数。
    extra_handler: 可选，用于将日志实时推送到前端。
    pause_event: threading.Event，传递给 fetch/process 实现暂停控制。
    stop_event: threading.Event，传递给 fetch/process 实现中止控制。
    """
    posts = fetch_all_posts(query,
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
    print("=== yande.re 图片爬虫 ===")
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

    query = input("请输入搜索词 (例如: hatsune_miku): ").strip()
    if not query:
        print("搜索词不能为空")
        return

    print(f"\n保存目录: {output_dir}\n")

    posts = fetch_all_posts(query)
    if not posts:
        print("未找到任何图片")
        return

    process_posts(posts, query, output_dir)
    print(f"\n下载完成！日志已保存至: {output_dir / LOG_FILENAME}")


if __name__ == "__main__":
    main()
