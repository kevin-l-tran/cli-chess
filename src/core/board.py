from core.moves import Move, make_move


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
            [None for _ in range(8)] for _ in range(8)
        ]
        self.white_king: tuple[int, int]
        self.black_king: tuple[int, int]
        self.white_pieces: list[tuple[int, int]] = []
        self.black_pieces: list[tuple[int, int]] = []
        self.pieces: dict[tuple[int, int], Piece] = {}

        # add white pawns
        pawn = make_piece("P", True, False)
        for i in range(8):
            self._add_piece(pawn, (1, i))

        # add white rooks
        rook = make_piece("R", True, False)
        self._add_piece(rook, (0, 0))
        self._add_piece(rook, (0, 7))

        # add white knights
        knight = make_piece("N", True, False)
        self._add_piece(knight, (0, 1))
        self._add_piece(knight, (0, 6))

        # add white bishops
        bishop = make_piece("B", True, False)
        self._add_piece(bishop, (0, 2))
        self._add_piece(bishop, (0, 5))

        # add white queen
        queen = make_piece("Q", True, False)
        self._add_piece(queen, (0, 3))

        # add white king
        king = make_piece("K", True, False)
        self._add_piece(king, (0, 4))

        # add black pawns
        pawn = make_piece("P", False, False)
        for i in range(8):
            self._add_piece(pawn, (6, i))

        # add black rooks
        rook = make_piece("R", False, False)
        self._add_piece(rook, (7, 0))
        self._add_piece(rook, (7, 7))

        # add black knights
        knight = make_piece("N", False, False)
        self._add_piece(knight, (7, 1))
        self._add_piece(knight, (7, 6))

        # add black bishops
        bishop = make_piece("B", False, False)
        self._add_piece(bishop, (7, 2))
        self._add_piece(bishop, (7, 5))

        # add black queen
        queen = make_piece("Q", False, False)
        self._add_piece(queen, (7, 3))

        # add black king
        king = make_piece("K", False, False)
        self._add_piece(king, (7, 4))

    def get_moves(self) -> list[Move]:
        return []

    def _add_piece(self, piece: Piece, position: tuple[int, int]) -> None:
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

    def _get_psuedo_moves(self) -> list[Move]:
        return []

    def _get_pawn_moves(self, piece: Piece, position: tuple[int, int]) -> list[Move]:
        return []

    def _get_rook_moves(self, rook: Piece, position: tuple[int, int]) -> list[Move]:
        moves: list[Move] = []
        moves += self._get_horizontal_slide_moves(rook, position)
        moves += self._get_vertical_slide_moves(rook, position)
        return moves

    def _get_knight_moves(self, knight: Piece, position: tuple[int, int]) -> list[Move]:
        moves: list[Move] = []
        relative_moves: list[tuple[int, int]] = [
            (2, 1),
            (2, -1),
            (-2, 1),
            (-2, -1),
            (1, 2),
            (-1, 2),
            (1, -2),
            (-1, -2),
        ]

        for rel in relative_moves:
            final = (position[0] + rel[0], position[1] + rel[1])
            square = self.board[final[0]][final[1]]
            move = _move_or_capture_or_halt(knight, square, position, final)
            if move is not None:
                moves.append(move)

        return moves

    def _get_bishop_moves(self, bishop: Piece, position: tuple[int, int]) -> list[Move]:
        moves: list[Move] = []
        moves += self._get_diagonal_slide_moves(bishop, position)
        return moves

    def _get_queen_moves(self, queen: Piece, position: tuple[int, int]) -> list[Move]:
        moves: list[Move] = []
        moves += self._get_horizontal_slide_moves(queen, position)
        moves += self._get_vertical_slide_moves(queen, position)
        moves += self._get_diagonal_slide_moves(queen, position)
        return moves

    def _get_king_moves(self, king: Piece, position: tuple[int, int]) -> list[Move]:
        moves: list[Move] = []
        relative_moves: list[tuple[int, int]] = [
            (1, 1),
            (1, 0),
            (1, -1),
            (0, 1),
            (0, -1),
            (-1, 1),
            (-1, 0),
            (-1, -1),
        ]

        for rel in relative_moves:
            final = (position[0] + rel[0], position[1] + rel[1])
            square = self.board[final[0]][final[1]]
            move = _move_or_capture_or_halt(king, square, position, final)
            if move is not None:
                moves.append(move)

        return moves

    def _get_vertical_slide_moves(
        self, piece: Piece, position: tuple[int, int]
    ) -> list[Move]:
        moves: list[Move] = []
        rank = position[1]

        up_index = position[0] + 1
        while _check_bounds((up_index, rank)):
            square = self.board[up_index][rank]
            move = _move_or_capture_or_halt(piece, square, position, (up_index, rank))
            if move is None:
                break
            else:
                moves.append(move)
            up_index += 1

        down_index = position[0] - 1
        while _check_bounds((down_index, rank)):
            square = self.board[down_index][rank]
            move = _move_or_capture_or_halt(piece, square, position, (down_index, rank))
            if move is None:
                break
            else:
                moves.append(move)
            down_index -= 1

        return moves

    def _get_horizontal_slide_moves(
        self, piece: Piece, position: tuple[int, int]
    ) -> list[Move]:
        moves: list[Move] = []
        file = position[0]

        right_index = position[1] + 1
        while _check_bounds((file, right_index)):
            square = self.board[file][right_index]
            move = _move_or_capture_or_halt(
                piece, square, position, (file, right_index)
            )
            if move is None:
                break
            else:
                moves.append(move)
            right_index += 1

        left_index = position[1] - 1
        while _check_bounds((file, left_index)):
            square = self.board[file][left_index]
            move = _move_or_capture_or_halt(piece, square, position, (file, left_index))
            if move is None:
                break
            else:
                moves.append(move)
            left_index -= 1

        return moves

    def _get_diagonal_slide_moves(
        self, piece: Piece, position: tuple[int, int]
    ) -> list[Move]:
        moves: list[Move] = []
        rank = position[1]
        file = position[0]

        up_index = file + 1
        left_index = rank - 1
        while _check_bounds((up_index, left_index)):
            square = self.board[up_index][left_index]
            move = _move_or_capture_or_halt(
                piece, square, position, (up_index, left_index)
            )
            if move is None:
                break
            else:
                moves.append(move)
            up_index += 1
            left_index -= 1

        up_index = file + 1
        right_index = rank + 1
        while _check_bounds((up_index, right_index)):
            square = self.board[up_index][right_index]
            move = _move_or_capture_or_halt(
                piece, square, position, (up_index, right_index)
            )
            if move is None:
                break
            else:
                moves.append(move)
            up_index += 1
            right_index += 1

        down_index = file - 1
        right_index = rank + 1
        while _check_bounds((down_index, right_index)):
            square = self.board[down_index][right_index]
            move = _move_or_capture_or_halt(
                piece, square, position, (down_index, right_index)
            )
            if move is None:
                break
            else:
                moves.append(move)
            down_index -= 1
            right_index += 1

        down_index = file - 1
        left_index = rank - 1
        while _check_bounds((down_index, left_index)):
            square = self.board[down_index][left_index]
            move = _move_or_capture_or_halt(
                piece, square, position, (down_index, left_index)
            )
            if move is None:
                break
            else:
                moves.append(move)
            down_index -= 1
            left_index -= 1

        return moves


def _check_bounds(position: tuple[int, int]):
    return (position[0] >= 0 and position[0] <= 7) and (
        position[1] >= 0 and position[1] <= 7
    )


def _move_or_capture_or_halt(
    piece: Piece, square: Piece | None, initial: tuple[int, int], final: tuple[int, int]
) -> Move | None:
    if square is None:
        return make_move(get_name(piece), initial, final, False)
    elif get_is_white(square) != get_is_white(piece):
        return make_move(get_name(piece), initial, final, False, get_name(square))
    else:
        return None
