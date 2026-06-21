import unittest

from src.blunder_explanation import (
    build_blunder_explanation_materials,
    build_blunder_explanation_prompt,
)


class TestBlunderExplanation(unittest.TestCase):
    def test_build_materials_calculates_black_loss(self):
        materials = build_blunder_explanation_materials(
            {"black": "先手", "white": "後手"},
            {
                "move_number": 2,
                "sfen": "before",
                "eval": 80,
            },
            {
                "move_number": 3,
                "move": "2g2f",
                "sfen": "after",
                "eval": -120,
                "best_move": "7g7f",
                "pv": "7g7f 3c3d",
                "candidates": [{"move": "7g7f", "eval": 70}],
            },
        )

        self.assertEqual(materials["eval_delta"], -200)
        self.assertEqual(materials["loss"], 200)
        self.assertEqual(materials["sfen_before"], "before")
        self.assertEqual(materials["sfen_after"], "after")
        self.assertEqual(materials["missing"], [])

    def test_build_prompt_requires_grounded_blunder_reasoning(self):
        materials = build_blunder_explanation_materials(
            {"black": "先手", "white": "後手"},
            {
                "move_number": 2,
                "sfen": "before",
                "eval": 80,
            },
            {
                "move_number": 3,
                "move": "2g2f",
                "sfen": "after",
                "eval": -120,
                "best_move": None,
                "pv": None,
                "candidates": [],
            },
        )

        prompt = build_blunder_explanation_prompt(materials)

        self.assertIn("確定情報と推測を混ぜない", prompt)
        self.assertIn("根拠に使った入力項目を明示する", prompt)
        self.assertIn("与えられていない読みや評価を創作しない", prompt)
        self.assertIn("着手前SFEN: before", prompt)
        self.assertIn("着手後SFEN: after", prompt)
        self.assertIn("評価値変化: -200", prompt)
        self.assertIn("不足項目: 最善手、読み筋、候補手", prompt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
