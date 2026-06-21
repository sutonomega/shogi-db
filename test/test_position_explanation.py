import unittest

from src.position_explanation import (
    PositionExplanationError,
    generate_position_explanation,
)


class TestPositionExplanation(unittest.TestCase):
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
