"""
文件名模板与过滤器 — 由 app.py 传入前端设置，供两个爬虫共用。
不依赖站点，纯函数模块。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
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

    @property
    def artist_name(self) -> str:
        return sanitize_segment("&".join(self.artists) if self.artists else "unknown", "unknown")

    @property
    def character_name(self) -> str:
        if not self.characters:
            return ""
        return sanitize_segment("&".join(self.characters), "")


# ── 预设模板 ─────────────────────────────────────────────────────────────────
# 每个预设是 (目录模板, 文件名模板)，占位符稍后替换。
# {index} 只在 default 预设中有意义（用于同一作者文件夹内的局部序号）。

PRESETS: dict[str, tuple[str, str]] = {
    "default":  ("{query}/{site}/{artist}", "{query}({artist})_{character}{index:02d}.{ext}"),
    "byId":     ("{query}/{site}",          "{id}.{ext}"),
    "byArtist": ("{site}/{artist}",         "{id}_{character}.{ext}"),
    "flat":     ("",                        "{site}_{query}_{id}.{ext}"),
}

_VALID_PLACEHOLDERS = {"id", "query", "artist", "character", "index", "ext", "site", "rating"}


def _validate_custom(template: str) -> None:
    if "{ext}" not in template:
        raise ValueError("自定义模板必须包含 {ext} 占位符")
    if "{id}" not in template and "{index}" not in template:
        raise ValueError("自定义模板必须包含 {id} 或 {index} 之一，避免同名覆盖")
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
    """
    if preset == "custom":
        _validate_custom(custom_template)
        rendered = custom_template.format(
            id=ctx.post_id,
            query=sanitize_segment(ctx.query),
            artist=ctx.artist_name,
            character=ctx.character_name,
            index=index,
            ext=ctx.ext,
            site=ctx.site,
            rating=ctx.rating or "u",
        )
        parts = [sanitize_segment(p, "_") for p in rendered.replace("\\", "/").split("/") if p]
        return root.joinpath(*parts)

    if preset not in PRESETS:
        preset = "default"
    dir_tpl, file_tpl = PRESETS[preset]

    fmt = dict(
        id=ctx.post_id,
        query=sanitize_segment(ctx.query),
        artist=ctx.artist_name,
        character=ctx.character_name,
        index=index,
        ext=ctx.ext,
        site=ctx.site,
        rating=ctx.rating or "u",
    )
    dir_parts = [sanitize_segment(p, "_") for p in dir_tpl.format(**fmt).split("/") if p]
    filename = sanitize_segment(file_tpl.format(**fmt), "untitled")
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
