import unittest

from src.sfen_generator import PositionRecord
from src.strategy_detector import StrategyDetector


def position(sfen: str) -> PositionRecord:
    return PositionRecord(
        move_number=1,
        sfen=sfen,
        move_usi=None,
        eval=None,
        best_move=None,
        pv=None,
        candidates=[],
    )


class TestStrategyDetector(unittest.TestCase):
    def setUp(self):
        self.detector = StrategyDetector()

    def test_detects_bishop_exchange(self):
        positions = [
            position(
                "lnsgkgsnl/1r7/ppppppppp/9/9/9/PPPPPPPPP/7R1/LNSGKGSNL b Bb 1"
            )
        ]

        self.assertEqual(self.detector.detect(positions), "角換わり")

    def test_detects_yokofudori(self):
        positions = [
            position(
                "lnsgkgsnl/1r5b1/ppppppppp/6R2/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"
            )
        ]

        self.assertEqual(self.detector.detect(positions), "横歩取り")

    def test_detects_shikenbisha(self):
        positions = [
            position(
                "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B1R5/LNSGKGSNL b - 1"
            )
        ]

        self.assertEqual(self.detector.detect(positions), "四間飛車")

    def test_detects_aigakari(self):
        positions = [
            position(
                "lnsgkgsnl/1r5b1/ppppppppp/9/1p5P1/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"
            )
        ]

        self.assertEqual(self.detector.detect(positions), "相掛かり")

    def test_returns_none_when_no_rule_matches(self):
        positions = [
            position(
                "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"
            )
        ]

        self.assertIsNone(self.detector.detect(positions))


if __name__ == "__main__":
    unittest.main(verbosity=2)
