import unittest

from src.enclosure_detector import EnclosureDetector
from src.sfen_generator import PositionRecord


def position_from_pieces(pieces: dict[str, str]) -> PositionRecord:
    ranks = "abcdefghi"
    rows = []
    for rank in ranks:
        row = ""
        empty_count = 0
        for file_number in range(9, 0, -1):
            piece = pieces.get(f"{file_number}{rank}")
            if piece is None:
                empty_count += 1
                continue
            if empty_count:
                row += str(empty_count)
                empty_count = 0
            row += piece
        if empty_count:
            row += str(empty_count)
        rows.append(row)

    return PositionRecord(
        move_number=1,
        sfen=f"{'/'.join(rows)} b - 1",
        move_usi=None,
        eval=None,
        best_move=None,
        pv=None,
        candidates=[],
    )


class TestEnclosureDetector(unittest.TestCase):
    def setUp(self):
        self.detector = EnclosureDetector()

    def test_detects_elmo(self):
        positions = [
            position_from_pieces({
                "7h": "K",
                "6h": "S",
                "7g": "G",
            })
        ]

        self.assertEqual(self.detector.detect(positions), "エルモ囲い")

    def test_detects_anaguma(self):
        positions = [
            position_from_pieces({
                "1i": "K",
                "1h": "L",
                "2h": "G",
            })
        ]

        self.assertEqual(self.detector.detect(positions), "居飛車穴熊")

    def test_detects_mino(self):
        positions = [
            position_from_pieces({
                "2h": "K",
                "3h": "S",
                "5h": "G",
            })
        ]

        self.assertEqual(self.detector.detect(positions), "美濃囲い")

    def test_detects_ginkanmuri(self):
        positions = [
            position_from_pieces({
                "2h": "K",
                "2g": "S",
                "3h": "G",
            })
        ]

        self.assertEqual(self.detector.detect(positions), "銀冠")

    def test_returns_none_when_no_rule_matches(self):
        positions = [
            position_from_pieces({
                "5i": "K",
                "4i": "G",
                "6i": "G",
            })
        ]

        self.assertIsNone(self.detector.detect(positions))


if __name__ == "__main__":
    unittest.main(verbosity=2)
