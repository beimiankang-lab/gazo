<p align="center">
  <img src="frontend/public/logo/logo.png" alt="Gazō" width="140">
</p>

<h1 align="center">Gazō — Booru Image Crawler</h1>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.zh-CN.md">简体中文</a> ·
  <a href="README.zh-TW.md">繁體中文</a> ·
  <strong>日本語</strong>
</p>

<p align="center"><em>画像を集める — <a href="https://danbooru.donmai.us">Danbooru</a> と <a href="https://yande.re">Yande.re</a> から画像を一括ダウンロードするツール。Web UI 付きで、リアルタイムログ・一時停止/再開・中断・ダウンロード履歴管理に対応しています。</em></p>

---

## 目次

- [動作環境](#動作環境)
- [インストール](#インストール)
- [起動方法](#起動方法)
- [画面構成](#画面構成)
- [Danbooru ガイド](#danbooru-ガイド)
- [Yande.re ガイド](#yandere-ガイド)
- [ダウンロード履歴の管理](#ダウンロード履歴の管理)
- [ファイル構成](#ファイル構成)
- [CLI での利用](#cli-での利用)
- [FAQ](#faq)

---

## 動作環境

- Python 3.10 以上
- Node.js 20+ と npm（フロントエンドのビルドに必要。ビルド済み成果物のみ使う場合は不要）
- Danbooru / Yande.re に接続できるネットワーク（必要に応じてプロキシをご用意ください）

---

## インストール

```bash
# 1. プロジェクトディレクトリへ移動
cd D:\crawler

# 2. 仮想環境の作成（任意、推奨）
python -m venv venv
venv\Scripts\activate

# 3. 依存関係のインストール
pip install -r requirements.txt
```

---

## 起動方法

### 本番モード（1 ポートで完結）

フロントエンドは `frontend/` 配下で Vue 3 + Vite を使用しています。初回はまず静的ファイルをビルドしてください：

```bash
# 1. フロントエンドのビルド（初回 clone 時やフロント修正後に実行）
cd frontend
npm install
npm run build
cd ..

# 2. バックエンドを起動。Flask がビルド済み静的ファイルを配信します
python app.py
```

ブラウザで以下を開きます：

```
http://127.0.0.1:5173
```

> まだビルドしていない場合、`python app.py` はエラーで停止し、`npm run build` を実行するよう促します。

### 開発モード（ホットリロード）

フロントエンドを編集する場合はフロント/バックエンドを別々に立ち上げると便利です。Vite は `/api` を Flask にプロキシします：

```bash
# ターミナル A：Flask（デフォルトポート 5173）
python app.py

# ターミナル B：Vite 開発サーバー（5174、ホットリロードあり）
cd frontend
npm run dev
```

Vite が表示する URL（既定では `http://127.0.0.1:5174`）を開きます。Vue ファイルを編集すると自動で再読み込みされます。

---

## 画面構成

```
┌─────────────────────────────────────────────────────┐
│  Gazō 画像を集める       [?ヘルプ] Danbooru & Yande │
├──────────────────┬──────────────────────────────────┤
│  Danbooru│Yande  │  Danbooru ログ │ Yande.re ログ   │
│──────────────────│─────────────────────────────────-│
│  タグ            │  [状態] 待機/実行/停止/中断      │
│  保存ディレクトリ│                                   │
│  [削除含める] ON │  2026-05-07 [INFO] 検索中...     │
│  [▶開始][⏸][⏹] │  2026-05-07 [INFO] 取得: xxx.jpg │
│──────────────────│                                   │
│  ダウンロード履歴│                                   │
│  D hatsune_miku  │                                   │
│  Y shingeki ...  │                                   │
└──────────────────┴──────────────────────────────────┘
```

| エリア | 説明 |
|--------|------|
| 左サイドバーのタブ | Danbooru / Yande.re の設定フォームを切り替え |
| 右側のログタブ | サイトごとのログを独立表示。切り替えてもタスクは中断されません |
| 操作ボタン | ▶ 開始、⏸ 一時停止 / 再開、⏹ 中断（確認ダイアログ付き） |
| 状態ランプ | 緑パルス=実行中、橙=一時停止、赤パルス=中断中、赤=停止/エラー、緑点灯=完了 |
| タブ右上のドット | タスク実行中に表示される小さな点。タブを切り替えても状態がひと目で分かります |
| ヘルプボタン | 右上の「? ヘルプ」で本ドキュメントと同じ内容のガイドを表示 |

---

## Danbooru ガイド

### 1. API 認証の設定

Danbooru の匿名アクセスは制限されています（セーフレート限定、1 ページ 20 件まで）。API キーの設定を推奨します：

1. [danbooru.donmai.us](https://danbooru.donmai.us) に登録・ログイン
2. マイページ → **API Key** で新しいキーを作成
   - **Permissions**：手軽に使うなら `All` を選択。最小権限で運用したい場合は `Scoped` を選び `posts:index` のみを有効化すれば十分です（本ツールは `/posts.json` しか呼びません）
   - 「削除済み画像」のダウンロードは**アカウントランク**（通常 Gold+ が必要）に依存し、API キーのスコープとは無関係です
3. プロジェクトルートの `.env.example` を `.env` にコピーし、認証情報を記入：

```bash
DANBOORU_LOGIN=ユーザー名
DANBOORU_API_KEY=取得した API Key
```

> `.env` はすでに `.gitignore` で除外されており、GitHub にはアップロードされません。起動時に自動で読み込まれます。

### 2. 検索構文

Danbooru はタグの組み合わせで検索します。複数タグはスペース区切りです：

| 例 | 説明 |
|----|------|
| `hatsune_miku` | 初音ミク関連 |
| `shingeki_no_kyojin` | 進撃の巨人関連 |
| `hatsune_miku solo` | 複数タグの組み合わせ |

> タグ名は Danbooru の検索ボックスで確認できます。タグ内の単語はアンダースコアで連結します。

### 3. 削除済み画像を含める

ON にすると `status:deleted` のポストも検索してダウンロードします。原画像が取得不能な場合は自動でスキップします。

### 4. ファイル保存構造

```
downloads/
└── {タグ}/
    └── danbooru/
        └── {作者名}/
            ├── shingeki_no_kyojin(artist_a)_eren_yeager01.jpg
            └── shingeki_no_kyojin(artist_b)_unknown02.png
```

---

## Yande.re ガイド

### 1. 検索構文

Yande.re もタグ検索を使います：

| 例 | 説明 |
|----|------|
| `hatsune_miku` | 初音ミクを検索 |
| `hatsune_miku rating:s` | セーフのみ検索 |

### 2. タグ種別の解決

あるクエリを初めてダウンロードする際、すべてのタグの種別（作者 / キャラクター / 版権 など）をまとめて取得し、ファイル名とディレクトリ分けに利用します。そのため初回は少し遅くなりますが、以降はキャッシュを再利用します。

### 3. ファイル保存構造

```
downloads/
└── {タグ}/
    └── yande/
        └── {作者名}/
            ├── hatsune_miku(artist_a)_hatsune_miku01.jpg
            └── hatsune_miku(unknown)02.jpg
```

---

## ダウンロード履歴の管理

`downloads/` 配下に 2 つの JSON ファイルが保存されます：

| ファイル | 説明 |
|----------|------|
| `.downloaded_danbooru.json` | Danbooru のダウンロード済みポスト ID |
| `.downloaded_yande.json` | Yande.re のダウンロード済みポスト ID |

2 サイトの履歴は完全に独立しており、片方をリセットしてももう片方には影響しません。

### 履歴のリセット

画面左側の「ダウンロード履歴」エリアで、各項目の右側にある **✕** ボタンを押して確認すると、そのクエリの履歴が削除されます。次回の実行で全画像が再ダウンロードされます。

---

## ファイル構成

```
D:\crawler\
├── app.py                      # Flask バックエンド（Web API を提供）
├── danbooru_crawler.py         # Danbooru クローラ本体
├── yande_crawler.py            # Yande.re クローラ本体
├── requirements.txt            # Python 依存
├── README.md                   # 英語版 README
├── README.zh-CN.md             # 简体中文
├── README.zh-TW.md             # 繁體中文
├── README.ja.md                # 本ファイル（日本語）
├── LICENSE                     # MIT ライセンス
├── .env.example                # 環境変数テンプレート
├── .gitignore                  # Git 除外ルール
├── frontend/                   # Vue 3 + Vite フロントエンド
│   ├── public/
│   │   └── logo/               # プロジェクト Logo（ビルド後は /logo/ で配信）
│   ├── src/
│   │   ├── components/         # ヘッダー、フォーム、ログ、履歴、ヘルプ
│   │   ├── api.ts              # /api 呼び出しのラッパ
│   │   ├── useTasks.ts         # タスク状態 + SSE
│   │   └── App.vue
│   ├── index.html
│   ├── vite.config.ts          # 開発時プロキシ /api → 5173
│   └── package.json
├── static_dist/                # フロントのビルド成果物（npm run build で生成、gitignore 済）
├── downloads/                  # 画像の保存先（gitignore 済）
│   ├── .downloaded_danbooru.json
│   └── .downloaded_yande.json
└── venv/                       # Python 仮想環境（gitignore 済）
```

---

## CLI での利用

Web UI を使わずにターミナルから直接クローラを実行することもできます：

```bash
# Danbooru
python danbooru_crawler.py

# Yande.re
python yande_crawler.py
```

プロンプトに従って選択してください：
- `1` ダウンロードを開始
- `2` 指定クエリの履歴をリセット
- `3` すべてのダウンロード履歴を表示

---

## FAQ

**Q: 実行時に 403 エラーが出ます。**
A: Danbooru の匿名アクセスは制限されています。プロジェクトルートに `.env` を作成し、`.env.example` を参考に API 認証情報を設定してください。

**Q: ダウンロードが遅い気がします。**
A: レート制限を避けるため、画像ごとに 0.5～1 秒の間隔を入れています。仕様です。

**Q: 一部の画像にダウンロードリンクがありません。**
A: 削除済みポストは原画像がサーバーから消えている場合があります。自動でスキップし、ログに記録します。

**Q: タブを切り替えたらタスクは停止しますか？**
A: いいえ。タブ切り替えは表示の切り替えのみで、バックグラウンドのタスクには影響しません。ログパネルも各サイトのリアルタイム出力を自由に行き来できます。

**Q: 一時停止するには？**
A: 開始ボタンの隣の **⏸** を押します。現在ダウンロード中の画像が完了してから一時停止します（ファイルが途中で切れることはありません）。**▶** で再開します。

**Q: タスクを中断するには？**
A: **⏹** を押し、確認ダイアログで承認すると、現在の画像のダウンロード完了後に終了します（同様にファイルは切られません）。ダウンロード済み画像と履歴は保持され、次回実行時に自動でスキップされます。Danbooru を中断しても実行中の Yande.re タスクには影響しません。両者は完全に独立しています。

**Q: タグを変更したい場合は？**
A: まず **⏹** で現在のタスクを停止し、状態が「中断」になってからタグを変更して開始ボタンを押してください。ページの再読み込みは不要で、もう一方のサイトのタスクも影響を受けません。

**Q: 誤ってページを閉じました。タスクは続いていますか？**
A: ブラウザを閉じてもフロントエンド接続が切れるだけで、Flask プロセスとダウンロードスレッドは実行を続けます。ページを再度開けば最新の状態が表示されます。ただし `app.py` 自体を停止（Ctrl+C）するとすべてのタスクが終了します。

**Q: 両サイトを同時実行できますか？**
A: できます。Danbooru と Yande.re は独立したドメインなので、Danbooru 1 本と Yande.re 1 本を並行実行しても問題ありません。一方、**同一サイト**に対して複数タスクを同時実行するのは非推奨です（リクエスト頻度が合算され、レート制限に引っかかりやすくなります）。

---

## License

本プロジェクトは [MIT License](LICENSE) の下で公開されています。原著作権表示を保持する限り、自由に利用・改変・再配布できます。

Copyright © 2026 ChuUNiMuggle
