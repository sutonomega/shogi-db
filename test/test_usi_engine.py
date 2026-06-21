import unittest

from src.usi_engine import MATE_EVAL, MAX_CANDIDATES, parse_usi_analysis


class TestUsiEngineAnalysis(unittest.TestCase):
    def test_parse_cp_score_pv_and_bestmove(self):
        analysis = parse_usi_analysis(
            [
                "id name Suisho5",
                "usiok",
                "readyok",
                "info depth 10 score cp 103 pv 2g2f 8c8d 2f2e",
                "bestmove 2g2f",
            ],
            requested_depth=10,
        )

        self.assertEqual(analysis.engine_name, "Suisho5")
        self.assertEqual(analysis.engine_depth, 10)
        self.assertEqual(analysis.eval, 103)
        self.assertEqual(analysis.best_move, "2g2f")
        self.assertEqual(analysis.pv, "2g2f 8c8d 2f2e")
        self.assertEqual(analysis.candidates, [{"move": "2g2f", "eval": 103}])

    def test_parse_multipv_candidates_keeps_top_five_latest_lines(self):
        analysis = parse_usi_analysis(
            [
                "id name Suisho5",
                "info depth 8 multipv 1 score cp 90 pv 7g7f 3c3d",
                "info depth 8 multipv 2 score cp 80 pv 2g2f 8c8d",
                "info depth 10 multipv 1 score cp 110 pv 7g7f 3c3d 2g2f",
                "info depth 10 multipv 2 score cp 95 pv 2g2f 8c8d 2f2e",
                "info depth 10 multipv 3 score cp 60 pv 6i7h",
                "info depth 10 multipv 4 score cp 40 pv 5i6h",
                "info depth 10 multipv 5 score cp 20 pv 3i4h",
                "info depth 10 multipv 6 score cp 10 pv 9g9f",
                "bestmove 7g7f",
            ],
            requested_depth=10,
        )

        self.assertEqual(analysis.eval, 110)
        self.assertEqual(analysis.best_move, "7g7f")
        self.assertEqual(analysis.pv, "7g7f 3c3d 2g2f")
        self.assertEqual(len(analysis.candidates), MAX_CANDIDATES)
        self.assertEqual(
            analysis.candidates,
            [
                {"move": "7g7f", "eval": 110},
                {"move": "2g2f", "eval": 95},
                {"move": "6i7h", "eval": 60},
                {"move": "5i6h", "eval": 40},
                {"move": "3i4h", "eval": 20},
            ],
        )

    def test_parse_mate_score(self):
        positive = parse_usi_analysis(
            ["info depth 10 score mate 3 pv 2g2f", "bestmove 2g2f"],
            engine_name="Suisho5",
            requested_depth=10,
        )
        negative = parse_usi_analysis(
            ["info depth 10 score mate -2 pv 8c8d", "bestmove 8c8d"],
            engine_name="Suisho5",
            requested_depth=10,
        )

        self.assertEqual(positive.eval, MATE_EVAL)
        self.assertEqual(negative.eval, -MATE_EVAL)


if __name__ == "__main__":
    unittest.main(verbosity=2)
