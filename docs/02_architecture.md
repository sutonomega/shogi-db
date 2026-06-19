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
│  Python + FastAPI                       │
│  ┌──────────┐  ┌────────┐  ┌─────────┐ │
│  │KIF Parser│  │SFEN 生成│  │集計処理 │ │
│  └──────────┘  └────────┘  └─────────┘ │
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

- **フレームワーク**: Python + FastAPI
- **KIF パーサー**: 独自実装（`python-shogi` ライブラリを補助的に利用）
- **SFEN 生成**: KIF を手番ごとに再生して SFEN を生成
- **DB アクセス**: SQLAlchemy + SQLite

### Database

- MVP: SQLite（ファイル 1 つで完結）
- 将来: PostgreSQL（サーバー運用時に移行）

詳細スキーマは [03_database.md](./03_database.md) を参照。

## データフロー

### KIF 取り込み

```
KIF ファイル
    ↓ POST /api/games/import
KIF パーサー（ヘッダー解析・指し手解析・評価値抽出）
    ↓
局面再生 → SFEN 生成（手番ごと）
    ↓
games テーブルへ保存
positions テーブルへ保存（全手番分）
```

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
| `GET` | `/api/games` | 対局一覧を返す |
| `GET` | `/api/games/{id}` | 対局詳細を返す |
| `GET` | `/api/games/{id}/positions` | 全局面データを返す |
| `GET` | `/api/positions/{sfen}` | 特定局面の情報を返す（定跡 DB 参照） |

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
