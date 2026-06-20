# システムアーキテクチャ

## 全体構成

```
┌─────────────────────────────────────────┐
│              Browser (Frontend)          │
│  React + Vite                           │
│  ┌──────────┐  ┌──────────────────────┐ │
│  │ 対局一覧  │  │ 棋譜ビューア         │ │
│  │          │  │ 盤面 ／ 評価値グラフ  │ │
│  └──────────┘  └──────────────────────┘ │
└────────────────────┬────────────────────┘
                     │ REST API (JSON)
┌────────────────────▼────────────────────┐
│              Backend (API Server)        │
│  Python                                 │
│  ┌──────────┐  ┌────────┐  ┌─────────┐ │
│  │KIF Parser│  │SFEN 生成│  │集計処理 │ │
│  └──────────┘  └────────┘  └─────────┘ │
│  ┌────────────────────────────────────┐ │
│  │水匠 USI 連携（Phase 4 以降）       │ │
│  └────────────────────────────────────┘ │
└────────────────────┬────────────────────┘
                     │ SQLite (MVP)
┌────────────────────▼────────────────────┐
│                Database                  │
│  games / positions / openings           │
└─────────────────────────────────────────┘
```

## コンポーネント詳細

### Frontend

- **フレームワーク**: React + Vite（TypeScript）
- **盤面描画**: canvas または SVG（将棋盤コンポーネントを独自実装 or ライブラリ活用）
- **グラフ**: Recharts または Chart.js
- **状態管理**: Zustand or React Context（MVP は Context で十分）
- **API 通信**: fetch / axios

### Backend

- **API**: MVP は標準ライブラリの `http.server` とサービス層で実装。必要に応じて FastAPI へ移行
- **KIF パーサー**: 独自実装
- **SFEN 生成**: KIF 手を USI に変換し、盤面を手番ごとに再生して SFEN を生成
- **DB アクセス**: MVP は `sqlite3` + SQLite。必要に応じて SQLAlchemy へ移行
- **水匠連携**: Phase 4 以降で `subprocess` により水匠5を USI エンジンとして起動

### Database

- MVP: SQLite（ファイル 1 つで完結）
- 将来: PostgreSQL（サーバー運用時に移行）

詳細スキーマは [03_database.md](./03_database.md) を参照。

## データフロー

### KIF 取り込み

```
KIF ファイル
    ↓ POST /api/games/import
UTF-8 / CP932 を自動判定してテキスト化
    ↓
KIF パーサー（ヘッダー解析・指し手解析・評価値抽出）
    ↓
KIF 手 → USI → 局面再生 → SFEN 生成（手番ごと）
    ↓
games テーブルへ保存
positions テーブルへ保存（全手番分）
```

### 定跡 DB 連携

```
games / positions
    ↓
SFEN ごとに指し手を集計
    ↓
openings(source='self') へ保存
```

外部定跡 DB は、やねうら王 DB などを HiraganaSuisho / BookConv などで SFEN 列へ変換できる場合に `openings(source='yaneou')` などとして取り込む。

### 水匠解析連携（Phase 4 以降）

```
positions.sfen
    ↓
subprocess で Suisho5.exe を起動
    ↓
usi / isready
    ↓
position sfen ...
    ↓
go depth N
    ↓
info score / pv / bestmove を取得
    ↓
positions.eval / best_move / pv / candidates へ保存
```

水匠は shogi-db 内部に組み込まず、外部 USI エンジンプロセスとして扱う。GPLv3 対象部分を配布・改変する場合は GPL の条件に従う。

### 棋譜ビューア表示

```
GET /api/games          → 対局一覧
GET /api/games/{id}     → 対局詳細（ヘッダー情報）
GET /api/games/{id}/positions  → 全局面データ（SFEN・評価値・候補手）
```

## API エンドポイント一覧（MVP）

| メソッド | パス | 内容 |
|---|---|---|
| `POST` | `/api/games/import` | KIF ファイルを取り込む |
| `POST` | `/api/games/import-directory` | サーバー上のフォルダから KIF を一括取り込みする |
| `GET` | `/api/games` | 対局一覧を返す |
| `GET` | `/api/games/{id}` | 対局詳細を返す |
| `GET` | `/api/games/{id}/positions` | 全局面データを返す |
| `GET` | `/api/positions/{sfen}` | 特定局面の情報を返す（定跡 DB 参照） |

## API エンドポイント一覧（将来）

| メソッド | パス | 内容 |
|---|---|---|
| `POST` | `/api/positions/{id}/analyze` | 指定局面を水匠で解析する |
| `POST` | `/api/games/{id}/analyze` | 指定対局の全局面または未解析局面を水匠で解析する |

## ディレクトリ構成（予定）

```
shogi-db/
├── docs/                  # このドキュメント群
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI エントリーポイント
│   │   ├── parser/        # KIF パーサー
│   │   ├── models/        # SQLAlchemy モデル
│   │   ├── schemas/       # Pydantic スキーマ
│   │   └── routers/       # API ルーター
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── components/    # React コンポーネント
    │   │   ├── Board/     # 盤面
    │   │   ├── Graph/     # 評価値グラフ
    │   │   └── GameList/  # 対局一覧
    │   └── App.tsx
    └── package.json
```
