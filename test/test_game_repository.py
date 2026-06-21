import json
import unittest
from dataclasses import replace

from src.game_repository import GameRepository, OpeningAggregate
from src.kif_parser import KifParser
from src.sfen_generator import PositionRecord, SfenGenerator


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


def position(move_number: int, move: str | None, eval_value: int | None) -> PositionRecord:
    return PositionRecord(
        move_number=move_number,
        sfen="lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1",
        move_usi=move,
        eval=eval_value,
        best_move=None,
        pv=None,
        candidates=[],
    )


def opening_position(
    move_number: int,
    sfen: str,
    move: str | None,
    eval_value: int | None,
) -> PositionRecord:
    return PositionRecord(
        move_number=move_number,
        sfen=sfen,
        move_usi=move,
        eval=eval_value,
        best_move=None,
        pv=None,
        candidates=[],
    )


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

    def test_schema_has_position_move_number_index(self):
        rows = self.repository.connection.execute(
            "PRAGMA index_list(positions)"
        ).fetchall()

        self.assertIn(
            "idx_positions_game_move_number",
            {row["name"] for row in rows},
        )

    def test_schema_has_engine_analysis_columns(self):
        rows = self.repository.connection.execute(
            "PRAGMA table_info(positions)"
        ).fetchall()

        self.assertIn("analyzed_at", {row["name"] for row in rows})
        self.assertIn("engine_name", {row["name"] for row in rows})
        self.assertIn("engine_depth", {row["name"] for row in rows})

    def test_schema_has_move_occurrences_cache(self):
        rows = self.repository.connection.execute(
            "PRAGMA table_info(move_occurrences)"
        ).fetchall()

        self.assertEqual(
            {"sfen", "move", "count", "game_count", "updated_at"},
            {row["name"] for row in rows},
        )

    def test_save_strategy(self):
        game_id = self.repository.save_game(
            self.game,
            self.positions,
            strategy="四間飛車",
        )
        stored = self.repository.get_game(game_id)

        self.assertEqual(stored.strategy, "四間飛車")

    def test_save_enclosure(self):
        game_id = self.repository.save_game(
            self.game,
            self.positions,
            enclosure="美濃囲い",
        )
        stored = self.repository.get_game(game_id)

        self.assertEqual(stored.enclosure, "美濃囲い")

    def test_list_strategy_stats(self):
        white_win_game = replace(self.game, raw_kif=f"{self.game.raw_kif}\n#2", winner="white")
        draw_game = replace(self.game, raw_kif=f"{self.game.raw_kif}\n#3", winner="draw")
        other_game = replace(self.game, raw_kif=f"{self.game.raw_kif}\n#4", winner="black")
        self.repository.save_game(self.game, self.positions, strategy="四間飛車")
        self.repository.save_game(white_win_game, self.positions, strategy="四間飛車")
        self.repository.save_game(draw_game, self.positions, strategy="四間飛車")
        self.repository.save_game(other_game, self.positions, strategy="角換わり")

        stats = self.repository.list_strategy_stats()

        self.assertEqual(stats[0].strategy, "四間飛車")
        self.assertEqual(stats[0].games, 3)
        self.assertEqual(stats[0].wins, 1)
        self.assertEqual(stats[0].losses, 1)
        self.assertEqual(stats[0].draws, 1)
        self.assertEqual(stats[0].win_rate, 0.5)
        self.assertEqual(stats[1].strategy, "角換わり")

    def test_list_enclosure_stats(self):
        white_win_game = replace(self.game, raw_kif=f"{self.game.raw_kif}\n#2", winner="white")
        draw_game = replace(self.game, raw_kif=f"{self.game.raw_kif}\n#3", winner="draw")
        other_game = replace(self.game, raw_kif=f"{self.game.raw_kif}\n#4", winner="black")
        self.repository.save_game(self.game, self.positions, enclosure="美濃囲い")
        self.repository.save_game(white_win_game, self.positions, enclosure="美濃囲い")
        self.repository.save_game(draw_game, self.positions, enclosure="美濃囲い")
        self.repository.save_game(other_game, self.positions, enclosure="エルモ囲い")

        stats = self.repository.list_enclosure_stats()

        self.assertEqual(stats[0].enclosure, "美濃囲い")
        self.assertEqual(stats[0].games, 3)
        self.assertEqual(stats[0].wins, 1)
        self.assertEqual(stats[0].losses, 1)
        self.assertEqual(stats[0].draws, 1)
        self.assertEqual(stats[0].win_rate, 0.5)
        self.assertEqual(stats[1].enclosure, "エルモ囲い")

    def test_list_blunders(self):
        positions = [
            position(0, None, 0),
            position(1, "7g7f", 100),
            position(2, "3c3d", 300),
            position(3, "2g2f", 50),
        ]
        self.repository.save_game(self.game, positions)

        blunders = self.repository.list_blunders()

        self.assertEqual(len(blunders), 2)
        self.assertEqual(blunders[0].move_number, 3)
        self.assertEqual(blunders[0].move, "2g2f")
        self.assertIn(" b ", blunders[0].previous_sfen)
        self.assertEqual(blunders[0].eval_before, 300)
        self.assertEqual(blunders[0].eval_after, 50)
        self.assertEqual(blunders[0].eval_delta, -250)
        self.assertEqual(blunders[0].loss, 250)
        self.assertEqual(blunders[0].occurrence_count, 1)
        self.assertEqual(blunders[0].game_count, 1)
        self.assertEqual(blunders[1].move_number, 2)
        self.assertEqual(blunders[1].eval_delta, -200)

    def test_list_blunders_counts_same_position_move_occurrences(self):
        first_positions = [
            position(0, None, 0),
            position(1, "7g7f", 100),
            position(2, "3c3d", 300),
            position(3, "2g2f", 50),
        ]
        second_positions = [
            position(0, None, 0),
            position(1, "7g7f", 50),
            position(2, "8c8d", 160),
            position(3, "2g2f", -40),
        ]
        third_positions = [
            position(0, None, 0),
            position(1, "5i6h", 10),
            position(2, "3c3d", 90),
        ]
        self.repository.save_game(self.game, first_positions)
        self.repository.save_game(
            replace(self.game, raw_kif=f"{self.game.raw_kif}\n#2"),
            second_positions,
        )
        self.repository.save_game(
            replace(self.game, raw_kif=f"{self.game.raw_kif}\n#3"),
            third_positions,
        )

        blunders = self.repository.list_blunders()

        self.assertEqual(blunders[0].move, "2g2f")
        self.assertEqual(blunders[0].occurrence_count, 2)
        self.assertEqual(blunders[0].game_count, 2)
        self.assertEqual(blunders[1].move, "3c3d")
        self.assertEqual(blunders[1].occurrence_count, 2)
        self.assertEqual(blunders[1].game_count, 2)
        self.assertEqual(blunders[2].move, "2g2f")
        self.assertEqual(blunders[2].occurrence_count, 2)
        self.assertEqual(blunders[2].game_count, 2)

    def test_list_blunders_ignores_sfen_move_count_for_occurrences(self):
        first_positions = [
            opening_position(0, "same-board b - 1", None, 100),
            opening_position(1, "after 2g2f w - 2", "2g2f", -100),
        ]
        second_positions = [
            opening_position(0, "same-board b - 9", None, 80),
            opening_position(1, "after 2g2f w - 10", "2g2f", -120),
        ]
        self.repository.save_game(self.game, first_positions)
        self.repository.save_game(
            replace(self.game, raw_kif=f"{self.game.raw_kif}\n#2"),
            second_positions,
        )

        blunders = self.repository.list_blunders()
        cached = self.repository.connection.execute(
            """
            SELECT sfen, move, count, game_count
            FROM move_occurrences
            WHERE move = '2g2f'
            """
        ).fetchone()

        self.assertEqual(blunders[0].occurrence_count, 2)
        self.assertEqual(blunders[0].game_count, 2)
        self.assertEqual(cached["sfen"], "same-board b -")
        self.assertEqual(cached["count"], 2)
        self.assertEqual(cached["game_count"], 2)

    def test_save_positions_with_sfen_and_analysis(self):
        game_id = self.repository.save_game(self.game, self.positions)
        stored_positions = self.repository.list_positions(game_id)

        self.assertEqual(len(stored_positions), 4)
        self.assertIsInstance(stored_positions[0].id, int)
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

    def test_update_position_analysis(self):
        game_id = self.repository.save_game(self.game, self.positions)
        position_id = self.repository.list_positions(game_id)[0].id

        stored = self.repository.update_position_analysis(
            position_id,
            eval_value=103,
            best_move="2g2f",
            pv="2g2f 8c8d",
            candidates=[{"move": "2g2f", "eval": 103}],
            engine_name="Suisho5",
            engine_depth=10,
        )

        self.assertEqual(stored.eval, 103)
        self.assertEqual(stored.best_move, "2g2f")
        self.assertEqual(stored.pv, "2g2f 8c8d")
        self.assertEqual(json.loads(stored.candidates), [{"move": "2g2f", "eval": 103}])
        self.assertEqual(stored.engine_name, "Suisho5")
        self.assertEqual(stored.engine_depth, 10)
        self.assertIsNotNone(stored.analyzed_at)

    def test_duplicate_raw_kif_returns_existing_game_id(self):
        first_id = self.repository.save_game(self.game, self.positions)
        second_id = self.repository.save_game(
            self.game,
            self.positions,
            strategy="四間飛車",
        )

        self.assertEqual(second_id, first_id)
        self.assertEqual(self.repository.get_game(first_id).strategy, "四間飛車")
        count = self.repository.connection.execute(
            "SELECT COUNT(*) AS count FROM games"
        ).fetchone()["count"]
        self.assertEqual(count, 1)

    def test_duplicate_raw_kif_replaces_existing_positions(self):
        positions_without_eval = [
            replace(position_record, eval=None, best_move=None, pv=None, candidates=[])
            for position_record in self.positions
        ]
        game_id = self.repository.save_game(self.game, positions_without_eval)

        same_id = self.repository.save_game(self.game, self.positions)
        stored_positions = self.repository.list_positions(game_id)

        self.assertEqual(same_id, game_id)
        self.assertEqual(len(stored_positions), len(self.positions))
        self.assertEqual(stored_positions[1].eval, 64)
        self.assertEqual(stored_positions[1].best_move, "7g7f")
        count = self.repository.connection.execute(
            "SELECT COUNT(*) AS count FROM positions WHERE game_id = ?",
            (game_id,),
        ).fetchone()["count"]
        self.assertEqual(count, len(self.positions))

    def test_duplicate_raw_kif_refreshes_move_occurrences_cache(self):
        start_sfen = "startpos b - 1"
        first_positions = [
            opening_position(0, start_sfen, None, None),
            opening_position(1, "after 7g7f w - 2", "7g7f", 100),
        ]
        replacement_positions = [
            opening_position(0, start_sfen, None, None),
            opening_position(1, "after 2g2f w - 2", "2g2f", 100),
        ]
        self.repository.save_game(self.game, first_positions)

        self.repository.save_game(self.game, replacement_positions)

        rows = self.repository.connection.execute(
            """
            SELECT move, count, game_count
            FROM move_occurrences
            WHERE sfen = ?
            ORDER BY move
            """,
            ("startpos b -",),
        ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["move"], "2g2f")
        self.assertEqual(rows[0]["count"], 1)
        self.assertEqual(rows[0]["game_count"], 1)

    def test_list_games_does_not_load_raw_kif_body(self):
        game_id = self.repository.save_game(self.game, self.positions)

        listed_game = self.repository.list_games()[0]
        stored_game = self.repository.get_game(game_id)

        self.assertEqual(listed_game.id, game_id)
        self.assertEqual(listed_game.raw_kif, "")
        self.assertEqual(stored_game.raw_kif, KIF_WITH_ANALYSIS)

    def test_list_opening_aggregates_counts_moves_by_previous_sfen(self):
        start_sfen = "startpos b - 1"
        after_76 = "after 7g7f w - 2"
        after_34 = "after 3c3d b - 3"
        first_positions = [
            opening_position(0, start_sfen, None, None),
            opening_position(1, after_76, "7g7f", 100),
            opening_position(2, after_34, "3c3d", None),
        ]
        second_positions = [
            opening_position(0, start_sfen, None, None),
            opening_position(1, after_76, "7g7f", 200),
        ]
        other_positions = [
            opening_position(0, start_sfen, None, None),
            opening_position(1, "after 2g2f w - 2", "2g2f", 50),
        ]

        self.repository.save_game(self.game, first_positions)
        self.repository.save_game(
            replace(self.game, raw_kif=f"{self.game.raw_kif}\n#2"),
            second_positions,
        )
        self.repository.save_game(
            replace(self.game, raw_kif=f"{self.game.raw_kif}\n#3"),
            other_positions,
        )

        aggregates = self.repository.list_opening_aggregates()

        self.assertEqual(aggregates[0].source, "self")
        self.assertEqual(aggregates[0].sfen, start_sfen)
        self.assertEqual(aggregates[0].move, "7g7f")
        self.assertEqual(aggregates[0].count, 2)
        self.assertEqual(aggregates[0].avg_eval, 150)
        by_move = {aggregate.move: aggregate for aggregate in aggregates}
        self.assertEqual(by_move["2g2f"].count, 1)
        self.assertEqual(by_move["2g2f"].avg_eval, 50)
        self.assertEqual(by_move["3c3d"].sfen, after_76)
        self.assertEqual(by_move["3c3d"].avg_eval, None)

    def test_list_opening_aggregates_uses_requested_source(self):
        self.repository.save_game(self.game, self.positions)

        aggregates = self.repository.list_opening_aggregates(source="professional")

        self.assertEqual(aggregates[0].source, "professional")

    def test_list_move_frequencies_returns_moves_for_position(self):
        start_sfen = "startpos b - 1"
        first_positions = [
            opening_position(0, start_sfen, None, None),
            opening_position(1, "after 7g7f w - 2", "7g7f", 100),
        ]
        second_positions = [
            opening_position(0, start_sfen, None, None),
            opening_position(1, "after 7g7f w - 2", "7g7f", 200),
        ]
        third_positions = [
            opening_position(0, start_sfen, None, None),
            opening_position(1, "after 2g2f w - 2", "2g2f", None),
        ]

        self.repository.save_game(self.game, first_positions)
        self.repository.save_game(
            replace(self.game, raw_kif=f"{self.game.raw_kif}\n#2"),
            second_positions,
        )
        self.repository.save_game(
            replace(self.game, raw_kif=f"{self.game.raw_kif}\n#3"),
            third_positions,
        )

        frequencies = self.repository.list_move_frequencies(start_sfen)

        self.assertEqual(frequencies[0].move, "7g7f")
        self.assertEqual(frequencies[0].count, 2)
        self.assertEqual(frequencies[0].avg_eval, 150)
        self.assertEqual(frequencies[1].move, "2g2f")
        self.assertEqual(frequencies[1].count, 1)
        self.assertIsNone(frequencies[1].avg_eval)

    def test_upsert_opening_aggregates_saves_and_updates_openings(self):
        self.repository.upsert_opening_aggregates([
            OpeningAggregate(
                source="self",
                sfen="startpos b - 1",
                move="7g7f",
                count=1,
                avg_eval=100,
            )
        ])
        self.repository.upsert_opening_aggregates([
            OpeningAggregate(
                source="self",
                sfen="startpos b - 1",
                move="7g7f",
                count=3,
                avg_eval=150,
            )
        ])

        openings = self.repository.list_openings(
            source="self",
            sfen="startpos b - 1",
        )

        self.assertEqual(len(openings), 1)
        self.assertEqual(openings[0].move, "7g7f")
        self.assertEqual(openings[0].count, 3)
        self.assertEqual(openings[0].avg_eval, 150)


if __name__ == "__main__":
    unittest.main(verbosity=2)
