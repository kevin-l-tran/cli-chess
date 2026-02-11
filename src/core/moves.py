Move = str
"""
Represents a chess move. The complete representation of a move has the form:
    [N, rf(1), c, rf(2), E, C, F, P, A]
where 
    N     = name of the piece,
    rf(1) = initial rank, file,
    c     = name of the captured piece, '-' otherwise,
    rf(2) = final rank, file,
    E     = T if en-passant, F otherwise,
    P     = name of promotion piece, _ otherwise.

Castling is a special move represented by 0-0C and 0-0-0C for kingside and queenside castling respectively, where C is T if white castled and F otherwise.
"""


def _verify_position(position: tuple[int, int]) -> bool:
    return (
        len(position) == 2
        and position[0] in [0, 1, 2, 3, 4, 5, 6, 7]
        and position[1] in [0, 1, 2, 3, 4, 5, 6, 7]
    )


def _is_castle(move: Move) -> bool:
    return move[0:3] == "0-0" or move[0:5] == "0-0-0"


def _is_k_castle(move: Move) -> bool:
    return len(move) == 4


def _is_white_castle(move: Move) -> bool:
    return move[3] == "T" or move[5] == "T"


def make_move(
    piece_name: str,
    initial_position: tuple[int, int],
    final_position: tuple[int, int],
    en_passant: bool,
    capture_name: str | None = None,
    promotion: str | None = None,
) -> Move:
    """
    Constructs a Move string.

    Parameters:
        piece_name (str): The character representing the moved piece.
        initial_position (tuple[int, int]): The initial position (rank, file) of the moved piece.
        final_position (tuple[int, int]): The final position (rank, file) of the moved piece.
        capture_name (str): The name of the captured piece, if any.
        en_passant (bool): Whether the move was an en passant.
        promotion (str | None): The character representing the promotion piece, if a promotion occurred.
    """
    assert piece_name in ["P", "R", "N", "B", "Q", "K"]
    assert capture_name is None or capture_name in [
        "P", "R", "N", "B", "Q", "K"]
    assert promotion is None or promotion in ["R", "N", "B", "Q"]
    assert _verify_position(initial_position)
    assert _verify_position(final_position)

    move: Move = ""

    move += piece_name
    move += str(initial_position[0])
    move += str(initial_position[1])
    move += capture_name if capture_name else "-"
    move += str(final_position[0])
    move += str(final_position[1])
    move += "T" if en_passant else "F"
    move += promotion if promotion else "_"

    return move


def get_piece(move: Move) -> str:
    if _is_castle(move):
        return "K"
    else:
        return move[0]


def get_initial_position(move: Move) -> tuple[int, int]:
    if _is_castle(move):
        rank = 0 if _is_white_castle(move) else 7
        return (rank, 4)
    else:
        return (int(move[1]), int(move[2]))


def get_captured_piece(move: Move) -> str | None:
    if _is_castle(move):
        return None
    else:
        return move[3] if move[3] != "-" else None


def get_final_position(move: Move) -> tuple[int, int]:
    if _is_castle(move):
        rank = 0 if _is_white_castle(move) else 7
        file = 6 if _is_k_castle(move) else 2
        return (rank, file)
    else:
        return (int(move[4]), int(move[5]))


def is_en_passant(move: Move) -> bool:
    if _is_castle(move):
        return False
    else:
        return move[6] == "T"


def get_promotion(move: Move) -> str | None:
    if _is_castle(move):
        return None
    else:
        return move[7] if move[7] != "_" else None


def get_standard_representation(move: Move) -> str:
    return "not implemented"


def get_extended_representation(move: Move) -> str:
    return "not implemented"


def get_full_representation(move: Move) -> str:
    return "not implemented"
