import unittest

from src.usi_engine import MATE_EVAL, parse_usi_analysis


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
