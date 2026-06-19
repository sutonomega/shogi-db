"""
Rule-based enclosure detection from generated SFEN positions.
"""

from .sfen_generator import PositionRecord


class EnclosureDetector:
    def detect(self, positions: list[PositionRecord]) -> str | None:
        boards = [_SfenBoard(position.sfen) for position in positions]

        if any(board.is_black_anaguma() for board in boards):
            return "居飛車穴熊"
        if any(board.is_black_ginkanmuri() for board in boards):
            return "銀冠"
        if any(board.is_black_mino() for board in boards):
            return "美濃囲い"
        if any(board.is_black_elmo() for board in boards):
            return "エルモ囲い"

        return None


class _SfenBoard:
    _RANKS = "abcdefghi"

    def __init__(self, sfen: str) -> None:
        self.board_part = sfen.split()[0]
        self.squares = self._parse_board(self.board_part)

    def is_black_anaguma(self) -> bool:
        return (
            self.piece_at("1i") == "K"
            and self.piece_at("1h") == "L"
            and self.any_piece_at({"G", "S"}, ("2h", "3h"))
        )

    def is_black_ginkanmuri(self) -> bool:
        return (
            self.piece_at("2h") == "K"
            and self.piece_at("2g") == "S"
            and self.any_piece_at({"G"}, ("3h", "4h"))
        )

    def is_black_mino(self) -> bool:
        return (
            self.piece_at("2h") == "K"
            and self.piece_at("3h") == "S"
            and self.any_piece_at({"G"}, ("4h", "5h"))
        )

    def is_black_elmo(self) -> bool:
        return (
            self.piece_at("7h") == "K"
            and self.piece_at("6h") == "S"
            and self.piece_at("7g") == "G"
        )

    def any_piece_at(self, pieces: set[str], squares: tuple[str, ...]) -> bool:
        return any(self.piece_at(square) in pieces for square in squares)

    def piece_at(self, square: str) -> str | None:
        file_number = int(square[0])
        rank = square[1]
        row = self._RANKS.index(rank)
        column = 9 - file_number
        return self.squares[row][column]

    def _parse_board(self, board_part: str) -> list[list[str | None]]:
        rows: list[list[str | None]] = []
        for row_text in board_part.split("/"):
            row: list[str | None] = []
            index = 0
            while index < len(row_text):
                char = row_text[index]
                if char.isdigit():
                    row.extend([None] * int(char))
                elif char == "+":
                    index += 1
                    row.append(f"+{row_text[index]}")
                else:
                    row.append(char)
                index += 1
            rows.append(row)
        return rows
