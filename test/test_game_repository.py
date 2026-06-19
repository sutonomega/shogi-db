import json
import unittest

from src.game_repository import GameRepository
from src.kif_parser import KifParser
from src.sfen_generator import SfenGenerator


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


class TestGameRepository(unittest.TestCase):
    def setUp(self):
        self.repository = GameRepository()
        self.repository.init_schema()
        self.game = KifParser().parse(KIF_WITH_ANALYSIS)
        self.positions = SfenGenerator().generate(self.game)

    def tearDown(self):
        self.repository.close()

    def test_save_and_get_game(self):
        game_id = self.repository.save_game(self.game, self.positions)
        stored = self.repository.get_game(game_id)

        self.assertIsNotNone(stored)
        self.assertEqual(stored.played_at, "2024/02/10 19:00:00")
        self.assertEqual(stored.black, "解析太郎")
        self.assertEqual(stored.white, "棋譜花子")
        self.assertEqual(stored.winner, "black")
        self.assertEqual(stored.move_count, 3)
        self.assertIsNone(stored.strategy)
        self.assertIsNone(stored.enclosure)
        self.assertEqual(stored.raw_kif, KIF_WITH_ANALYSIS)

    def test_save_strategy(self):
        game_id = self.repository.save_game(
            self.game,
            self.positions,
            strategy="四間飛車",
        )
        stored = self.repository.get_game(game_id)

        self.assertEqual(stored.strategy, "四間飛車")

    def test_save_positions_with_sfen_and_analysis(self):
        game_id = self.repository.save_game(self.game, self.positions)
        stored_positions = self.repository.list_positions(game_id)

        self.assertEqual(len(stored_positions), 4)
        self.assertEqual(stored_positions[0].move_number, 0)
        self.assertEqual(stored_positions[0].move, None)
        self.assertEqual(
            stored_positions[0].sfen,
            "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1",
        )
        self.assertEqual(stored_positions[1].move_number, 1)
        self.assertEqual(stored_positions[1].move, "7g7f")
        self.assertEqual(stored_positions[1].eval, 64)
        self.assertEqual(stored_positions[1].best_move, "7g7f")
        self.assertEqual(stored_positions[1].pv, "7g7f 3c3d 2g2f")
        self.assertEqual(
            json.loads(stored_positions[1].candidates),
            [
                {"move": "2g2f", "eval": 55},
                {"move": "6i7h", "eval": 40},
            ],
        )

    def test_duplicate_raw_kif_returns_existing_game_id(self):
        first_id = self.repository.save_game(self.game, self.positions)
        second_id = self.repository.save_game(
            self.game,
            self.positions,
            strategy="四間飛車",
        )

        self.assertEqual(second_id, first_id)
        self.assertIsNone(self.repository.get_game(first_id).strategy)
        count = self.repository.connection.execute(
            "SELECT COUNT(*) AS count FROM games"
        ).fetchone()["count"]
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
