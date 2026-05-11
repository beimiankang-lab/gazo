<p align="center">
  <img src="frontend/public/logo/logo.png" alt="Gazō" width="140">
</p>

<h1 align="center">Gazō — Booru Image Crawler</h1>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.zh-CN.md">简体中文</a> ·
  <strong>繁體中文</strong> ·
  <a href="README.ja.md">日本語</a>
</p>

<p align="center"><em>画像を集める — 來自 <a href="https://danbooru.donmai.us">Danbooru</a> 與 <a href="https://yande.re">Yande.re</a> 的圖片批次下載工具，提供視覺化 Web 介面，支援即時日誌、暫停繼續、中止任務與下載紀錄管理。</em></p>

---

## 目錄

- [環境需求](#環境需求)
- [安裝步驟](#安裝步驟)
- [啟動方式](#啟動方式)
- [介面說明](#介面說明)
- [Danbooru 使用說明](#danbooru-使用說明)
- [Yande.re 使用說明](#yandere-使用說明)
- [下載紀錄管理](#下載紀錄管理)
- [檔案結構](#檔案結構)
- [命令列直接使用](#命令列直接使用)
- [常見問題](#常見問題)

---

## 環境需求

- Python 3.10 以上
- Node.js 20+ 及 npm（用於建置前端；若僅執行預先建置好的產物則不需要）
- 可正常連線 Danbooru / Yande.re（必要時需使用代理伺服器）

---

## 安裝步驟

```bash
# 1. 進入專案目錄
cd D:\crawler

# 2. 建立虛擬環境（選用，建議）
python -m venv venv
venv\Scripts\activate

# 3. 安裝套件
pip install -r requirements.txt
```

---

## 啟動方式

### 正式模式（單一埠口執行）

前端程式碼位於 `frontend/`，使用 Vue 3 + Vite 撰寫。第一次使用前需要先建置一次靜態產物：

```bash
# 1. 建置前端（第一次 clone 或修改前端程式碼後執行）
cd frontend
npm install
npm run build
cd ..

# 2. 啟動後端，Flask 會託管 frontend 建置好的靜態檔案
python app.py
```

啟動後在瀏覽器開啟：

```
http://127.0.0.1:5000
```

> 若尚未建置前端，`python app.py` 會直接顯示錯誤並提示先執行 `npm run build`。

### 開發模式（前後端熱更新）

修改前端時建議前後端分別啟動，Vite 會把 `/api` 代理到 Flask：

```bash
# 終端機 A：啟動 Flask（預設埠口 5000）
python app.py

# 終端機 B：啟動 Vite 開發伺服器（5173，支援熱更新）
cd frontend
npm run dev
```

在瀏覽器開啟 Vite 顯示的網址（預設 `http://127.0.0.1:5173`）。修改 Vue 檔案後會自動重新整理。

---

## 介面說明

```
┌─────────────────────────────────────────────────────┐
│  Gazō 画像を集める      [?使用教學] Danbooru & Yande│
├──────────────────┬──────────────────────────────────┤
│  Danbooru│Yande  │  Danbooru 日誌 │ Yande.re 日誌   │
│──────────────────│─────────────────────────────────-│
│  搜尋關鍵字      │  [狀態燈] 閒置/執行/暫停/中止    │
│  儲存目錄        │                                   │
│  [含已刪除] 開關 │  2026-05-07 [INFO] 正在搜尋...   │
│  [▶開始][⏸][⏹] │  2026-05-07 [INFO] 下載: xxx.jpg │
│──────────────────│                                   │
│  下載紀錄        │                                   │
│  D hatsune_miku  │                                   │
│  Y shingeki ...  │                                   │
└──────────────────┴──────────────────────────────────┘
```

| 區域 | 說明 |
|------|------|
| 左側分頁 | 切換 Danbooru / Yande.re 設定表單 |
| 右側日誌分頁 | 獨立檢視各站點日誌，切換不會中斷任務 |
| 按鈕區 | ▶ 開始、⏸ 暫停 / 繼續、⏹ 中止（含二次確認）|
| 狀態指示燈 | 綠色呼吸=執行中，橘色=已暫停，紅色呼吸=正在中止，紅色=已中止/錯誤，綠色恆亮=完成 |
| 角標小圓點 | 分頁右上角小圓點，任務執行中會出現，方便跨分頁掌握狀態 |
| 使用教學按鈕 | 右上角「? 使用教學」，點擊後彈出完整教學，內容與本文件一致 |

---

## Danbooru 使用說明

### 1. 設定 API 驗證

Danbooru 匿名存取受限（僅能搜尋安全級別內容，每頁限 20 筆）。建議設定 API Key：

1. 註冊並登入 [danbooru.donmai.us](https://danbooru.donmai.us)
2. 進入個人主頁 → **API Key** 頁面，建立 Key
   - **Permissions**：選 `All` 最省事；若想套用最小權限，請選 `Scoped` 並只勾選 `posts:index` 即可，本專案僅會呼叫 `/posts.json` 一個端點
   - 下載「已刪除圖片」依賴的是**帳號等級**（通常需要 Gold+ 會員），與 API Key 權限無關
3. 將專案根目錄的 `.env.example` 複製為 `.env`，填入憑證：

```bash
DANBOORU_LOGIN=你的使用者名稱
DANBOORU_API_KEY=你的 API Key
```

> `.env` 已列入 `.gitignore`，不會被上傳到 GitHub。程式啟動時會自動載入。

### 2. 搜尋語法

Danbooru 以標籤組合搜尋，多個標籤以空白分隔：

| 範例 | 說明 |
|------|------|
| `hatsune_miku` | 搜尋初音未來相關圖片 |
| `shingeki_no_kyojin` | 搜尋進擊的巨人相關圖片 |
| `hatsune_miku solo` | 多標籤組合 |

> 標籤名稱可於 Danbooru 搜尋框中確認，單字之間以底線連接。

### 3. 含已刪除圖片

開啟後會額外搜尋 `status:deleted` 的貼文並一併下載。已刪除貼文可能無法取得原圖連結，會自動略過。

### 4. 檔案儲存結構

```
downloads/
└── {搜尋關鍵字}/
    └── danbooru/
        └── {作者名}/
            ├── shingeki_no_kyojin(artist_a)_eren_yeager01.jpg
            └── shingeki_no_kyojin(artist_b)_unknown02.png
```

---

## Yande.re 使用說明

### 1. 搜尋語法

Yande.re 同樣使用標籤搜尋：

| 範例 | 說明 |
|------|------|
| `hatsune_miku` | 搜尋初音未來 |
| `hatsune_miku rating:s` | 僅搜尋安全級別 |

### 2. 標籤類型查詢

首次下載某個搜尋關鍵字時，程式會批次查詢所有標籤的類型（作者 / 角色 / 版權等），用於自動分類檔名與目錄。此步驟會略慢，屬於正常現象。

### 3. 檔案儲存結構

```
downloads/
└── {搜尋關鍵字}/
    └── yande/
        └── {作者名}/
            ├── hatsune_miku(artist_a)_hatsune_miku01.jpg
            └── hatsune_miku(unknown)02.jpg
```

---

## 下載紀錄管理

程式會在 `downloads/` 目錄下儲存兩個紀錄檔：

| 檔案 | 說明 |
|------|------|
| `.downloaded_danbooru.json` | Danbooru 已下載貼文 ID |
| `.downloaded_yande.json` | Yande.re 已下載貼文 ID |

兩個站點的紀錄完全獨立，重設一個不會影響另一個。

### 重設紀錄

在介面左側的下載紀錄區，點擊每筆紀錄右側的 **✕** 按鈕，確認後即可清除該搜尋關鍵字的下載紀錄。下次執行時會重新下載所有圖片。

---

## 檔案結構

```
D:\crawler\
├── app.py                      # Flask 後端，提供 Web API
├── danbooru_crawler.py         # Danbooru 爬蟲核心
├── yande_crawler.py            # Yande.re 爬蟲核心
├── requirements.txt            # Python 套件清單
├── README.md                   # 英文版 README
├── README.zh-CN.md             # 简体中文
├── README.zh-TW.md             # 本檔（繁體中文）
├── README.ja.md                # 日本語
├── LICENSE                     # MIT 授權條款
├── .env.example                # 環境變數範本
├── .gitignore                  # Git 忽略規則
├── frontend/                   # Vue 3 + Vite 前端原始碼
│   ├── public/
│   │   └── logo/               # 專案 Logo（建置後置於 /logo/）
│   ├── src/
│   │   ├── components/         # 標頭、表單、日誌、紀錄、教學
│   │   ├── api.ts              # 封裝 /api 呼叫
│   │   ├── useTasks.ts         # 任務狀態 + SSE
│   │   └── App.vue
│   ├── index.html
│   ├── vite.config.ts          # 開發代理 /api → 5000
│   └── package.json
├── static_dist/                # 前端建置產物（npm run build 生成；已 gitignore）
├── downloads/                  # 圖片下載目錄（已 gitignore）
│   ├── .downloaded_danbooru.json
│   └── .downloaded_yande.json
└── venv/                       # Python 虛擬環境（已 gitignore）
```

---

## 命令列直接使用

不啟動 Web 介面，也可直接於終端機執行爬蟲：

```bash
# Danbooru
python danbooru_crawler.py

# Yande.re
python yande_crawler.py
```

依提示選擇操作：
- `1` 開始下載
- `2` 重設指定搜尋關鍵字的紀錄
- `3` 檢視所有下載紀錄

---

## 常見問題

**Q: 執行時遇到 403 錯誤？**
A: Danbooru 匿名存取受限，請於專案根目錄建立 `.env` 並填寫 API 驗證資訊（參考 `.env.example`）。

**Q: 圖片下載速度慢？**
A: 程式每張圖片之間有 0.5~1 秒間隔，用以避免觸發站點的請求頻率限制，屬於正常現象。

**Q: 部分圖片沒有下載連結？**
A: 已刪除貼文的原圖可能已從伺服器移除，程式會自動略過並於日誌中提示。

**Q: 切換分頁後任務還在執行嗎？**
A: 是的。切換分頁只是切換介面顯示，背景任務不受影響。右側日誌面板可隨時切換檢視兩個站點各自的即時日誌。

**Q: 如何暫停任務？**
A: 點擊開始按鈕旁的 **⏸** 按鈕，任務會在當前圖片下載完成後暫停（不會於中途截斷檔案）。點擊 **▶** 繼續。

**Q: 如何中止任務？**
A: 點擊 **⏹** 中止按鈕，於確認視窗確認後，任務會在當前圖片下載完成後離開（同樣不會截斷檔案）。已下載的圖片與紀錄會全部保留，下次執行時會自動跳過。中止 Danbooru 任務不會影響正在執行的 Yande 任務，兩者完全獨立。

**Q: 要更換搜尋關鍵字怎麼辦？**
A: 先點 **⏹** 中止當前任務，待狀態變為「已中止」後修改搜尋關鍵字，再點開始即可。不需重新整理頁面，另一個站點的任務也不會受影響。

**Q: 意外關閉頁面後，任務還在嗎？**
A: 關閉瀏覽器只會切斷前端連線，背景 Flask 服務與下載執行緒仍在執行。重新開啟頁面後可看到最新狀態。但關閉 `app.py` 行程（Ctrl+C）會終止所有任務。

**Q: 兩個站點可以同時執行嗎？**
A: 可以。Danbooru 與 Yande.re 屬於兩個獨立網域，同時執行一個 Danbooru 任務與一個 Yande.re 任務完全沒問題，不會互相影響。但不建議在同一站點同時執行多個任務（請求頻率會疊加，容易觸發限流）。

---

## License

本專案以 [MIT License](LICENSE) 授權。您可以自由使用、修改、散佈本專案的程式碼，僅需保留原始版權宣告。

Copyright © 2026 ChuUNiMuggle
