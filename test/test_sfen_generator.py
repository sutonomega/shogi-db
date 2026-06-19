import unittest

from src.kif_parser import KifParser
from src.sfen_generator import SfenGenerationError, SfenGenerator


KIF_OPENING = """\
開始日時：2024/01/15 20:00:00
手合割：平手
先手：テストA
後手：テストB
手数----指手---------消費時間--
   1 ７六歩(77)
   2 ３四歩(33)
   3 ２二角成(88)
   4 ８四歩(83)
   5 ５五角打
   6 投了
"""


KIF_SAME_CAPTURE = """\
手合割：平手
先手：テストA
後手：テストB
手数----指手---------消費時間--
   1 ７六歩(77)
   2 ３四歩(33)
   3 ２二角成(88)
   4 同　銀(31)
   5 投了
"""


class TestSfenGenerator(unittest.TestCase):
    def test_initial_position_is_included(self):
        record = KifParser().parse(KIF_OPENING)
        positions = SfenGenerator().generate(record)

        self.assertEqual(
            positions[0].sfen,
            "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1",
        )

    def test_kif_moves_are_converted_to_usi(self):
        record = KifParser().parse(KIF_OPENING)
        positions = SfenGenerator().generate(record)

        self.assertEqual(
            [move.move_usi for move in record.moves],
            ["7g7f", "3c3d", "8h2b+", "8c8d", "B*5e"],
        )
        self.assertEqual(
            [position.move_usi for position in positions[1:]],
            ["7g7f", "3c3d", "8h2b+", "8c8d", "B*5e"],
        )

    def test_sfen_is_generated_for_each_move(self):
        record = KifParser().parse(KIF_OPENING)
        positions = SfenGenerator().generate(record)

        self.assertEqual(len(positions), 6)
        self.assertEqual(
            positions[1].sfen,
            "lnsgkgsnl/1r5b1/ppppppppp/9/9/2P6/PP1PPPPPP/1B5R1/LNSGKGSNL w - 2",
        )
        self.assertEqual(positions[3].sfen.split()[2], "B")
        self.assertEqual(positions[5].sfen.split()[2], "-")

    def test_same_square_move_uses_previous_destination(self):
        record = KifParser().parse(KIF_SAME_CAPTURE)
        positions = SfenGenerator().generate(record)

        self.assertEqual(record.moves[3].move_usi, "3a2b")
        self.assertEqual(positions[4].sfen.split()[2], "Bb")

    def test_missing_source_raises_useful_error(self):
        record = KifParser().parse("""\
手合割：平手
先手：A
後手：B
手数----指手---------消費時間--
   1 ７六歩
""")

        with self.assertRaisesRegex(SfenGenerationError, "Move source is missing"):
            SfenGenerator().generate(record)


if __name__ == "__main__":
    unittest.main(verbosity=2)
