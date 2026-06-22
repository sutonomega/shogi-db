import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.api import ApiError, ShogiDbApi
from src.game_repository import GameRepository, OpeningAggregate
from src.settings import AppSettings
from src.usi_engine import EngineAnalysis


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

    def test_import_game_bytes_accepts_utf8(self):
        response = self.api.import_game_bytes(KIF_WITH_ANALYSIS.encode("utf-8"))

        self.assertEqual(response["game"]["black"], "解析太郎")
        self.assertEqual(response["game"]["move_count"], 2)

    def test_import_game_bytes_accepts_cp932(self):
        response = self.api.import_game_bytes(KIF_WITH_ANALYSIS.encode("cp932"))

        self.assertEqual(response["game"]["black"], "解析太郎")
        self.assertEqual(response["game"]["move_count"], 2)

    def test_import_games_from_directory(self):
        with TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            (directory / "utf8.kif").write_bytes(KIF_WITH_ANALYSIS.encode("utf-8"))
            (directory / "cp932.kif").write_bytes(SHIKENBISHA_KIF.encode("cp932"))
            (directory / "memo.txt").write_text("ignored", encoding="utf-8")

            response = self.api.import_games_from_directory(str(directory))

        self.assertEqual(response["total"], 2)
        self.assertEqual(response["imported"], 2)
        self.assertEqual(response["failed"], 0)
        self.assertEqual(len(response["games"]), 2)
        self.assertEqual(len(self.api.list_games()["games"]), 2)
        self.assertNotIn("raw_kif", response["games"][0]["game"])

    def test_import_games_from_directory_reports_progress(self):
        progress = []
        with TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            (directory / "first.kif").write_bytes(KIF_WITH_ANALYSIS.encode("utf-8"))
            (directory / "second.kif").write_bytes(SHIKENBISHA_KIF.encode("utf-8"))

            self.api.import_games_from_directory(
                str(directory),
                progress_callback=lambda processed, total: progress.append((processed, total)),
            )

        self.assertEqual(progress[0], (0, 2))
        self.assertEqual(progress[-1], (2, 2))

    def test_import_games_from_directory_can_cancel(self):
        calls = []
        with TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            (directory / "first.kif").write_bytes(KIF_WITH_ANALYSIS.encode("utf-8"))
            (directory / "second.kif").write_bytes(SHIKENBISHA_KIF.encode("utf-8"))

            response = self.api.import_games_from_directory(
                str(directory),
                progress_callback=lambda processed, total: calls.append((processed, total)),
                should_cancel=lambda: bool(calls),
            )

        self.assertEqual(response["total"], 2)
        self.assertEqual(response["imported"], 0)

    def test_import_games_from_directory_continues_after_error(self):
        with TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            (directory / "ok.kif").write_bytes(KIF_WITH_ANALYSIS.encode("utf-8"))
            (directory / "bad.kif").write_bytes(b"\x81")

            response = self.api.import_games_from_directory(str(directory))

        self.assertEqual(response["total"], 2)
        self.assertEqual(response["imported"], 1)
        self.assertEqual(response["failed"], 1)
        self.assertIn("bad.kif", response["errors"][0]["path"])

    def test_import_games_from_directory_recursive(self):
        with TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            child = directory / "child"
            child.mkdir()
            (child / "game.kif").write_bytes(KIF_WITH_ANALYSIS.encode("utf-8"))

            non_recursive = self.api.import_games_from_directory(str(directory))
            recursive = self.api.import_games_from_directory(str(directory), recursive=True)

        self.assertEqual(non_recursive["total"], 0)
        self.assertEqual(recursive["total"], 1)
        self.assertEqual(recursive["imported"], 1)

    def test_import_games_from_directory_missing_path_raises_api_error(self):
        with self.assertRaises(ApiError) as context:
            self.api.import_games_from_directory("/path/that/does/not/exist")

        self.assertEqual(context.exception.status_code, 400)

    def test_import_opening_games_from_directory(self):
        progress = []
        with TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            (directory / "first.kif").write_bytes(KIF_WITH_ANALYSIS.encode("utf-8"))
            (directory / "second.kif").write_bytes(SHIKENBISHA_KIF.encode("cp932"))

            response = self.api.import_opening_games_from_directory(
                str(directory),
                source="professional",
                progress_callback=lambda processed, total: progress.append((processed, total)),
            )

        self.assertEqual(response["source"], "professional")
        self.assertEqual(response["total"], 2)
        self.assertEqual(response["imported"], 2)
        self.assertEqual(response["failed"], 0)
        self.assertGreater(response["openings_count"], 0)
        self.assertEqual(progress[0], (0, 2))
        self.assertEqual(progress[-1], (2, 2))
        self.assertEqual(len(self.api.list_games()["games"]), 0)

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
        self.assertIn(" b ", response["blunders"][0]["previous_sfen"])
        self.assertEqual(response["blunders"][0]["eval_before"], 80)
        self.assertEqual(response["blunders"][0]["eval_after"], -120)
        self.assertEqual(response["blunders"][0]["eval_delta"], -200)
        self.assertEqual(response["blunders"][0]["loss"], 200)
        self.assertEqual(response["blunders"][0]["occurrence_count"], 1)
        self.assertEqual(response["blunders"][0]["game_count"], 1)

    def test_get_blunder_explanation_prompt(self):
        game_id = self.api.import_game(KIF_WITH_BLUNDER)["game"]["id"]

        response = self.api.get_blunder_explanation_prompt(game_id, 3)

        self.assertEqual(response["game"]["id"], game_id)
        self.assertEqual(response["position"]["move_number"], 3)
        self.assertEqual(response["previous_position"]["move_number"], 2)
        self.assertEqual(response["materials"]["move"], "2g2f")
        self.assertEqual(response["materials"]["eval_before"], 80)
        self.assertEqual(response["materials"]["eval_after"], -120)
        self.assertEqual(response["materials"]["eval_delta"], -200)
        self.assertEqual(response["materials"]["loss"], 200)
        self.assertEqual(response["materials"]["severity"], "brief")
        self.assertIn("着手前SFEN:", response["prompt"])
        self.assertIn("着手後SFEN:", response["prompt"])
        self.assertIn("推測として考えられる悪手理由", response["prompt"])

    def test_get_blunder_explanation_prompt_requires_existing_move(self):
        game_id = self.api.import_game(KIF_WITH_BLUNDER)["game"]["id"]

        with self.assertRaises(ApiError) as context:
            self.api.get_blunder_explanation_prompt(game_id, 99)

        self.assertEqual(context.exception.status_code, 404)

    def test_explain_blunder(self):
        game_id = self.api.import_game(KIF_WITH_BLUNDER)["game"]["id"]

        with patch("src.api.generate_position_explanation") as generate:
            generate.return_value = "2六歩で評価値が下がりました。"

            response = self.api.explain_blunder(
                game_id,
                3,
                llm_command="fake-llm",
            )

        self.assertEqual(response["game"]["id"], game_id)
        self.assertEqual(response["materials"]["move"], "2g2f")
        self.assertIn("着手前SFEN:", response["prompt"])
        self.assertEqual(response["explanation"], "2六歩で評価値が下がりました。")
        generate.assert_called_once()

    def test_explain_blunder_skips_small_eval_change(self):
        game_id = self.api.import_game(KIF_WITH_BLUNDER)["game"]["id"]
        self.repository.connection.execute(
            "UPDATE positions SET eval = ? WHERE game_id = ? AND move_number = ?",
            (0, game_id, 3),
        )

        with patch("src.api.generate_position_explanation") as generate:
            with self.assertRaises(ApiError) as context:
                self.api.explain_blunder(
                    game_id,
                    3,
                    llm_command="fake-llm",
                )

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("too small", str(context.exception))
        generate.assert_not_called()

    @patch("src.api.load_settings")
    def test_explain_blunder_requires_llm_command(self, mock_load_settings):
        mock_load_settings.return_value = AppSettings()

        game_id = self.api.import_game(KIF_WITH_BLUNDER)["game"]["id"]

        with self.assertRaises(ApiError) as context:
            self.api.explain_blunder(game_id, 3)

        self.assertEqual(context.exception.status_code, 400)

    def test_get_position_frequency(self):
        first_game = self.api.import_game(KIF_WITH_ANALYSIS)
        self.api.import_game(f"{KIF_WITH_ANALYSIS}\n# duplicate variation")
        start_sfen = self.api.get_positions(first_game["game"]["id"])["positions"][0]["sfen"]

        response = self.api.get_position_frequency(start_sfen)

        self.assertEqual(response["sfen"], start_sfen)
        self.assertEqual(response["total"], 2)
        self.assertEqual(response["moves"][0]["move"], "7g7f")
        self.assertEqual(response["moves"][0]["count"], 2)
        self.assertEqual(response["moves"][0]["ratio"], 1.0)
        self.assertEqual(response["moves"][0]["avg_eval"], 64)

    def test_get_position_frequency_rejects_empty_sfen(self):
        with self.assertRaises(ApiError) as context:
            self.api.get_position_frequency("")

        self.assertEqual(context.exception.status_code, 400)

    def test_rebuild_openings(self):
        self.api.import_game(KIF_WITH_ANALYSIS)

        response = self.api.rebuild_openings()
        openings = self.repository.list_openings(source="self")
        openings_by_move = {opening.move: opening for opening in openings}

        self.assertEqual(response["source"], "self")
        self.assertEqual(response["count"], len(openings))
        self.assertEqual(openings_by_move["7g7f"].count, 1)
        self.assertEqual(openings_by_move["7g7f"].avg_eval, 64)
        self.assertIn(
            "7g7f",
            {opening["move"] for opening in response["openings"]},
        )

    def test_rebuild_openings_with_progress(self):
        progress = []
        self.api.import_game(KIF_WITH_ANALYSIS)

        response = self.api.rebuild_openings_with_progress(
            progress_callback=lambda processed, total: progress.append((processed, total)),
        )

        self.assertEqual(response["source"], "self")
        self.assertEqual(response["processed"], response["total"])
        self.assertGreater(response["total"], 0)
        self.assertFalse(response["canceled"])
        self.assertEqual(progress[0][0], 0)
        self.assertEqual(progress[-1], (response["total"], response["total"]))

    def test_rebuild_openings_with_progress_can_cancel_before_upsert(self):
        progress = []
        self.api.import_game(KIF_WITH_ANALYSIS)

        response = self.api.rebuild_openings_with_progress(
            progress_callback=lambda processed, total: progress.append((processed, total)),
            should_cancel=lambda: bool(progress),
        )

        self.assertTrue(response["canceled"])
        self.assertEqual(response["count"], 0)
        self.assertEqual(self.repository.list_openings(source="self"), [])

    def test_rebuild_openings_rejects_empty_source(self):
        with self.assertRaises(ApiError) as context:
            self.api.rebuild_openings("")

        self.assertEqual(context.exception.status_code, 400)

    def test_import_opening_game_saves_professional_openings(self):
        response = self.api.import_opening_game(KIF_WITH_ANALYSIS, source="professional")

        openings = self.repository.list_openings(source="professional")
        openings_by_move = {opening.move: opening for opening in openings}

        self.assertEqual(response["source"], "professional")
        self.assertEqual(response["count"], len(openings))
        self.assertEqual(openings_by_move["7g7f"].count, 1)
        self.assertEqual(self.repository.list_games(), [])

    def test_import_opening_game_adds_to_existing_openings(self):
        self.api.import_opening_game(KIF_WITH_ANALYSIS, source="professional")
        self.api.import_opening_game(KIF_WITH_ANALYSIS, source="professional")

        openings = self.repository.list_openings(source="professional")
        openings_by_move = {opening.move: opening for opening in openings}

        self.assertEqual(openings_by_move["7g7f"].count, 2)

    def test_get_openings(self):
        first_game = self.api.import_game(KIF_WITH_ANALYSIS)
        start_sfen = self.api.get_positions(first_game["game"]["id"])["positions"][0]["sfen"]
        self.api.import_opening_game(KIF_WITH_ANALYSIS, source="professional")

        response = self.api.get_openings(start_sfen, source="professional")

        self.assertEqual(response["source"], "professional")
        self.assertEqual(response["sfen"], start_sfen)
        self.assertEqual(response["total"], 1)
        self.assertEqual(response["moves"][0]["move"], "7g7f")
        self.assertEqual(response["moves"][0]["count"], 1)
        self.assertEqual(response["moves"][0]["ratio"], 1.0)
        self.assertEqual(response["moves"][0]["avg_eval"], 64)

    def test_get_openings_rejects_empty_sfen(self):
        with self.assertRaises(ApiError) as context:
            self.api.get_openings("")

        self.assertEqual(context.exception.status_code, 400)

    def test_get_opening_comparison_prompt(self):
        game_id = self.api.import_game(KIF_WITH_ANALYSIS)["game"]["id"]
        position = self.repository.list_positions(game_id)[0]
        self.api.rebuild_openings()
        self.repository.upsert_opening_aggregates([
            OpeningAggregate(
                source="professional",
                sfen=position.sfen,
                move="2g2f",
                count=3,
                avg_eval=42,
            )
        ])
        self.repository.update_position_analysis(
            position.id,
            eval_value=20,
            best_move="7g7f",
            pv="7g7f 3c3d",
            candidates=[{"move": "7g7f", "eval": 30}],
            engine_name="test-engine",
            engine_depth=1,
        )

        response = self.api.get_opening_comparison_prompt(
            position.id,
            sources=["self", "professional"],
        )

        self.assertEqual(response["position"]["id"], position.id)
        self.assertEqual(response["sources"], ["self", "professional"])
        self.assertEqual(response["materials"]["move_frequencies"][0]["move"], "7g7f")
        self.assertEqual(response["materials"]["openings_by_source"]["professional"][0]["move"], "2g2f")
        self.assertEqual(response["materials"]["engine_candidates"][0]["move"], "7g7f")
        self.assertIn("source別定跡候補:", response["prompt"])
        self.assertIn("エンジン候補手:", response["prompt"])

    def test_explain_opening_comparison(self):
        game_id = self.api.import_game(KIF_WITH_ANALYSIS)["game"]["id"]
        position = self.repository.list_positions(game_id)[0]
        self.api.rebuild_openings()

        with patch("src.api.generate_position_explanation") as generate:
            generate.return_value = "7六歩と定跡候補を比較しました。"

            response = self.api.explain_opening_comparison(
                position.id,
                sources=["self"],
                llm_command="fake-llm",
            )

        self.assertEqual(response["position"]["id"], position.id)
        self.assertEqual(response["sources"], ["self"])
        self.assertIn("source別定跡候補:", response["prompt"])
        self.assertEqual(response["explanation"], "7六歩と定跡候補を比較しました。")
        generate.assert_called_once()

    @patch("src.api.load_settings")
    def test_explain_opening_comparison_requires_llm_command(self, mock_load_settings):
        mock_load_settings.return_value = AppSettings()

        game_id = self.api.import_game(KIF_WITH_ANALYSIS)["game"]["id"]
        position = self.repository.list_positions(game_id)[0]

        with self.assertRaises(ApiError) as context:
            self.api.explain_opening_comparison(position.id)

        self.assertEqual(context.exception.status_code, 400)

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

    def test_analyze_position(self):
        game_id = self.api.import_game(KIF_WITH_ANALYSIS)["game"]["id"]
        position_id = self.repository.list_positions(game_id)[0].id

        with patch("src.api.UsiEngineAnalyzer") as analyzer_class:
            analyzer_class.return_value.analyze_sfen.return_value = EngineAnalysis(
                eval=103,
                best_move="2g2f",
                pv="2g2f 8c8d",
                candidates=[{"move": "2g2f", "eval": 103}],
                engine_name="Suisho5",
                engine_depth=10,
            )

            response = self.api.analyze_position(
                position_id,
                engine_path="/path/to/Suisho5",
                depth=10,
            )

        position = response["position"]
        self.assertEqual(position["id"], position_id)
        self.assertEqual(position["eval"], 103)
        self.assertEqual(position["best_move"], "2g2f")
        self.assertEqual(position["pv"], "2g2f 8c8d")
        self.assertEqual(position["candidates"], [{"move": "2g2f", "eval": 103}])
        self.assertEqual(position["engine_name"], "Suisho5")
        self.assertEqual(position["engine_depth"], 10)
        self.assertIsNotNone(position["analyzed_at"])

    @patch("src.api.load_settings")
    def test_analyze_position_requires_engine_path(self, mock_load_settings):
        mock_load_settings.return_value = AppSettings()

        game_id = self.api.import_game(KIF_WITH_ANALYSIS)["game"]["id"]
        position_id = self.repository.list_positions(game_id)[0].id

        with self.assertRaises(ApiError) as context:
            self.api.analyze_position(position_id, engine_path=None)

        self.assertEqual(context.exception.status_code, 400)

    def test_get_position_explanation_prompt(self):
        game_id = self.api.import_game(KIF_WITH_ANALYSIS)["game"]["id"]
        self.api.import_opening_game(KIF_WITH_ANALYSIS, source="professional")
        position_id = self.repository.list_positions(game_id)[1].id

        response = self.api.get_position_explanation_prompt(position_id)

        self.assertEqual(response["position"]["id"], position_id)
        self.assertEqual(response["previous_position"]["move_number"], 0)
        self.assertEqual(response["materials"]["previous_position"]["move_number"], 0)
        self.assertIsNone(response["materials"]["eval_before"])
        self.assertIsNone(response["materials"]["eval_delta"])
        self.assertIsNone(response["materials"]["loss"])
        self.assertEqual(response["materials"]["severity"], "unknown")
        self.assertEqual(response["materials"]["eval"], 64)
        self.assertEqual(response["materials"]["best_move"], "7g7f")
        self.assertEqual(response["materials"]["candidates"][0]["move"], "2g2f")
        self.assertEqual(response["materials"]["top_candidate_eval"], 55)
        self.assertEqual(response["materials"]["top_candidate_eval_gap"], -9)
        self.assertEqual(response["materials"]["openings"][0]["move"], "3c3d")
        self.assertNotIn("評価値", response["materials"]["missing"])
        self.assertIn("SFEN:", response["prompt"])
        self.assertIn("直前SFEN:", response["prompt"])
        self.assertIn("評価値変化: なし", response["prompt"])
        self.assertIn("実戦手: 7g7f", response["prompt"])
        self.assertIn("候補手: 2g2f(+55)", response["prompt"])
        self.assertIn("候補手上位との差: -9", response["prompt"])
        self.assertIn("確定情報と推測を混ぜない", response["prompt"])
        self.assertIn("根拠に使った入力項目を明示する", response["prompt"])
        self.assertIn("与えられていない読みや評価を創作しない", response["prompt"])

    def test_get_position_explanation_prompt_marks_missing_materials(self):
        game_id = self.api.import_game(SHIKENBISHA_KIF)["game"]["id"]
        position_id = self.repository.list_positions(game_id)[0].id

        response = self.api.get_position_explanation_prompt(position_id)

        self.assertIsNone(response["previous_position"])
        self.assertIn("直前局面", response["materials"]["missing"])
        self.assertIn("評価値", response["materials"]["missing"])
        self.assertIn("候補手", response["materials"]["missing"])
        self.assertIn("直前SFEN: なし", response["prompt"])
        self.assertIn("評価値: なし", response["prompt"])
        self.assertIn("候補手: なし", response["prompt"])

    def test_get_position_explanation_prompt_missing_position_raises_404(self):
        with self.assertRaises(ApiError) as context:
            self.api.get_position_explanation_prompt(999)

        self.assertEqual(context.exception.status_code, 404)

    def test_explain_position(self):
        game_id = self.api.import_game(KIF_WITH_ANALYSIS)["game"]["id"]
        position_id = self.repository.list_positions(game_id)[1].id

        with patch("src.api.generate_position_explanation") as generate:
            generate.return_value = "7六歩は自然な初手です。"

            response = self.api.explain_position(
                position_id,
                llm_command="fake-llm",
            )

        self.assertEqual(response["position"]["id"], position_id)
        self.assertIn("SFEN:", response["prompt"])
        self.assertEqual(response["explanation"], "7六歩は自然な初手です。")
        generate.assert_called_once()

    @patch("src.api.load_settings")
    def test_explain_position_requires_llm_command(self, mock_load_settings):
        mock_load_settings.return_value = AppSettings()

        game_id = self.api.import_game(KIF_WITH_ANALYSIS)["game"]["id"]
        position_id = self.repository.list_positions(game_id)[0].id

        with self.assertRaises(ApiError) as context:
            self.api.explain_position(position_id)

        self.assertEqual(context.exception.status_code, 400)

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
