import unittest

from src.api import ApiError, ShogiDbApi
from src.game_repository import GameRepository


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
   3 投了
まで2手で後手の勝ち
"""

SHIKENBISHA_KIF = """\
開始日時：2024/03/01 10:00:00
手合割：平手
先手：振飛車太郎
後手：居飛車花子
手数----指手---------消費時間--
   1 ７六歩(77)    ( 0:01/00:00:01)
   2 ３四歩(33)    ( 0:01/00:00:01)
   3 ６八飛(28)    ( 0:01/00:00:02)
   4 投了
まで3手で先手の勝ち
"""

MINO_KIF = """\
開始日時：2024/03/02 10:00:00
手合割：平手
先手：囲い太郎
後手：居飛車花子
手数----指手---------消費時間--
   1 ７六歩(77)    ( 0:01/00:00:01)
   2 ３四歩(33)    ( 0:01/00:00:01)
   3 ６八飛(28)    ( 0:01/00:00:02)
   4 ８四歩(83)    ( 0:01/00:00:02)
   5 ４八玉(59)    ( 0:01/00:00:03)
   6 ８五歩(84)    ( 0:01/00:00:03)
   7 ３八玉(48)    ( 0:01/00:00:04)
   8 ６二銀(71)    ( 0:01/00:00:04)
   9 ２八玉(38)    ( 0:01/00:00:05)
  10 ４二玉(51)    ( 0:01/00:00:05)
  11 ３八銀(39)    ( 0:01/00:00:06)
  12 ３二玉(42)    ( 0:01/00:00:06)
  13 ５八金左(69)  ( 0:01/00:00:07)
  14 投了
まで13手で先手の勝ち
"""

KIF_WITH_BLUNDER = """\
開始日時：2024/03/03 10:00:00
手合割：平手
先手：悪手太郎
後手：悪手花子
手数----指手---------消費時間--
   1 ７六歩(77)
**解析 0
*評価値 +100  読み筋 7g7f 3c3d
   2 ３四歩(33)
**解析 0
*評価値 +80  読み筋 3c3d 2g2f
   3 ２六歩(27)
**解析 0
*評価値 -120  読み筋 2g2f 8c8d
   4 投了
まで3手で先手の勝ち
"""


class TestShogiDbApi(unittest.TestCase):
    def setUp(self):
        self.repository = GameRepository()
        self.api = ShogiDbApi(self.repository)

    def tearDown(self):
        self.repository.close()

    def test_import_game(self):
        response = self.api.import_game(KIF_WITH_ANALYSIS)

        self.assertEqual(response["game"]["id"], 1)
        self.assertEqual(response["game"]["black"], "解析太郎")
        self.assertEqual(response["game"]["white"], "棋譜花子")
        self.assertEqual(response["game"]["winner"], "white")
        self.assertEqual(response["game"]["move_count"], 2)
        self.assertIsNone(response["game"]["strategy"])
        self.assertIsNone(response["game"]["enclosure"])
        self.assertEqual(response["positions_count"], 3)

    def test_import_game_detects_strategy(self):
        response = self.api.import_game(SHIKENBISHA_KIF)

        self.assertEqual(response["game"]["strategy"], "四間飛車")

    def test_get_strategy_stats(self):
        self.api.import_game(SHIKENBISHA_KIF)

        response = self.api.get_strategy_stats()

        self.assertEqual(response["strategies"][0]["strategy"], "四間飛車")
        self.assertEqual(response["strategies"][0]["games"], 1)
        self.assertEqual(response["strategies"][0]["wins"], 1)
        self.assertEqual(response["strategies"][0]["losses"], 0)
        self.assertEqual(response["strategies"][0]["draws"], 0)
        self.assertEqual(response["strategies"][0]["win_rate"], 1.0)

    def test_import_game_detects_enclosure(self):
        response = self.api.import_game(MINO_KIF)

        self.assertEqual(response["game"]["enclosure"], "美濃囲い")

    def test_get_enclosure_stats(self):
        self.api.import_game(MINO_KIF)

        response = self.api.get_enclosure_stats()

        self.assertEqual(response["enclosures"][0]["enclosure"], "美濃囲い")
        self.assertEqual(response["enclosures"][0]["games"], 1)
        self.assertEqual(response["enclosures"][0]["wins"], 1)
        self.assertEqual(response["enclosures"][0]["losses"], 0)
        self.assertEqual(response["enclosures"][0]["draws"], 0)
        self.assertEqual(response["enclosures"][0]["win_rate"], 1.0)

    def test_get_blunders(self):
        self.api.import_game(KIF_WITH_BLUNDER)

        response = self.api.get_blunders()

        self.assertEqual(response["blunders"][0]["move_number"], 3)
        self.assertEqual(response["blunders"][0]["move"], "2g2f")
        self.assertEqual(response["blunders"][0]["eval_before"], 80)
        self.assertEqual(response["blunders"][0]["eval_after"], -120)
        self.assertEqual(response["blunders"][0]["eval_delta"], -200)
        self.assertEqual(response["blunders"][0]["loss"], 200)

    def test_list_games(self):
        self.api.import_game(KIF_WITH_ANALYSIS)

        response = self.api.list_games()

        self.assertEqual(len(response["games"]), 1)
        self.assertEqual(response["games"][0]["black"], "解析太郎")
        self.assertIn("strategy", response["games"][0])
        self.assertIn("enclosure", response["games"][0])
        self.assertNotIn("raw_kif", response["games"][0])

    def test_get_positions(self):
        game_id = self.api.import_game(KIF_WITH_ANALYSIS)["game"]["id"]

        response = self.api.get_positions(game_id)

        self.assertEqual(response["game"]["id"], game_id)
        self.assertIn("strategy", response["game"])
        self.assertEqual(len(response["positions"]), 3)
        self.assertEqual(response["positions"][0]["move"], None)
        self.assertEqual(response["positions"][1]["move"], "7g7f")
        self.assertEqual(response["positions"][1]["eval"], 64)
        self.assertEqual(
            response["positions"][1]["candidates"],
            [
                {"move": "2g2f", "eval": 55},
                {"move": "6i7h", "eval": 40},
            ],
        )

    def test_empty_import_raises_api_error(self):
        with self.assertRaises(ApiError) as context:
            self.api.import_game("")

        self.assertEqual(context.exception.status_code, 400)

    def test_missing_game_raises_404(self):
        with self.assertRaises(ApiError) as context:
            self.api.get_positions(999)

        self.assertEqual(context.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
