"""
Rule-based strategy detection from generated SFEN positions.
"""

from .sfen_generator import PositionRecord


class StrategyDetector:
    def detect(self, positions: list[PositionRecord]) -> str | None:
        boards = [_SfenBoard(position.sfen) for position in positions]

        if any(board.has_bishop_exchange() for board in boards):
            return "角換わり"
        if any(board.black_rook_on("3d") for board in boards):
            return "横歩取り"
        if any(board.black_rook_on("6h") for board in boards):
            return "四間飛車"
        if any(board.is_aigakari_shape() for board in boards):
            return "相掛かり"

        return None


class _SfenBoard:
    _RANKS = "abcdefghi"

    def __init__(self, sfen: str) -> None:
        parts = sfen.split()
        self.board_part = parts[0]
        self.hands_part = parts[2] if len(parts) > 2 else "-"
        self.squares = self._parse_board(self.board_part)

    def has_bishop_exchange(self) -> bool:
        board_text = self.board_part.replace("+", "")
        return "B" not in board_text and "b" not in board_text and self._has_hand("B") and self._has_hand("b")

    def black_rook_on(self, square: str) -> bool:
        return self.piece_at(square) == "R"

    def is_aigakari_shape(self) -> bool:
        return self.piece_at("2e") == "P" and self.piece_at("8e") == "p"

    def piece_at(self, square: str) -> str | None:
        file_number = int(square[0])
        rank = square[1]
        row = self._RANKS.index(rank)
        column = 9 - file_number
        return self.squares[row][column]

    def _has_hand(self, piece: str) -> bool:
        return piece in self.hands_part

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
