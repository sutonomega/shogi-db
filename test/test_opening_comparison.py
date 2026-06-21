import unittest

from src.opening_comparison import (
    build_opening_comparison_materials,
    build_opening_comparison_prompt,
)


class TestOpeningComparison(unittest.TestCase):
    def test_build_materials_marks_missing_sources(self):
        materials = build_opening_comparison_materials(
            {
                "id": 1,
                "move_number": 0,
                "sfen": "startpos",
                "best_move": "7g7f",
                "pv": "7g7f 3c3d",
                "candidates": [{"move": "7g7f", "eval": 30}],
            },
            [{"move": "2g2f", "count": 2, "ratio": 1.0, "avg_eval": 10}],
            {
                "self": [{"move": "2g2f", "count": 2, "avg_eval": 10}],
                "professional": [],
            },
        )

        self.assertEqual(materials["position_id"], 1)
        self.assertIn("定跡候補:professional", materials["missing"])

    def test_build_prompt_compares_sources_and_engine_candidates(self):
        materials = build_opening_comparison_materials(
            {
                "id": 1,
                "move_number": 0,
                "sfen": "startpos",
                "best_move": "7g7f",
                "pv": "7g7f 3c3d",
                "candidates": [{"move": "7g7f", "eval": 30}],
            },
            [{"move": "2g2f", "count": 2, "ratio": 1.0, "avg_eval": 10}],
            {"self": [{"move": "2g2f", "count": 2, "avg_eval": 10}]},
        )

        prompt = build_opening_comparison_prompt(materials)

        self.assertIn("source別の定跡候補", prompt)
        self.assertIn("自分の実戦頻度手: 2g2f", prompt)
        self.assertIn("self: 2g2f", prompt)
        self.assertIn("エンジン候補手: 7g7f", prompt)
        self.assertIn("source別定跡候補との違い", prompt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
