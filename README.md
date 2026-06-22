# shogi-db

将棋棋譜の保存・分析を行う個人用データベース。

水匠の解析結果を含む KIF 棋譜を登録し、局面ごとの評価値・候補手・読み筋を蓄積する。棋譜ビューアで盤面と評価値グラフを確認しながら、苦手局面の発見や戦法分析に活用する。

## ドキュメント

| ファイル                                        | 内容                             |
| ----------------------------------------------- | -------------------------------- |
| [00_overview.md](./docs/00_overview.md)         | プロジェクト概要・目的・開発方針 |
| [01_requirements.md](./docs/01_requirements.md) | 要件定義                         |
| [02_architecture.md](./docs/02_architecture.md) | システムアーキテクチャ           |
| [03_database.md](./docs/03_database.md)         | DB 設計・スキーマ                |
| [04_roadmap.md](./docs/04_roadmap.md)           | 開発ロードマップ                 |
| [ui/viewer.md](./docs/ui/viewer.md)             | 棋譜ビューア UI 仕様             |

## 機能概要

```
棋譜（KIF / 水匠解析付き）
        ↓
   KIF パーサー
        ↓
  SFEN 生成・保存
        ↓
┌───────────────────┐
│  対局DB  局面DB   │
└───────────────────┘
        ↓
棋譜ビューア ／ 評価値グラフ ／ 定跡DB
```

## フェーズ別ロードマップ（概要）

- **Phase 1 MVP** — KIF 読み込み・棋譜ビューア・評価値グラフ
- **Phase 2** — 戦法・囲い判定、悪手分析
- **Phase 3** — 定跡 DB 生成・自分専用定跡
- **Phase 4** — AI による局面解説

## Windows exe のビルド方法

Windows環境で実行する。

### 1. 仮想環境を作成

```bash
python -m venv .venv-win
source .venv-win/Scripts/activate
```

### 2. PyInstaller をインストール

```bash
python -m pip install --upgrade pip
python -m pip install pyinstaller
```

### 3. ビルド

```bash
python -m PyInstaller shogi-db.spec
```

### 4. 起動

```bash
./dist/shogi-db/shogi-db.exe
```

## 注意

水匠エンジンはネットワーク共有上では起動に失敗することがあるため、ローカルフォルダに配置する。

例:

```text
C:\Users\suton\tools\Suisho5-AVX2.exe
```

設定ファイルは以下に保存される。

```text
C:\Users\<ユーザー名>\AppData\Roaming\shogi-db\config.json
```
