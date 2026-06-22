import unittest

from src.japanese_move import usi_to_japanese_move


START_SFEN = (
    "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/"
    "PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"
)


class TestJapaneseMove(unittest.TestCase):
    def test_black_pawn_move(self):
        self.assertEqual(
            usi_to_japanese_move(START_SFEN, "7g7f"),
            "▲７六歩",
        )

    def test_white_pawn_move(self):
        sfen = (
            "lnsgkgsnl/1r5b1/ppppppppp/9/9/2P6/"
            "PP1PPPPPP/1B5R1/LNSGKGSNL w - 2"
        )
        self.assertEqual(
            usi_to_japanese_move(sfen, "3c3d"),
            "△３四歩",
        )

    def test_drop_move(self):
        sfen = (
            "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/"
            "PPPPPPPPP/1B5R1/LNSGKGSNL b P 1"
        )
        self.assertEqual(
            usi_to_japanese_move(sfen, "P*5e"),
            "▲５五歩打",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
