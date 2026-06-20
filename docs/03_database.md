# DB 設計

## テーブル一覧

| テーブル | 内容 |
|---|---|
| `games` | 対局情報 |
| `positions` | 局面情報（手番ごと） |
| `openings` | 定跡 DB |

---

## `games` — 対局情報

```sql
CREATE TABLE games (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    played_at   TEXT,           -- 対局日時 (ISO 8601)
    black       TEXT NOT NULL,  -- 先手
    white       TEXT NOT NULL,  -- 後手
    winner      TEXT,           -- 'black' | 'white' | 'draw' | NULL
    move_count  INTEGER,        -- 総手数
    strategy    TEXT,           -- 戦法タグ (Phase 2 以降)
    enclosure   TEXT,           -- 囲いタグ (Phase 2 以降)
    raw_kif     TEXT,           -- 元の KIF テキスト（フルテキスト保存）
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### フィールド補足

- `winner`: `NULL` は中断・不明
- `strategy` / `enclosure`: Phase 2 で shogi-extend adapter の判定結果を保存
- `raw_kif`: 元データを丸ごと保持しておくことで再パースが可能

---

## `positions` — 局面情報

```sql
CREATE TABLE positions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     INTEGER NOT NULL REFERENCES games(id),
    move_number INTEGER NOT NULL,  -- 手数（0 = 開始局面）
    sfen        TEXT NOT NULL,     -- 局面の SFEN 文字列
    move        TEXT,              -- この手番で指した手（USI 形式）
    eval        INTEGER,           -- 評価値（先手視点 cp）。NULL = 解析なし
    best_move   TEXT,              -- 水匠の最善手（USI 形式）
    pv          TEXT,              -- 読み筋（スペース区切り USI）
    candidates  TEXT,              -- 候補手 JSON（後述）
    analyzed_at TEXT,              -- 水匠などで後解析した日時（Phase 4 以降）
    engine_name TEXT,              -- 解析エンジン名（例: Suisho5）
    engine_depth INTEGER           -- 解析深さ（例: 18）
);

CREATE INDEX idx_positions_game_id ON positions(game_id);
CREATE INDEX idx_positions_sfen    ON positions(sfen);
```

### `candidates` JSON フォーマット

```json
[
  { "move": "7g7f", "eval": 120 },
  { "move": "2g2f", "eval": 95 },
  { "move": "6i7h", "eval": 80 }
]
```

### 後解析メタ情報

`analyzed_at`, `engine_name`, `engine_depth` は Phase 4 以降の水匠解析連携で使用する。MVP では NULL のまま扱う。

水匠解析では保存済み `positions.sfen` を USI エンジンに渡し、USI 出力から `eval`, `best_move`, `pv`, `candidates` を取得して同じ `positions` レコードへ追記する。

---

## `openings` — 定跡 DB

KIF を大量に取り込んで集計した局面ごとの指し手統計。

```sql
CREATE TABLE openings (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    source    TEXT NOT NULL DEFAULT 'self', -- self / yaneou / professional / floodgate など
    sfen      TEXT NOT NULL,   -- 局面の SFEN（持ち駒・手番を含む）
    move      TEXT NOT NULL,   -- 指し手（USI 形式）
    count     INTEGER NOT NULL DEFAULT 0,  -- 実戦での出現回数
    avg_eval  INTEGER,         -- 平均評価値（先手視点 cp）
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source, sfen, move)
);

CREATE INDEX idx_openings_sfen ON openings(sfen);
CREATE INDEX idx_openings_source_sfen ON openings(source, sfen);
```

### `source`

`openings.source` は定跡データの由来を表す。

| source | 内容 |
|---|---|
| `self` | 自分の実戦棋譜から集計した定跡 |
| `yaneou` | やねうら王定跡 DB など外部定跡 |
| `professional` | プロ棋譜由来の統計 |
| `floodgate` | Floodgate など公開対局由来の統計 |

MVP では `self` のみを扱い、外部 source は Phase 3 以降で取り込む。

### 保存例

```json
{
  "source": "self",
  "sfen": "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1",
  "move": "7g7f",
  "count": 120,
  "avg_eval": 135
}
```

### 生成フロー

```
games / positions テーブルの蓄積データ
    ↓
直前局面の sfen と次の指し手 move ごとに集計
    ↓
source='self' の count・avg_eval を更新（UPSERT）
    ↓
openings テーブルへ反映
```

外部定跡 DB は、変換ツールを利用して SFEN と指し手の列へ変換できる場合に `source` を分けて `openings` へ取り込む。

---

## 戦法・囲い集計クエリ例

### 戦法別勝率

```sql
SELECT
    strategy,
    COUNT(*) AS total,
    SUM(CASE WHEN winner = 'black' THEN 1 ELSE 0 END) AS black_wins,
    ROUND(
        100.0 * SUM(CASE WHEN winner = 'black' THEN 1 ELSE 0 END) / COUNT(*),
        1
    ) AS win_rate
FROM games
WHERE strategy IS NOT NULL
GROUP BY strategy
ORDER BY total DESC;
```

### 局面別出現回数・最頻手

```sql
SELECT
    sfen,
    move,
    count,
    avg_eval
FROM openings
WHERE sfen = :target_sfen
ORDER BY count DESC
LIMIT 5;
```
