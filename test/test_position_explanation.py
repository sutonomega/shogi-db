import unittest

from src.position_explanation import (
    PositionExplanationError,
    build_position_explanation_prompt,
    generate_position_explanation,
)


class TestPositionExplanation(unittest.TestCase):
    def test_build_prompt_separates_facts_and_inferences(self):
        prompt = build_position_explanation_prompt(
            {
                "sfen": "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1",
                "move_number": 1,
                "move": "7g7f",
                "eval": -120,
                "best_move": "2g2f",
                "pv": "2g2f 8c8d",
                "candidates": [{"move": "2g2f", "eval": 35}],
                "openings": [{"move": "7g7f", "count": 3, "avg_eval": -20}],
                "missing": [],
            }
        )

        self.assertIn("確定情報と推測を混ぜない", prompt)
        self.assertIn("根拠に使った入力項目を明示する", prompt)
        self.assertIn("与えられていない読みや評価を創作しない", prompt)
        self.assertIn("確定情報:", prompt)
        self.assertIn("3. 推測として考えられる悪化理由", prompt)
        self.assertIn("5. 不足情報と注意点", prompt)

    def test_generate_position_explanation_uses_command_stdout(self):
        explanation = generate_position_explanation(
            "局面データ",
            llm_command="python3 -c \"import sys; print('解説:' + sys.stdin.read())\"",
            timeout=5,
        )

        self.assertEqual(explanation, "解説:局面データ")

    def test_generate_position_explanation_rejects_empty_output(self):
        with self.assertRaisesRegex(PositionExplanationError, "empty output"):
            generate_position_explanation(
                "局面データ",
                llm_command="python3 -c \"print('')\"",
                timeout=5,
            )

    def test_generate_position_explanation_reports_command_failure(self):
        with self.assertRaisesRegex(PositionExplanationError, "失敗"):
            generate_position_explanation(
                "局面データ",
                llm_command="python3 -c \"import sys; sys.stderr.write('失敗'); sys.exit(2)\"",
                timeout=5,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
