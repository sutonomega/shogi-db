"""
SFEN generator for parsed KIF records.

The KIF parser keeps the original move notation. This module owns the next
step: KIF move notation -> USI -> board replay -> SFEN.
"""

import re
from dataclasses import dataclass

from .kif_parser import Candidate, GameRecord


@dataclass
class PositionRecord:
    move_number: int
    sfen: str
    move_usi: str | None
    eval: int | None
    best_move: str | None
    pv: str | None
    candidates: list[Candidate]


class SfenGenerationError(ValueError):
    """Raised when a KIF move cannot be converted or applied."""


class SfenGenerator:
    _RANK_TO_USI = {
        "1": "a", "１": "a", "一": "a",
        "2": "b", "２": "b", "二": "b",
        "3": "c", "３": "c", "三": "c",
        "4": "d", "４": "d", "四": "d",
        "5": "e", "５": "e", "五": "e",
        "6": "f", "６": "f", "六": "f",
        "7": "g", "７": "g", "七": "g",
        "8": "h", "８": "h", "八": "h",
        "9": "i", "９": "i", "九": "i",
    }
    _FILE_TO_USI = {
        "1": "1", "１": "1",
        "2": "2", "２": "2",
        "3": "3", "３": "3",
        "4": "4", "４": "4",
        "5": "5", "５": "5",
        "6": "6", "６": "6",
        "7": "7", "７": "7",
        "8": "8", "８": "8",
        "9": "9", "９": "9",
    }
    _DROP_PIECES = {
        "歩": "P",
        "香": "L",
        "桂": "N",
        "銀": "S",
        "金": "G",
        "角": "B",
        "飛": "R",
    }
    _HAND_ORDER = ("R", "B", "G", "S", "N", "L", "P")
    _PROMOTABLE = {"P", "L", "N", "S", "B", "R"}
    _RE_SOURCE = re.compile(r"\(([1-9１-９]{2})\)")

    def generate(self, game: GameRecord) -> list[PositionRecord]:
        board = _Board()
        positions = [
            PositionRecord(
                move_number=0,
                sfen=board.to_sfen(),
                move_usi=None,
                eval=None,
                best_move=None,
                pv=None,
                candidates=[],
            )
        ]

        previous_to: tuple[int, int] | None = None
        for move in game.moves:
            try:
                move_usi, previous_to = self.kif_to_usi(move.move_kif, previous_to)
                board.apply_usi(move_usi, move.move_number, move.move_kif)
            except SfenGenerationError:
                raise
            except Exception as exc:
                raise SfenGenerationError(
                    f"Failed to generate SFEN at move {move.move_number}: "
                    f"{move.move_kif}"
                ) from exc

            move.move_usi = move_usi
            positions.append(
                PositionRecord(
                    move_number=move.move_number,
                    sfen=board.to_sfen(),
                    move_usi=move_usi,
                    eval=move.eval,
                    best_move=move.best_move,
                    pv=move.pv,
                    candidates=move.candidates,
                )
            )

        return positions

    def kif_to_usi(
        self, move_kif: str, previous_to: tuple[int, int] | None = None
    ) -> tuple[str, tuple[int, int]]:
        text = move_kif.replace(" ", "").replace("　", "")
        source_match = self._RE_SOURCE.search(text)
        source_text = source_match.group(1) if source_match else None
        main_text = self._RE_SOURCE.sub("", text)

        to_square, rest = self._parse_destination(main_text, previous_to)

        if "打" in rest:
            piece = self._parse_drop_piece(rest)
            return f"{piece}*{self._square_to_usi(to_square)}", to_square

        if source_text is None:
            raise SfenGenerationError(
                f"Move source is missing for KIF move: {move_kif}"
            )

        from_square = self._parse_source_square(source_text)
        promote = self._is_promoting_move(rest)
        suffix = "+" if promote else ""
        return (
            f"{self._square_to_usi(from_square)}{self._square_to_usi(to_square)}{suffix}",
            to_square,
        )

    def _parse_destination(
        self, text: str, previous_to: tuple[int, int] | None
    ) -> tuple[tuple[int, int], str]:
        if text.startswith("同"):
            if previous_to is None:
                raise SfenGenerationError("Same-square move has no previous move")
            return previous_to, text[1:]

        if len(text) < 2:
            raise SfenGenerationError(f"Destination is missing for KIF move: {text}")

        file_char = text[0]
        rank_char = text[1]
        if file_char not in self._FILE_TO_USI or rank_char not in self._RANK_TO_USI:
            raise SfenGenerationError(f"Unsupported destination in KIF move: {text}")

        return (int(self._FILE_TO_USI[file_char]), self._rank_char_to_number(rank_char)), text[2:]

    def _parse_source_square(self, source_text: str) -> tuple[int, int]:
        file_char = source_text[0]
        rank_char = source_text[1]
        if file_char not in self._FILE_TO_USI or rank_char not in self._FILE_TO_USI:
            raise SfenGenerationError(f"Unsupported source square: {source_text}")
        return int(self._FILE_TO_USI[file_char]), int(self._FILE_TO_USI[rank_char])

    def _parse_drop_piece(self, rest: str) -> str:
        for label, usi_piece in self._DROP_PIECES.items():
            if label in rest:
                return usi_piece
        raise SfenGenerationError(f"Unsupported drop piece in KIF move: {rest}")

    def _is_promoting_move(self, rest: str) -> bool:
        if "不成" in rest:
            return False
        if rest in ("成銀", "成桂", "成香"):
            return False
        return rest.endswith("成")

    def _rank_char_to_number(self, rank_char: str) -> int:
        return "abcdefghi".index(self._RANK_TO_USI[rank_char]) + 1

    def _square_to_usi(self, square: tuple[int, int]) -> str:
        file_number, rank_number = square
        return f"{file_number}{chr(ord('a') + rank_number - 1)}"


class _Board:
    def __init__(self) -> None:
        self.squares: dict[tuple[int, int], str] = {}
        self.hands = {
            "b": {piece: 0 for piece in SfenGenerator._HAND_ORDER},
            "w": {piece: 0 for piece in SfenGenerator._HAND_ORDER},
        }
        self.turn = "b"
        self.ply = 1
        self._setup_initial_position()

    def _setup_initial_position(self) -> None:
        rows = {
            1: "lnsgkgsnl",
            2: "1r5b1",
            3: "ppppppppp",
            7: "PPPPPPPPP",
            8: "1B5R1",
            9: "LNSGKGSNL",
        }
        for rank, row in rows.items():
            file_number = 9
            for char in row:
                if char.isdigit():
                    file_number -= int(char)
                    continue
                self.squares[(file_number, rank)] = char
                file_number -= 1

    def apply_usi(self, move_usi: str, move_number: int, move_kif: str) -> None:
        if "*" in move_usi:
            self._apply_drop(move_usi, move_number, move_kif)
        else:
            self._apply_move(move_usi, move_number, move_kif)
        self.turn = "w" if self.turn == "b" else "b"
        self.ply += 1

    def _apply_drop(self, move_usi: str, move_number: int, move_kif: str) -> None:
        piece, to_usi = move_usi.split("*", 1)
        to_square = self._usi_square_to_tuple(to_usi)
        board_piece = piece if self.turn == "b" else piece.lower()

        if self.squares.get(to_square):
            raise SfenGenerationError(
                f"Drop target is occupied at move {move_number}: {move_kif}"
            )
        if self.hands[self.turn][piece] <= 0:
            raise SfenGenerationError(
                f"Piece is not in hand at move {move_number}: {move_kif}"
            )

        self.hands[self.turn][piece] -= 1
        self.squares[to_square] = board_piece

    def _apply_move(self, move_usi: str, move_number: int, move_kif: str) -> None:
        from_square = self._usi_square_to_tuple(move_usi[:2])
        to_square = self._usi_square_to_tuple(move_usi[2:4])
        promote = move_usi.endswith("+")
        piece = self.squares.pop(from_square, None)

        if piece is None:
            raise SfenGenerationError(
                f"Move source is empty at move {move_number}: {move_kif}"
            )
        if self.turn == "b" and not piece[-1].isupper():
            raise SfenGenerationError(
                f"Black cannot move white piece at move {move_number}: {move_kif}"
            )
        if self.turn == "w" and not piece[-1].islower():
            raise SfenGenerationError(
                f"White cannot move black piece at move {move_number}: {move_kif}"
            )

        captured = self.squares.pop(to_square, None)
        if captured is not None:
            self.hands[self.turn][captured[-1].upper()] += 1

        if promote:
            piece = self._promote(piece, move_number, move_kif)

        self.squares[to_square] = piece

    def to_sfen(self) -> str:
        rows = []
        for rank in range(1, 10):
            empty_count = 0
            row_parts = []
            for file_number in range(9, 0, -1):
                piece = self.squares.get((file_number, rank))
                if piece is None:
                    empty_count += 1
                    continue
                if empty_count:
                    row_parts.append(str(empty_count))
                    empty_count = 0
                row_parts.append(piece)
            if empty_count:
                row_parts.append(str(empty_count))
            rows.append("".join(row_parts))

        return f"{'/'.join(rows)} {self.turn} {self._hands_to_sfen()} {self.ply}"

    def _hands_to_sfen(self) -> str:
        parts = []
        for piece in SfenGenerator._HAND_ORDER:
            count = self.hands["b"][piece]
            if count:
                parts.append(f"{count if count > 1 else ''}{piece}")
        for piece in SfenGenerator._HAND_ORDER:
            count = self.hands["w"][piece]
            if count:
                parts.append(f"{count if count > 1 else ''}{piece.lower()}")
        return "".join(parts) if parts else "-"

    def _promote(self, piece: str, move_number: int, move_kif: str) -> str:
        base = piece[-1].upper()
        if base not in SfenGenerator._PROMOTABLE:
            raise SfenGenerationError(
                f"Piece cannot promote at move {move_number}: {move_kif}"
            )
        return f"+{piece[-1]}"

    def _usi_square_to_tuple(self, square: str) -> tuple[int, int]:
        file_number = int(square[0])
        rank_number = ord(square[1]) - ord("a") + 1
        if not 1 <= file_number <= 9 or not 1 <= rank_number <= 9:
            raise SfenGenerationError(f"Invalid USI square: {square}")
        return file_number, rank_number
