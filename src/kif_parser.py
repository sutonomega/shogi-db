"""
KIF パーサー

対応フォーマット:
  - 通常の KIF（解析なし）
  - 水匠（ShogiGUI）解析付き KIF

解析付き KIF のコメント構造:
  指し手行の直後に以下のコメント行が続く
    **解析 0
    *評価値 <cp>  読み筋 <move1> <move2> ...
    * <候補手1> <cp1>
    * <候補手2> <cp2>
    ...
"""

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------

@dataclass
class Candidate:
    move: str       # USI 形式の手
    eval: int       # 評価値（先手視点 cp）


@dataclass
class MoveRecord:
    move_number: int
    move_kif: str           # KIF 表記（例: ７六歩(77)）
    move_usi: str | None    # USI 形式（例: 7g7f）。変換未対応時は None
    time_str: str | None    # 消費時間文字列（例: 0:01）
    eval: int | None                    # 評価値（先手視点 cp）。解析なしは None
    best_move: str | None               # 最善手 USI
    pv: str | None                      # 読み筋（スペース区切り USI）
    candidates: list[Candidate] = field(default_factory=list)


@dataclass
class GameRecord:
    """1対局分のパース結果"""
    # ヘッダー情報
    played_at: str | None       # 対局日時（文字列のまま保持）
    black: str                  # 先手
    white: str                  # 後手
    winner: str | None          # 'black' | 'white' | 'draw' | None
    move_count: int             # 総手数

    # 指し手・局面リスト
    moves: list[MoveRecord]

    # 生テキスト
    raw_kif: str


# ---------------------------------------------------------------------------
# パーサー本体
# ---------------------------------------------------------------------------

class KifParser:
    """
    KIF ファイルをパースして GameRecord を返す。

    使い方:
        parser = KifParser()
        record = parser.parse(kif_text)
    """

    # ヘッダー行のパターン
    _RE_PLAYED_AT = re.compile(r"^開始日時[：:]\s*(.+)")
    _RE_BLACK     = re.compile(r"^先手[：:]\s*(.+)")
    _RE_WHITE     = re.compile(r"^後手[：:]\s*(.+)")
    _RE_VARIATION = re.compile(r"^\s*変化[：:]")

    # 指し手行: "   1 ７六歩(77)   ( 0:01/00:00:01)"
    _RE_MOVE = re.compile(
        r"^\s*(\d+)\s+"         # 手数
        r"(.+?)"                 # 指し手（KIF 表記）
        r"(?:\s+\(\s*(\S+)/\S+\))?"  # 消費時間（省略可）
        r"\s*$"
    )

    # 終了行
    _RE_RESIGN   = re.compile(r"^\s*\d+\s+投了")
    _RE_TORYO    = re.compile(r"^\s*\d+\s+投了")
    _RE_SENNICHITE = re.compile(r"^\s*\d+\s+千日手")
    _RE_JISHOGI  = re.compile(r"^\s*\d+\s+持将棋")
    _RE_TSUMI    = re.compile(r"^\s*\d+\s+詰み")

    # 水匠解析コメント
    _RE_ANALYSIS_HEADER = re.compile(r"^\*\*(?:解析\s+\d+|対局\b)")
    _RE_INLINE_ANALYSIS = re.compile(
        r"評価値\s+([+\-]?\d+|[+\-]?詰\s*\d*)"
        r"(?:\s+読み筋\s+(.+))?"
    )
    _RE_EVAL_LINE = re.compile(
        r"^\*評価値\s+([+\-]?\d+|[+\-]?詰\s*\d*)"  # 評価値（数値 or 詰）
        r"(?:\s+読み筋\s+(.+))?"                     # 読み筋（省略可）
    )
    _RE_CANDIDATE = re.compile(
        r"^\*\s*(\S+)\s+([+\-]?\d+|[+\-]?詰\s*\d*)"
    )

    # 詰み評価値の変換
    _TSUMI_VALUE = 100_000

    def parse(self, kif_text: str) -> GameRecord:
        """KIF テキスト全体をパースして GameRecord を返す。"""
        lines = kif_text.splitlines()

        played_at: str | None = None
        black = "先手"
        white = "後手"
        winner: str | None = None
        moves: list[MoveRecord] = []
        pending_analysis: tuple[int | None, str | None, str | None, list[Candidate]] | None = None

        i = 0
        while i < len(lines):
            line = lines[i]

            if self._RE_VARIATION.match(line):
                break

            # --- ヘッダー解析 ---
            if m := self._RE_PLAYED_AT.match(line):
                played_at = m.group(1).strip()
                i += 1
                continue

            if m := self._RE_BLACK.match(line):
                black = m.group(1).strip()
                i += 1
                continue

            if m := self._RE_WHITE.match(line):
                white = m.group(1).strip()
                i += 1
                continue

            # --- 終了判定行 ---
            if self._RE_RESIGN.match(line):
                # 投了行の手数を取得: その手番のプレイヤーが投了した
                # 奇数手番 = 先手が投了 → 後手勝ち
                # 偶数手番 = 後手が投了 → 先手勝ち
                if m2 := re.match(r"^\s*(\d+)\s+投了", line):
                    resign_number = int(m2.group(1))
                    winner = "white" if resign_number % 2 == 1 else "black"
                i += 1
                continue

            if self._RE_SENNICHITE.match(line) or self._RE_JISHOGI.match(line):
                winner = "draw"
                i += 1
                continue

            # --- 指し手の前にある解析行 ---
            if self._RE_ANALYSIS_HEADER.match(line):
                eval_val, best_move, pv, candidates, consumed = \
                    self._parse_analysis_block(lines, i)
                pending_analysis = (eval_val, best_move, pv, candidates)
                i += consumed
                continue

            # --- 指し手行 ---
            if m := self._RE_MOVE.match(line):
                move_number = int(m.group(1))
                move_kif    = m.group(2).strip()
                time_str    = m.group(3)

                # 終了系の指し手テキストはスキップ
                if move_kif in ("投了", "中断", "千日手", "持将棋", "詰み", "切れ負け"):
                    i += 1
                    continue

                if pending_analysis is not None:
                    eval_val, best_move, pv, candidates = pending_analysis
                    consumed = 0
                    pending_analysis = None
                else:
                    # 解析コメントを先読み
                    eval_val, best_move, pv, candidates, consumed = \
                        self._parse_analysis_block(lines, i + 1)

                moves.append(MoveRecord(
                    move_number=move_number,
                    move_kif=move_kif,
                    move_usi=None,      # SFEN 生成ステップで付与
                    time_str=time_str,
                    eval=eval_val,
                    best_move=best_move,
                    pv=pv,
                    candidates=candidates,
                ))
                i += 1 + consumed
                continue

            # --- その他の行（コメント・空行など）は無視 ---
            i += 1

        return GameRecord(
            played_at=played_at,
            black=black,
            white=white,
            winner=winner,
            move_count=len(moves),
            moves=moves,
            raw_kif=kif_text,
        )

    # ------------------------------------------------------------------
    # 解析ブロックのパース
    # ------------------------------------------------------------------

    def _parse_analysis_block(
        self, lines: list[str], start: int
    ) -> tuple[int | None, str | None, str | None, list[Candidate], int]:
        """
        指し手行の直後に続く解析コメントブロックをパースする。

        Returns:
            (eval, best_move, pv, candidates, consumed_line_count)
        """
        eval_val: int | None = None
        best_move: str | None = None
        pv: str | None = None
        candidates: list[Candidate] = []
        consumed = 0

        i = start

        # "**解析 0" ヘッダーがなければ解析なし
        if i >= len(lines) or not self._RE_ANALYSIS_HEADER.match(lines[i]):
            return None, None, None, [], 0

        if m := self._RE_INLINE_ANALYSIS.search(lines[i]):
            eval_val = self._parse_eval(m.group(1))
            if m.group(2):
                best_move, pv = self._parse_pv(m.group(2))

        consumed += 1
        i += 1

        # "*評価値 ... 読み筋 ..." 行
        if i < len(lines):
            if m := self._RE_EVAL_LINE.match(lines[i]):
                eval_val = self._parse_eval(m.group(1))
                if m.group(2):
                    best_move, pv = self._parse_pv(m.group(2))
                consumed += 1
                i += 1

        # 候補手行 "* <手> <評価値>"
        while i < len(lines):
            if m := self._RE_CANDIDATE.match(lines[i]):
                candidates.append(Candidate(
                    move=m.group(1),
                    eval=self._parse_eval(m.group(2)),
                ))
                consumed += 1
                i += 1
            else:
                break

        return eval_val, best_move, pv, candidates, consumed

    # ------------------------------------------------------------------
    # ユーティリティ
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_pv(raw: str) -> tuple[str | None, str]:
        pv = raw.strip()
        moves_in_pv = pv.split()
        best_move = moves_in_pv[0] if moves_in_pv else None
        return best_move, pv

    @staticmethod
    def _parse_eval(raw: str) -> int:
        """
        評価値文字列を整数に変換する。
          "+詰 5"  → +100000
          "-詰 3"  → -100000
          "+320"   → 320
          "-80"    → -80
        """
        raw = raw.strip()
        if "詰" in raw:
            return KifParser._TSUMI_VALUE if raw.startswith("+") else -KifParser._TSUMI_VALUE
        # 矢印や余分な記号を除去
        raw = re.sub(r"[↑↓]", "", raw).strip()
        return int(raw)
