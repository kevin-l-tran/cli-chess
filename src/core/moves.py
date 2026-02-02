Move = str
"""
Represents a chess move. The complete representation of a move has the form:
    [N, fr(1), c, fr(2), E, C, F, P, A]
where 
    N     = name of the piece,
    fr(1) = initial file (str), rank (int)
    c     = 'x' if there was a capture, '-' otherwise
    fr(2) = final file (str), rank (int)
    E     = T if en-passant, F otherwise
    C     = T if check, F otherwise
    F     = T if checkmate, F otherwise
    P     = name of promotion piece, _ otherwise
    A     = move rating, _ otherwise
"""


def _verify_position(position: tuple[int, int]) -> bool:
    return (
        len(position) == 2
        and position[0] in [0, 1, 2, 3, 4, 5, 6, 7]
        and position[1] in [0, 1, 2, 3, 4, 5, 6, 7]
    )


def make_move(
    piece: str,
    initial_position: tuple[int, int],
    final_position: tuple[int, int],
    capture: bool,
    en_passant: bool,
    check: bool,
    checkmate: bool,
    promotion: str | None,
    annotation: str | None,
) -> Move:
    """
    Constructs a Move string.

    Parameters:
        piece (str): The character representing the moved piece.
        initial_position (tuple[int, int]): The initial position (file,rank) of the moved piece.
        final_position (tuple[int, int]): The final position (file,rank) of the moved piece.
        capture (bool): Whether a piece was captured during the move.
        en_passant (bool): Whether the move was an en passant.
        check (bool): Whether the move resulted in a check.
        checkmate (bool): Whether the move resulted in a checkmate.
        promotion (str | None): The character representing the promotion piece, if a promotion occurred.
        annotation (str | None): The rating of the move, if any.
    """
    assert piece in ["P", "R", "N", "B", "Q", "K"]
    assert _verify_position(initial_position)
    assert _verify_position(final_position)
    assert promotion is None or promotion in ["P", "R", "N", "B", "Q", "K"]
    assert annotation is None or annotation in ["!!", "!", "!?", "?!", "?", "??", "--"]

    move: Move = ""

    move += piece
    move += chr(initial_position[0] + ord("a") - 1)
    move += str(initial_position[1])
    move += "x" if capture else "-"
    move += chr(final_position[0] + ord("a") - 1)
    move += str(final_position[1])
    move += "T" if en_passant else "F"
    move += "T" if check else "F"
    move += "T" if checkmate else "F"
    move += promotion if promotion else "_"
    move += annotation if annotation else "_"

    return move


def get_piece(move: Move) -> str:
    return move[0]


def get_initial_position(move: Move) -> tuple[int, int]:
    return (int(ord(move[1]) - ord("a")), int(move[2]))


def is_capture(move: Move) -> bool:
    return move[3] == "x"


def get_final_position(move: Move) -> tuple[int, int]:
    return (int(ord(move[4]) - ord("a")), int(move[5]))


def is_en_passant(move: Move) -> bool:
    return move[6] == "T"


def is_check(move: Move) -> bool:
    return move[7] == "T"


def is_checkmate(move: Move) -> bool:
    return move[8] == "T"


def get_promotion(move: Move) -> str | None:
    return move[9] if move[9] != "_" else None


def get_rating(move: Move) -> str | None:
    return move[10:] if move[10] != "_" else None


def get_standard_representation(move: Move) -> str:
    return "not implemented"


def get_extended_representation(move: Move) -> str:
    return "not implemented"


def get_full_representation(move: Move) -> str:
    return "not implemented"
