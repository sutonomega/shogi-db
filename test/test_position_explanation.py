import unittest

from src.position_explanation import (
    PositionExplanationError,
    build_position_explanation_materials,
    build_position_explanation_prompt,
    generate_position_explanation,
)


class TestPositionExplanation(unittest.TestCase):
    def test_build_prompt_separates_facts_and_inferences(self):
        prompt = build_position_explanation_prompt(
            {
                "sfen": "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1",
                "previous_position": {
                    "sfen": "before",
                    "eval": 80,
                },
                "move_number": 1,
                "move": "7g7f",
                "eval_before": 80,
                "eval": -120,
                "eval_delta": -200,
                "loss": 200,
                "severity": "brief",
                "explanation_policy": "200点以上500点未満の低下として、根拠に限定した簡易解説にする",
                "best_move": "2g2f",
                "top_candidate_eval": 35,
                "top_candidate_eval_gap": 155,
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
        self.assertIn("直前SFEN: before", prompt)
        self.assertIn("評価値変化: -200", prompt)
        self.assertIn("損失: 200", prompt)
        self.assertIn("候補手上位との差: +155", prompt)
        self.assertIn("3. 推測として考えられる悪化理由", prompt)
        self.assertIn("5. 不足情報と注意点", prompt)

    def test_build_materials_adds_eval_delta_and_candidate_gap(self):
        materials = build_position_explanation_materials(
            {
                "id": 2,
                "move_number": 3,
                "sfen": "after",
                "move": "2g2f",
                "eval": -120,
                "best_move": "7g7f",
                "pv": "7g7f 3c3d",
                "candidates": [{"move": "7g7f", "eval": 70}],
                "analyzed_at": None,
                "engine_name": None,
                "engine_depth": None,
            },
            [],
            {
                "id": 1,
                "move_number": 2,
                "sfen": "before",
                "move": "3c3d",
                "eval": 80,
                "best_move": None,
                "pv": None,
                "candidates": [],
                "analyzed_at": None,
                "engine_name": None,
                "engine_depth": None,
            },
        )

        self.assertEqual(materials["eval_before"], 80)
        self.assertEqual(materials["eval_delta"], -200)
        self.assertEqual(materials["loss"], 200)
        self.assertEqual(materials["severity"], "brief")
        self.assertEqual(materials["top_candidate_eval"], 70)
        self.assertEqual(materials["top_candidate_eval_gap"], 190)
        self.assertNotIn("直前局面", materials["missing"])

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
