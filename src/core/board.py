Piece = str
"""
Represents a chess piece. The complete representation of a piece has the form:
    [N, C, M]
where
    N = the name of the piece
    C = "T" if the piece color is white, "F" otherwise
    M = "T" if the piece has moved, "F" otherwise
"""


def make_piece(name: str, is_white: bool, has_moved: bool):
    """
    Constructs a Piece string.

    Parameters:
        name (str): A letter representing the name of the piece.
        is_white (bool): Whether the piece is white or black.
        has_moved (bool): Whether the piece has moved.
    """
    assert name in ["P", "R", "N", "B", "Q", "K"]

    piece = ""
    piece += name
    piece += "T" if is_white else "F"
    piece += "T" if has_moved else "F"
    return piece


def get_name(p: Piece) -> str:
    return p[0]


def get_is_white(p: Piece) -> bool:
    return p[1] == "T"


def get_has_moved(p: Piece) -> bool:
    return p[2] == "T"


class Board:
    """
    Represents a chess board.

    Attributes: 
        board (list[list[Piece | None]]): An 8x8 array representing a board.
        white_king (tuple[int, int]): Position of the white king.
        black_king (tuple[int, int]): Position of the black king.
        white_pieces (list[tuple[int, int]]): List of positions of all white pieces.
        black_pieces (list[tuple[int, int]]): List of positions of all black pieces.
        pieces (dict[tuple[int, int], Piece]): Map from position to piece.
    """

    def __init__(self) -> None:
        self.board: list[list[Piece | None]] = [
            [None for _ in range(8)] for _ in range(8)]
        self.white_king: tuple[int, int]
        self.black_king: tuple[int, int]
        self.white_pieces: list[tuple[int, int]] = []
        self.black_pieces: list[tuple[int, int]] = []
        self.pieces: dict[tuple[int, int], Piece] = {}

        # add white pawns
        pawn = make_piece("P", True, False)
        for i in range(8):
            self.add_piece(pawn, (1, i))

        # add white rooks
        rook = make_piece("R", True, False)
        self.add_piece(rook, (0, 0))
        self.add_piece(rook, (0, 7))

        # add white knights
        knight = make_piece("N", True, False)
        self.add_piece(knight, (0, 1))
        self.add_piece(knight, (0, 6))

        # add white bishops
        bishop = make_piece("B", True, False)
        self.add_piece(bishop, (0, 2))
        self.add_piece(bishop, (0, 5))

        # add white queen
        queen = make_piece("Q", True, False)
        self.add_piece(queen, (0, 3))

        # add white king
        king = make_piece("K", True, False)
        self.add_piece(king, (0, 4))

        # add black pawns
        pawn = make_piece("P", False, False)
        for i in range(8):
            self.add_piece(pawn, (6, i))

        # add black rooks
        rook = make_piece("R", False, False)
        self.add_piece(rook, (7, 0))
        self.add_piece(rook, (7, 7))

        # add black knights
        knight = make_piece("N", False, False)
        self.add_piece(knight, (7, 1))
        self.add_piece(knight, (7, 6))

        # add black bishops
        bishop = make_piece("B", False, False)
        self.add_piece(bishop, (7, 2))
        self.add_piece(bishop, (7, 5))

        # add black queen
        queen = make_piece("Q", False, False)
        self.add_piece(queen, (7, 3))

        # add black king
        king = make_piece("K", False, False)
        self.add_piece(king, (7, 4))

    def add_piece(self, piece: Piece, position: tuple[int, int]) -> None:
        self.board[position[0]][position[1]] = piece
        self.pieces[position] = piece

        if get_is_white(piece):
            self.white_pieces.append(position)
        else:
            self.black_pieces.append(position)

        if get_name(piece) == "K":
            if get_is_white(piece):
                self.white_king = position
            else:
                self.black_king = position
