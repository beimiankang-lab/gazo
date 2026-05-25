"""
文件名模板与过滤器 — 由 app.py 传入前端设置，供两个爬虫共用。
不依赖站点，纯函数模块。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


_INVALID_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_segment(name: str, default: str = "_") -> str:
    """清洗单个路径/文件名字段：去非法字符、去首尾点和空白。"""
    if not name:
        return default
    cleaned = _INVALID_RE.sub("_", name)
    cleaned = cleaned.strip(" .")
    return cleaned or default


@dataclass(frozen=True)
class PostCtx:
    """渲染模板所需的贴文上下文。"""
    site: str                # "danbooru" 或 "yande"
    post_id: int
    query: str               # 用户输入的搜索词（不含评级片段）
    artists: list[str]
    characters: list[str]
    rating: str              # "s" / "q" / "e"，未知时为 ""
    ext: str                 # 无前导点
    # 新增可选字段：date(YYYY-MM-DD), md5, copyrights
    date: str = ""
    md5: str = ""
    copyrights: list[str] = field(default_factory=list)
    score: int = 0

    @property
    def artist_name(self) -> str:
        return sanitize_segment("&".join(self.artists) if self.artists else "unknown", "unknown")

    @property
    def character_name(self) -> str:
        if not self.characters:
            return ""
        return sanitize_segment("&".join(self.characters), "")

    @property
    def copyright_name(self) -> str:
        if not self.copyrights:
            return ""
        return sanitize_segment("&".join(self.copyrights), "")


# ── 预设模板 ─────────────────────────────────────────────────────────────────
# 每个预设是 (目录模板, 文件名模板)，占位符稍后替换。
# {index} 只在 default 预设中有意义（用于同一作者文件夹内的局部序号）。

PRESETS: dict[str, tuple[str, str]] = {
    "default":  ("{query}/{site}/{artist}", "{query}({artist})_{character}{index:02d}.{ext}"),
    "byId":     ("{query}/{site}",          "{id}.{ext}"),
    "byArtist": ("{site}/{artist}",         "{id}_{character}.{ext}"),
    "flat":     ("",                        "{site}_{query}_{id}.{ext}"),
}

# 所有合法占位符（用于校验和前端展示）
PLACEHOLDERS = ["id", "query", "artist", "character", "copyright",
                "index", "ext", "site", "rating", "date", "md5", "score"]
_VALID_PLACEHOLDERS = set(PLACEHOLDERS)


def _build_format_dict(ctx: PostCtx, index: int) -> dict:
    return dict(
        id=ctx.post_id,
        query=sanitize_segment(ctx.query),
        artist=ctx.artist_name,
        character=ctx.character_name,
        copyright=ctx.copyright_name,
        index=index,
        ext=ctx.ext,
        site=ctx.site,
        rating=ctx.rating or "u",
        date=ctx.date or "unknown_date",
        md5=ctx.md5 or "nomd5",
        score=ctx.score,
    )


def _validate_template(template: str, *, require_ext: bool = False, require_unique: bool = False) -> None:
    """通用占位符校验。"""
    if require_ext and "{ext}" not in template:
        raise ValueError("文件名模板必须包含 {ext} 占位符")
    if require_unique and "{id}" not in template and "{index}" not in template and "{md5}" not in template:
        raise ValueError("文件名模板必须包含 {id}、{index} 或 {md5} 之一，避免同名覆盖")
    for match in re.finditer(r"\{([a-zA-Z_]+)(?::[^}]*)?\}", template):
        name = match.group(1)
        if name not in _VALID_PLACEHOLDERS:
            raise ValueError(f"未知占位符：{{{name}}}")


def render_path(
    preset: str,
    custom_template: str,
    ctx: PostCtx,
    index: int,
    root: Path,
) -> Path:
    """
    根据预设或自定义模板返回最终的完整文件路径。
    root 是用户选择的保存目录，即模板的起点。
    保留旧的单一 custom_template 入口以保持向后兼容。
    """
    if preset == "custom":
        _validate_template(custom_template, require_ext=True, require_unique=True)
        fmt = _build_format_dict(ctx, index)
        rendered = custom_template.format(**fmt)
        parts = [sanitize_segment(p, "_") for p in rendered.replace("\\", "/").split("/") if p]
        return root.joinpath(*parts)

    if preset not in PRESETS:
        preset = "default"
    dir_tpl, file_tpl = PRESETS[preset]

    fmt = _build_format_dict(ctx, index)
    dir_parts = [sanitize_segment(p, "_") for p in dir_tpl.format(**fmt).split("/") if p]
    filename = sanitize_segment(file_tpl.format(**fmt), "untitled")
    return root.joinpath(*dir_parts, filename)


def render_split_path(
    path_template: str,
    file_template: str,
    ctx: PostCtx,
    index: int,
    root: Path,
) -> Path:
    """
    新版渲染：保存子目录和文件名分开两个模板。
    path_template 可以为空（直接放在 root 下）。
    """
    _validate_template(file_template, require_ext=True, require_unique=True)
    if path_template:
        _validate_template(path_template)

    fmt = _build_format_dict(ctx, index)
    dir_parts: list[str] = []
    if path_template:
        rendered_dir = path_template.format(**fmt).replace("\\", "/")
        dir_parts = [sanitize_segment(p, "_") for p in rendered_dir.split("/") if p]
    filename = sanitize_segment(file_template.format(**fmt), "untitled")
    return root.joinpath(*dir_parts, filename)


# ── 文件类型/大小过滤 ─────────────────────────────────────────────────────────

_IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "bmp"}
_ANIMATED_EXTS = {"gif"}
_VIDEO_EXTS = {"mp4", "webm", "swf", "avi", "mkv", "mov"}


@dataclass(frozen=True)
class Filters:
    allow_image: bool = True
    allow_animated: bool = True
    allow_video: bool = True
    max_size_bytes: int | None = None

    def rejects(self, ext: str, file_size: int | None) -> str | None:
        """若应被过滤，返回跳过原因；否则返回 None。"""
        e = (ext or "").lower().lstrip(".")
        if e in _ANIMATED_EXTS and not self.allow_animated:
            return f"已跳过动图 (.{e})"
        if e in _VIDEO_EXTS and not self.allow_video:
            return f"已跳过视频 (.{e})"
        # 其余扩展名（包含未知类型）按静态图处理
        if (e in _IMAGE_EXTS or e not in (_ANIMATED_EXTS | _VIDEO_EXTS)) and not self.allow_image:
            return f"已跳过静态图 (.{e})"
        if self.max_size_bytes is not None and file_size is not None and file_size > self.max_size_bytes:
            mb = file_size / (1024 * 1024)
            limit_mb = self.max_size_bytes / (1024 * 1024)
            return f"已跳过超大文件 ({mb:.1f} MB > {limit_mb:.0f} MB)"
        return None


def parse_filters(raw: dict | None) -> Filters:
    if not raw:
        return Filters()
    max_mb = raw.get("max_size_mb")
    max_bytes = int(max_mb) * 1024 * 1024 if max_mb else None
    return Filters(
        allow_image=bool(raw.get("allow_image", True)),
        allow_animated=bool(raw.get("allow_animated", True)),
        allow_video=bool(raw.get("allow_video", True)),
        max_size_bytes=max_bytes,
    )
