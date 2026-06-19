"""
KifParser のユニットテスト

実行:
    python3 -m unittest discover -s test -v
"""

import unittest

from src.kif_parser import KifParser


# ---------------------------------------------------------------------------
# テスト用 KIF サンプル
# ---------------------------------------------------------------------------

KIF_NO_ANALYSIS = """\
開始日時：2024/01/15 20:00:00
終了日時：2024/01/15 20:45:00
手合割：平手
先手：テストA
後手：テストB
手数----指手---------消費時間--
   1 ７六歩(77)    ( 0:05/00:00:05)
   2 ３四歩(33)    ( 0:03/00:00:03)
   3 ２六歩(27)    ( 0:04/00:00:09)
   4 投了
まで3手で先手の勝ち
"""

KIF_WITH_ANALYSIS = """\
開始日時：2024/02/10 19:00:00
手合割：平手
先手：解析太郎
後手：棋譜花子
手数----指手---------消費時間--
   1 ７六歩(77)    ( 0:02/00:00:02)
**解析 0
*評価値 +64  読み筋 7g7f 3c3d 2g2f
* 2g2f +55
* 6i7h +40
   2 ３四歩(33)    ( 0:01/00:00:01)
**解析 0
*評価値 +44  読み筋 3c3d 2g2f 8c8d
* 8c8d +30
   3 ２六歩(27)    ( 0:03/00:00:05)
**解析 0
*評価値 +80  読み筋 2g2f 8c8d 2f2e
   4 投了
まで3手で先手の勝ち
"""

KIF_WITH_TSUMI = """\
開始日時：2024/03/01 10:00:00
手合割：平手
先手：詰将棋A
後手：詰将棋B
手数----指手---------消費時間--
  77 ５二金(61)    ( 0:10/00:10:00)
**解析 0
*評価値 +詰 13  読み筋 5i5h 4h5g 5h4h
  78 投了
まで77手で先手の勝ち
"""

KIF_DRAW = """\
開始日時：2024/04/01 12:00:00
手合割：平手
先手：引き分けA
後手：引き分けB
手数----指手---------消費時間--
   1 ７六歩(77)    ( 0:05/00:00:05)
   2 ３四歩(33)    ( 0:03/00:00:03)
   3 千日手
"""

KIF_NO_HEADER_DATE = """\
手合割：平手
先手：名無しA
後手：名無しB
手数----指手---------消費時間--
   1 ７六歩(77)
   2 投了
まで1手で先手の勝ち
"""


# ---------------------------------------------------------------------------
# テストクラス
# ---------------------------------------------------------------------------

class TestHeader(unittest.TestCase):
    def setUp(self):
        self.record = KifParser().parse(KIF_NO_ANALYSIS)

    def test_played_at(self):
        self.assertEqual(self.record.played_at, "2024/01/15 20:00:00")

    def test_black(self):
        self.assertEqual(self.record.black, "テストA")

    def test_white(self):
        self.assertEqual(self.record.white, "テストB")

    def test_played_at_missing(self):
        record = KifParser().parse(KIF_NO_HEADER_DATE)
        self.assertIsNone(record.played_at)


class TestWinner(unittest.TestCase):
    def test_black_wins(self):
        record = KifParser().parse(KIF_NO_ANALYSIS)
        self.assertEqual(record.winner, "black")

    def test_white_wins(self):
        kif = """\
手合割：平手
先手：A
後手：B
手数----指手---------消費時間--
   1 ７六歩(77)
   2 ３四歩(33)
   3 ２六歩(27)
   4 ８四歩(83)
   5 投了
"""
        record = KifParser().parse(kif)
        self.assertEqual(record.winner, "white")

    def test_draw_sennichite(self):
        record = KifParser().parse(KIF_DRAW)
        self.assertEqual(record.winner, "draw")


class TestMoves(unittest.TestCase):
    def setUp(self):
        self.record = KifParser().parse(KIF_NO_ANALYSIS)

    def test_move_count(self):
        self.assertEqual(self.record.move_count, 3)
        self.assertEqual(len(self.record.moves), 3)

    def test_move_kif(self):
        self.assertEqual(self.record.moves[0].move_kif, "７六歩(77)")
        self.assertEqual(self.record.moves[1].move_kif, "３四歩(33)")

    def test_move_number(self):
        self.assertEqual(self.record.moves[0].move_number, 1)
        self.assertEqual(self.record.moves[2].move_number, 3)

    def test_time_str(self):
        self.assertEqual(self.record.moves[0].time_str, "0:05")


class TestNoAnalysis(unittest.TestCase):
    def test_all_eval_none(self):
        record = KifParser().parse(KIF_NO_ANALYSIS)
        for move in record.moves:
            self.assertIsNone(move.eval)
            self.assertIsNone(move.best_move)
            self.assertIsNone(move.pv)
            self.assertEqual(move.candidates, [])


class TestWithAnalysis(unittest.TestCase):
    def setUp(self):
        self.record = KifParser().parse(KIF_WITH_ANALYSIS)

    def test_move_count(self):
        self.assertEqual(self.record.move_count, 3)

    def test_first_eval(self):
        self.assertEqual(self.record.moves[0].eval, 64)

    def test_second_eval(self):
        self.assertEqual(self.record.moves[1].eval, 44)

    def test_best_move(self):
        self.assertEqual(self.record.moves[0].best_move, "7g7f")

    def test_pv(self):
        self.assertEqual(self.record.moves[0].pv, "7g7f 3c3d 2g2f")

    def test_candidates(self):
        candidates = self.record.moves[0].candidates
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].move, "2g2f")
        self.assertEqual(candidates[0].eval, 55)
        self.assertEqual(candidates[1].move, "6i7h")
        self.assertEqual(candidates[1].eval, 40)

    def test_no_candidates(self):
        self.assertEqual(self.record.moves[2].candidates, [])

    def test_winner(self):
        self.assertEqual(self.record.winner, "black")


class TestTsumi(unittest.TestCase):
    def test_positive_tsumi(self):
        record = KifParser().parse(KIF_WITH_TSUMI)
        self.assertEqual(record.moves[0].eval, 100_000)

    def test_negative_tsumi(self):
        kif = """\
手合割：平手
先手：A
後手：B
手数----指手---------消費時間--
   1 ７六歩(77)
**解析 0
*評価値 -詰 5  読み筋 7g7f
   2 投了
"""
        record = KifParser().parse(kif)
        self.assertEqual(record.moves[0].eval, -100_000)


class TestRawKif(unittest.TestCase):
    def test_raw_kif_preserved(self):
        record = KifParser().parse(KIF_NO_ANALYSIS)
        self.assertEqual(record.raw_kif, KIF_NO_ANALYSIS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
