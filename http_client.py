"""
统一 HTTP 客户端封装。

替代标准 `requests` 库以绕过 Cloudflare TLS 指纹检测：
使用 curl_cffi 配合 firefox133 浏览器模拟，复刻真实 TLS 握手行为。

提供与 requests 兼容的 API（get/post/Session/HTTPError/ConnectionError/Timeout/iter_content/...），
让 danbooru_crawler / yande_crawler / app.py / download_runtime.py 几乎零修改地切换。

特性：
- 默认 impersonate='firefox133'（用户实测可绕过 Cloudflare）
- 自动从 Windows 注册表读取系统代理（HKCU 的 Internet Settings）
- 兼容 requests.exceptions.* 的异常类型
"""

from __future__ import annotations

import os
from typing import Any

from curl_cffi import requests as _cffi_requests
from curl_cffi.requests import exceptions as _cffi_exceptions

# ── 默认浏览器模拟配置 ──────────────────────────────────────────────────────────
# 用户实测：chrome120/124/131 全部被 Cloudflare 拦截；firefox133 与 safari17_2_ios
# 可正常返回 200。统一选 firefox133，桌面浏览器特征更接近通常用户。
DEFAULT_IMPERSONATE = "firefox133"
DEFAULT_TIMEOUT = 30


# ── 系统代理自动检测 ────────────────────────────────────────────────────────────

def _detect_system_proxies() -> dict[str, str] | None:
    """
    从 Windows 注册表读取当前用户的系统代理设置。
    其它平台或未启用代理时返回 None，curl_cffi 将走直连。
    """
    if os.name != "nt":
        return None
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        )
        try:
            enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
            if not enable:
                return None
            server, _ = winreg.QueryValueEx(key, "ProxyServer")
        finally:
            winreg.CloseKey(key)
        if not server:
            return None
        # Windows ProxyServer 格式："host:port" 或 "http=host:port;https=host:port"
        if "=" in server:
            mapping: dict[str, str] = {}
            for part in server.split(";"):
                if "=" in part:
                    proto, addr = part.split("=", 1)
                    mapping[proto.strip().lower()] = addr.strip()
            http_proxy = mapping.get("http") or mapping.get("https")
            https_proxy = mapping.get("https") or mapping.get("http")
            if not http_proxy and not https_proxy:
                return None
            return {
                "http": f"http://{http_proxy}" if http_proxy else "",
                "https": f"http://{https_proxy}" if https_proxy else "",
            }
        return {
            "http":  f"http://{server}",
            "https": f"http://{server}",
        }
    except Exception:
        return None


_SYSTEM_PROXIES = _detect_system_proxies()


def get_proxies() -> dict[str, str] | None:
    """对外暴露当前生效的代理映射，供调用方需要时复用。"""
    return _SYSTEM_PROXIES


# ── 请求默认参数注入 ────────────────────────────────────────────────────────────

def _apply_defaults(kwargs: dict[str, Any]) -> dict[str, Any]:
    kwargs.setdefault("impersonate", DEFAULT_IMPERSONATE)
    if "timeout" not in kwargs:
        kwargs["timeout"] = DEFAULT_TIMEOUT
    if _SYSTEM_PROXIES is not None and "proxies" not in kwargs:
        kwargs["proxies"] = _SYSTEM_PROXIES
    return kwargs


# ── 顶层 API ────────────────────────────────────────────────────────────────────

def get(url: str, **kwargs: Any):
    return _cffi_requests.get(url, **_apply_defaults(kwargs))


def post(url: str, **kwargs: Any):
    return _cffi_requests.post(url, **_apply_defaults(kwargs))


def request(method: str, url: str, **kwargs: Any):
    return _cffi_requests.request(method, url, **_apply_defaults(kwargs))


# ── Session ─────────────────────────────────────────────────────────────────────

class Session(_cffi_requests.Session):
    """
    curl_cffi.Session 的薄包装，自动应用默认 impersonate 与系统代理。
    实例方法签名与 requests.Session 完全兼容。
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("impersonate", DEFAULT_IMPERSONATE)
        super().__init__(*args, **kwargs)
        if _SYSTEM_PROXIES is not None and not getattr(self, "proxies", None):
            self.proxies = _SYSTEM_PROXIES  # type: ignore[assignment]

    def request(self, method: str, url: str, **kwargs: Any):
        if "timeout" not in kwargs:
            kwargs["timeout"] = DEFAULT_TIMEOUT
        return super().request(method, url, **kwargs)


# ── 兼容 requests.exceptions 的异常别名 ─────────────────────────────────────────
# 让现有代码的 `except requests.HTTPError` / `requests.Timeout` 等无需改写。

HTTPError       = _cffi_exceptions.HTTPError
ConnectionError = _cffi_exceptions.ConnectionError
Timeout         = _cffi_exceptions.Timeout
RequestException = _cffi_exceptions.RequestException
ProxyError      = _cffi_exceptions.ProxyError
SSLError        = _cffi_exceptions.SSLError

Response = _cffi_requests.Response


# requests.exceptions 子模块兼容写法：让 `http_client.exceptions.Timeout` 也可用
class exceptions:  # noqa: N801 — 故意小写贴合 requests 风格
    HTTPError       = HTTPError
    ConnectionError = ConnectionError
    Timeout         = Timeout
    RequestException = RequestException
    ProxyError      = ProxyError
    SSLError        = SSLError


__all__ = [
    "DEFAULT_IMPERSONATE",
    "DEFAULT_TIMEOUT",
    "Session",
    "Response",
    "HTTPError",
    "ConnectionError",
    "Timeout",
    "RequestException",
    "ProxyError",
    "SSLError",
    "exceptions",
    "get",
    "post",
    "request",
    "get_proxies",
]
