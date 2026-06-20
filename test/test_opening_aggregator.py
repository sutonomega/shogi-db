import unittest

from src.game_repository import GameRepository
from src.opening_aggregator import OpeningAggregator
from src.sfen_generator import PositionRecord
from src.kif_parser import GameRecord


def position(
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


class TestOpeningAggregator(unittest.TestCase):
    def setUp(self):
        self.repository = GameRepository()
        self.repository.init_schema()
        self.aggregator = OpeningAggregator(self.repository)

    def tearDown(self):
        self.repository.close()

    def test_aggregate_returns_self_opening_moves(self):
        game = GameRecord(
            played_at=None,
            black="A",
            white="B",
            winner=None,
            move_count=1,
            moves=[],
            raw_kif="raw",
        )
        self.repository.save_game(
            game,
            [
                position(0, "start", None, None),
                position(1, "after", "7g7f", 100),
            ],
        )

        aggregates = self.aggregator.aggregate()

        self.assertEqual(len(aggregates), 1)
        self.assertEqual(aggregates[0].source, "self")
        self.assertEqual(aggregates[0].sfen, "start")
        self.assertEqual(aggregates[0].move, "7g7f")
        self.assertEqual(aggregates[0].count, 1)
        self.assertEqual(aggregates[0].avg_eval, 100)

    def test_rebuild_saves_opening_moves(self):
        game = GameRecord(
            played_at=None,
            black="A",
            white="B",
            winner=None,
            move_count=1,
            moves=[],
            raw_kif="raw",
        )
        self.repository.save_game(
            game,
            [
                position(0, "start", None, None),
                position(1, "after", "7g7f", 100),
            ],
        )

        aggregates = self.aggregator.rebuild()
        openings = self.repository.list_openings(source="self", sfen="start")

        self.assertEqual(len(aggregates), 1)
        self.assertEqual(len(openings), 1)
        self.assertEqual(openings[0].move, "7g7f")
        self.assertEqual(openings[0].count, 1)
        self.assertEqual(openings[0].avg_eval, 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
