ZENKAKU_FILES = {
    "1": "１",
    "2": "２",
    "3": "３",
    "4": "４",
    "5": "５",
    "6": "６",
    "7": "７",
    "8": "８",
    "9": "９",
}

KANJI_RANKS = {
    "a": "一",
    "b": "二",
    "c": "三",
    "d": "四",
    "e": "五",
    "f": "六",
    "g": "七",
    "h": "八",
    "i": "九",
}

PIECE_NAMES = {
    "P": "歩",
    "L": "香",
    "N": "桂",
    "S": "銀",
    "G": "金",
    "B": "角",
    "R": "飛",
    "K": "玉",
    "+P": "と",
    "+L": "杏",
    "+N": "圭",
    "+S": "全",
    "+B": "馬",
    "+R": "龍",
}

DROP_PIECES = {
    "P": "歩",
    "L": "香",
    "N": "桂",
    "S": "銀",
    "G": "金",
    "B": "角",
    "R": "飛",
}


def usi_to_japanese_move(sfen: str, usi: str) -> str:
    if not usi:
        return ""

    side = _side_to_mark(sfen)

    if "*" in usi:
        piece_code, to_square = usi.split("*", 1)
        return (
            f"{side}"
            f"{_square_to_japanese(to_square)}"
            f"{DROP_PIECES.get(piece_code.upper(), piece_code)}打"
        )

    from_square = usi[:2]
    to_square = usi[2:4]
    promote = usi.endswith("+")

    board = _parse_board_from_sfen(sfen)
    piece_code = board.get(from_square)

    piece_name = _piece_name(piece_code)

    if promote:
        piece_name += "成"

    return (
        f"{side}"
        f"{_square_to_japanese(to_square)}"
        f"{piece_name}"
    )


def _side_to_mark(sfen: str) -> str:
    parts = sfen.split()
    if len(parts) >= 2 and parts[1] == "w":
        return "△"
    return "▲"


def _square_to_japanese(square: str) -> str:
    file_char = square[0]
    rank_char = square[1]

    return (
        f"{ZENKAKU_FILES.get(file_char, file_char)}"
        f"{KANJI_RANKS.get(rank_char, rank_char)}"
    )


def _piece_name(piece_code: str | None) -> str:
    if piece_code is None:
        return "?"
    promoted = piece_code.startswith("+")
    base = piece_code[-1].upper()

    if promoted:
        return PIECE_NAMES.get(f"+{base}", PIECE_NAMES.get(base, base))

    return PIECE_NAMES.get(base, base)


def _parse_board_from_sfen(sfen: str) -> dict[str, str]:
    board_part = sfen.split()[0]
    ranks = board_part.split("/")

    board = {}

    for rank_index, rank_text in enumerate(ranks):
        rank = chr(ord("a") + rank_index)
        file_number = 9
        promoted = False

        for char in rank_text:
            if char.isdigit():
                file_number -= int(char)
                continue

            if char == "+":
                promoted = True
                continue

            piece = f"+{char}" if promoted else char
            square = f"{file_number}{rank}"
            board[square] = piece

            promoted = False
            file_number -= 1

    return board

def format_usi_move_with_japanese(sfen: str, usi: str) -> str:
    japanese = usi_to_japanese_move(sfen, usi)
    if japanese.endswith("?"):
        return usi
    return f"{usi}（{japanese}）"


def format_usi_pv_with_japanese(sfen: str, pv: str) -> str:
    if not pv:
        return ""

    board_sfen = sfen
    formatted_moves = []

    for usi in pv.split():
        formatted_moves.append(
            format_usi_move_with_japanese(board_sfen, usi)
        )
        board_sfen = apply_usi_move_to_sfen(board_sfen, usi)

    return " ".join(formatted_moves)

def apply_usi_move_to_sfen(sfen: str, usi: str) -> str:
    parts = sfen.split()
    board_part = parts[0]
    side = parts[1] if len(parts) > 1 else "b"
    hands = parts[2] if len(parts) > 2 else "-"
    move_number = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1

    board = _parse_board_from_sfen(sfen)

    if "*" in usi:
        piece_code, to_square = usi.split("*", 1)
        board[to_square] = piece_code.upper() if side == "b" else piece_code.lower()
    else:
        from_square = usi[:2]
        to_square = usi[2:4]
        promote = usi.endswith("+")

        piece = board.pop(from_square, None)
        if piece is not None:
            if promote and not piece.startswith("+"):
                piece = f"+{piece}"
            board[to_square] = piece

    next_side = "w" if side == "b" else "b"
    next_board = _board_to_sfen_board(board)

    return f"{next_board} {next_side} {hands} {move_number + 1}"

def _board_to_sfen_board(board: dict[str, str]) -> str:
    ranks = []

    for rank_index in range(9):
        rank = chr(ord("a") + rank_index)
        empty_count = 0
        rank_text = []

        for file_number in range(9, 0, -1):
            square = f"{file_number}{rank}"
            piece = board.get(square)

            if piece is None:
                empty_count += 1
                continue

            if empty_count:
                rank_text.append(str(empty_count))
                empty_count = 0

            rank_text.append(piece)

        if empty_count:
            rank_text.append(str(empty_count))

        ranks.append("".join(rank_text))

    return "/".join(ranks)
