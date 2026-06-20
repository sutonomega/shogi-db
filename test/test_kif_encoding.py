import unittest

from src.kif_encoding import KifEncodingError, decode_kif_bytes


KIF_TEXT = """\
開始日時：2024/02/10 19:00:00
手合割：平手
先手：解析太郎
後手：棋譜花子
手数----指手---------消費時間--
   1 ７六歩(77)
   2 投了
"""


class TestKifEncoding(unittest.TestCase):
    def test_decodes_utf8_kif(self):
        decoded = decode_kif_bytes(KIF_TEXT.encode("utf-8"))

        self.assertEqual(decoded, KIF_TEXT)

    def test_decodes_utf8_sig_kif(self):
        decoded = decode_kif_bytes(KIF_TEXT.encode("utf-8-sig"))

        self.assertEqual(decoded, KIF_TEXT)

    def test_decodes_cp932_kif(self):
        decoded = decode_kif_bytes(KIF_TEXT.encode("cp932"))

        self.assertEqual(decoded, KIF_TEXT)

    def test_rejects_unsupported_bytes(self):
        with self.assertRaises(KifEncodingError):
            decode_kif_bytes(b"\x81")


if __name__ == "__main__":
    unittest.main(verbosity=2)
