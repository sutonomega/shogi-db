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

### KIF 登録

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
openings(source='professional') へ保存
```

外部定跡 DB は、やねうら王 DB などを HiraganaSuisho / BookConv などで SFEN 列へ変換できる場合に `openings(source='yaneou')` などとして登録する。

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

### 局面解説プロンプト生成（Phase 4）

```
positions.id
    ↓
positions から SFEN / 評価値 / 最善手 / 読み筋 / 候補手を取得
    ↓
openings(source='professional') から同一 SFEN の登録済み定跡候補を取得
    ↓
解説材料を JSON で正規化
    ↓
LLM に渡す日本語プロンプトを生成
```

プロンプトでは、局面データを「確定情報」として列挙し、評価値悪化の理由や改善案は「推測」として扱うよう指示する。候補手・読み筋・評価値などの不足項目がある場合は、不足を明示し、断定的な説明を避ける。

`GET /api/positions/{id}/explanation-prompt` でプロンプトと入力材料を返す。

### 局面解説生成（Phase 4）

```
GET /api/positions/{id}/explanation-prompt と同じ材料
    ↓
プロンプトを生成
    ↓
SHOGI_DB_LLM_COMMAND または request body の llm_command を外部プロセスとして起動
    ↓
プロンプトを stdin に渡す
    ↓
stdout を explanation として返す
```

LLM は shogi-db に組み込まず、外部コマンドとして扱う。これにより OpenAI CLI、Ollama、独自スクリプトなどを同じ API から利用できる。初期実装では生成結果の永続化は行わない。

### 悪手理由解説プロンプト生成（Phase 4）

```
game_id + move_number
    ↓
positions から着手前局面と着手後局面を取得
    ↓
前後 SFEN / 実戦手 / 前後評価値 / 評価値低下量 / 候補手 / 読み筋を正規化
    ↓
評価値低下量から解説の要否と粒度を判定
    ↓
LLM に渡す日本語プロンプトを生成
```

`GET /api/blunders/explanation-prompt?game_id={id}&move_number={n}` で、悪手ランキングの各手に対応する理由解説用プロンプトと入力材料を返す。初期実装では生成実行と保存は行わず、局面解説と同じ方針で、確定情報・根拠・推測・不足情報を分ける。

`POST /api/blunders/explain` は request body の `game_id` / `move_number` から同じプロンプトを生成し、`llm_command` または `SHOGI_DB_LLM_COMMAND` で指定した外部 LLM コマンドへ標準入力として渡す。初期実装では生成結果の永続化は行わない。
評価値低下量が 200 点未満の場合は 400 を返し、LLM 呼び出しを行わない。200 点以上 500 点未満は簡易解説、500 点以上は詳細解説を促す材料をプロンプトへ含める。

### 定跡比較プロンプト生成（Phase 4）

```
positions.id
    ↓
positions.sfen を比較キーにする
    ↓
list_move_frequencies(sfen) で自分の実戦頻度手を取得
    ↓
openings(source=...) で source 別の定跡候補を取得
    ↓
positions.best_move / candidates からエンジン候補手を取得
    ↓
LLM に渡す日本語プロンプトを生成
```

`GET /api/positions/{id}/opening-comparison-prompt` で、指定局面の定跡比較用プロンプトと入力材料を返す。初期実装では source は `self` を既定にし、`sources=self,yaneou,professional` のようなカンマ区切り指定も受け付ける。

`POST /api/positions/{id}/opening-comparison-explain` は同じ比較材料からプロンプトを作り、`llm_command` または `SHOGI_DB_LLM_COMMAND` で指定した外部 LLM コマンドへ標準入力として渡す。初期実装では生成結果の永続化は行わない。

### 棋譜ビューア表示

```
GET /api/games          → 対局一覧
GET /api/games/{id}     → 対局詳細（ヘッダー情報）
GET /api/games/{id}/positions  → 全局面データ（SFEN・評価値・候補手）
```

## API エンドポイント一覧（MVP）

| メソッド | パス | 内容 |
|---|---|---|
| `POST` | `/api/games/import` | KIF ファイルを登録する |
| `POST` | `/api/games/import-directory` | サーバー上のフォルダから KIF を一括登録する（`async=true` でジョブ起動） |
| `GET` | `/api/games/import-directory/jobs/{id}` | 一括登録ジョブの進捗を返す |
| `POST` | `/api/games/import-directory/jobs/{id}/cancel` | 一括登録ジョブのキャンセルを要求する |
| `GET` | `/api/games` | 対局一覧を返す |
| `GET` | `/api/games/{id}` | 対局詳細を返す |
| `GET` | `/api/games/{id}/positions` | 全局面データを返す |
| `GET` | `/api/positions?sfen={sfen}` | 特定局面の指し手頻度を返す（定跡 DB 参照） |
| `GET` | `/api/openings?sfen={sfen}&source=professional` | 保存済み定跡 DB から特定局面の候補手を返す |
| `POST` | `/api/openings/import?source=professional` | 定跡用 KIF を openings に登録する |
| `POST` | `/api/openings/import-directory` | サーバー上のフォルダから定跡用 KIF を一括登録する（`async=true` でジョブ起動） |
| `GET` | `/api/openings/import-directory/jobs/{id}` | 定跡一括登録ジョブの進捗を返す |
| `POST` | `/api/openings/import-directory/jobs/{id}/cancel` | 定跡一括登録ジョブのキャンセルを要求する |
| `POST` | `/api/openings/rebuild` | 保存済み局面から定跡 DB を再生成する（`async=true` でジョブ起動） |
| `GET` | `/api/openings/rebuild/jobs/{id}` | 定跡 DB 更新ジョブの進捗を返す |
| `POST` | `/api/openings/rebuild/jobs/{id}/cancel` | 定跡 DB 更新ジョブのキャンセルを要求する |
| `POST` | `/api/positions/{id}/analyze` | 指定局面を外部USIエンジンで解析する |
| `GET` | `/api/blunders/explanation-prompt?game_id={id}&move_number={n}` | 悪手理由解説用プロンプトを返す |
| `POST` | `/api/blunders/explain` | 悪手理由解説を外部 LLM コマンドで生成する |
| `GET` | `/api/positions/{id}/explanation-prompt` | 指定局面の解説用プロンプトを返す |
| `POST` | `/api/positions/{id}/explain` | 指定局面の解説を外部 LLM コマンドで生成する |
| `GET` | `/api/positions/{id}/opening-comparison-prompt?sources=self,yaneou` | 指定局面の定跡比較用プロンプトを返す |
| `POST` | `/api/positions/{id}/opening-comparison-explain` | 指定局面の定跡比較解説を外部 LLM コマンドで生成する |

## API エンドポイント一覧（将来）

| メソッド | パス | 内容 |
|---|---|---|
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
