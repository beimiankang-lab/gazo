<p align="center">
  <img src="logo/logo.png" alt="Gazō" width="140">
</p>

<h1 align="center">Gazō — Booru Image Crawler</h1>

<p align="center"><em>画像を集める — 来自 <a href="https://danbooru.donmai.us">Danbooru</a> 和 <a href="https://yande.re">Yande.re</a> 的图片批量采集工具，提供可视化 Web 界面，支持实时日志、暂停继续、中止任务、下载记录管理。</em></p>

---

## 目录

- [环境要求](#环境要求)
- [安装步骤](#安装步骤)
- [启动方式](#启动方式)
- [界面说明](#界面说明)
- [Danbooru 使用说明](#danbooru-使用说明)
- [Yande.re 使用说明](#yandere-使用说明)
- [下载记录管理](#下载记录管理)
- [文件结构](#文件结构)
- [命令行直接使用](#命令行直接使用)
- [常见问题](#常见问题)

---

## 环境要求

- Python 3.10 及以上
- 网络可正常访问 Danbooru / Yande.re（必要时需挂代理）

---

## 安装步骤

```bash
# 1. 进入项目目录
cd D:\crawler

# 2. 创建虚拟环境（可选，推荐）
python -m venv venv
venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt
```

---

## 启动方式

```bash
python app.py
```

启动后在浏览器打开：

```
http://127.0.0.1:5000
```

---

## 界面说明

```
┌─────────────────────────────────────────────────────┐
│  Gazō 画像を集める      [?使用教程] Danbooru & Yande│
├──────────────────┬──────────────────────────────────┤
│  Danbooru│Yande  │  Danbooru 日志 │ Yande.re 日志   │
│──────────────────│─────────────────────────────────-│
│  搜索词          │  [状态灯] 空闲/运行/暂停/中止    │
│  保存目录        │                                   │
│  [含已删除] 开关 │  2026-05-07 [INFO] 正在搜索...   │
│  [▶开始][⏸][⏹] │  2026-05-07 [INFO] 下载: xxx.jpg │
│──────────────────│                                   │
│  下载记录        │                                   │
│  D hatsune_miku  │                                   │
│  Y shingeki ...  │                                   │
└──────────────────┴──────────────────────────────────┘
```

| 区域 | 说明 |
|------|------|
| 左侧选项卡 | 切换 Danbooru / Yande.re 配置表单 |
| 右侧日志选项卡 | 独立查看每个站点的日志，切换不会中断任务 |
| 按钮区 | ▶ 开始、⏸ 暂停 / 继续、⏹ 中止（带二次确认）|
| 状态指示灯 | 绿色呼吸=运行中，橙色=已暂停，红色呼吸=正在中止，红色=已中止/出错，绿色常亮=完成 |
| 角标小圆点 | 选项卡右上角小点，任务运行时出现，方便切换后感知状态 |
| 使用教程按钮 | 顶部右上角「? 使用教程」，点击弹出完整教程，内容与本文档一致 |

---

## Danbooru 使用说明

### 1. 配置 API 认证

Danbooru 匿名访问受限（只能搜索安全级别内容，每页限 20 条）。建议配置 API Key：

1. 注册并登录 [danbooru.donmai.us](https://danbooru.donmai.us)
2. 进入个人主页 → **API Key** 页面，生成 Key
3. 复制项目根目录下的 `.env.example` 为 `.env`，填入凭据：

```bash
DANBOORU_LOGIN=你的用户名
DANBOORU_API_KEY=你的API Key
```

> `.env` 文件已在 `.gitignore` 中排除，不会被上传到 GitHub。程序启动时会自动加载。

### 2. 搜索词格式

Danbooru 使用标签组合搜索，多个标签用空格分隔：

| 示例搜索词 | 说明 |
|-----------|------|
| `hatsune_miku` | 搜索初音未来相关图片 |
| `shingeki_no_kyojin` | 搜索进击的巨人相关图片 |
| `hatsune_miku solo` | 多标签组合 |

> 标签名称可在 Danbooru 网站搜索框中确认，单词间用下划线连接。

### 3. 含已删除图片

开启后会额外搜索 `status:deleted` 的帖子并一并下载。已删除帖子可能无法获取原图链接，会自动跳过。

### 4. 文件保存结构

```
downloads/
└── {搜索词}/
    └── danbooru/
        └── {作者名}/
            ├── shingeki_no_kyojin(artist_a)_eren_yeager01.jpg
            └── shingeki_no_kyojin(artist_b)_unknown02.png
```

---

## Yande.re 使用说明

### 1. 搜索词格式

Yande.re 同样使用标签搜索：

| 示例搜索词 | 说明 |
|-----------|------|
| `hatsune_miku` | 搜索初音未来 |
| `hatsune_miku rating:s` | 只搜索安全级别 |

### 2. 标签类型查询

首次下载某个搜索词时，程序会批量查询所有标签的类型（作者 / 角色 / 版权等），用于自动归类文件名和目录，此步骤会稍慢，属正常现象。

### 3. 文件保存结构

```
downloads/
└── {搜索词}/
    └── yande/
        └── {作者名}/
            ├── hatsune_miku(artist_a)_hatsune_miku01.jpg
            └── hatsune_miku(unknown)02.jpg
```

---

## 下载记录管理

程序会在 `downloads/` 目录下保存两个记录文件：

| 文件 | 说明 |
|------|------|
| `.downloaded_danbooru.json` | Danbooru 已下载帖子 ID |
| `.downloaded_yande.json` | Yande.re 已下载帖子 ID |

两个站点的记录完全独立，重置一个不影响另一个。

### 重置记录

在界面左侧下载记录区域，点击每条记录右侧的 **✕** 按钮，确认后即可清除该搜索词的下载记录。下次运行时会重新下载所有图片。

---

## 文件结构

```
D:\crawler\
├── app.py                      # Flask 后端，提供 Web API
├── danbooru_crawler.py         # Danbooru 爬虫核心
├── yande_crawler.py            # Yande.re 爬虫核心
├── requirements.txt            # Python 依赖
├── README.md                   # 本文件
├── LICENSE                     # MIT 开源协议
├── .env.example                # 环境变量模板
├── .gitignore                  # Git 忽略规则
├── logo/
│   └── logo.png                # 项目 Logo
├── templates/
│   └── index.html              # 前端页面
├── downloads/                  # 图片下载目录（已 gitignore）
│   ├── .downloaded_danbooru.json
│   └── .downloaded_yande.json
└── venv/                       # Python 虚拟环境（已 gitignore）
```

---

## 命令行直接使用

不启动 Web 界面，也可以直接在终端运行爬虫：

```bash
# Danbooru
python danbooru_crawler.py

# Yande.re
python yande_crawler.py
```

按提示选择操作：
- `1` 开始下载
- `2` 重置指定搜索词记录
- `3` 查看所有下载记录

---

## 常见问题

**Q: 运行时遇到 403 错误？**
A: Danbooru 匿名访问受限，请在项目根目录创建 `.env` 文件并填写 API 认证信息（参考 `.env.example`）。

**Q: 图片下载很慢？**
A: 程序每张图片之间有 0.5~1 秒间隔，这是为了避免触发站点的请求频率限制，属正常现象。

**Q: 部分图片没有下载链接？**
A: 已删除帖子的原图可能已从服务器移除，程序会自动跳过并在日志中提示。

**Q: 切换选项卡后任务还在跑吗？**
A: 是的。切换选项卡只是切换界面显示，后台任务不受影响。右侧日志面板可随时切换查看两个站点各自的实时日志。

**Q: 如何暂停任务？**
A: 点击开始按钮旁边的 **⏸** 按钮，任务会在当前图片下载完成后暂停（不会中途截断文件）。点击 **▶** 继续。

**Q: 如何中止任务？**
A: 点击 **⏹** 中止按钮，弹出确认框，确认后任务会在当前图片下载完成后退出（同样不会截断文件）。已下载的图片和记录全部保留，下次运行会自动跳过。中止 Danbooru 任务不会影响正在跑的 Yande 任务，两者完全独立。

**Q: 想换搜索词怎么办？**
A: 先点 **⏹** 中止当前任务，等状态变成「已中止」后修改搜索词，再点开始即可。不需要刷新页面，这样另一个站点的任务不会受影响。

**Q: 意外关闭页面，任务还在吗？**
A: 关闭浏览器只断开了前端连接，后台 Flask 服务和下载线程仍在运行。重新打开页面后可以看到最新状态。但关闭 `app.py` 进程（Ctrl+C）会终止所有任务。

**Q: 两个站点可以同时跑吗？**
A: 可以。Danbooru 和 Yande.re 是两个独立域名，同时跑一个 Danbooru 和一个 Yande.re 任务完全没问题，不会互相影响。但不建议同一站点同时跑多个任务（总请求频率叠加，容易触发限流）。

---

## License

本项目基于 [MIT License](LICENSE) 开源。你可以自由使用、修改、分发本项目的代码，只需保留原始版权声明。

Copyright © 2026 ChuUNiMuggle
