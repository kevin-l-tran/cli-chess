from typing import Callable, Self
from core.moves import (
    Move,
    get_captured_piece,
    get_final_position,
    get_initial_position,
    is_en_passant,
    make_move,
)


Piece = str
"""
Represents a chess piece. The complete representation of a piece has the form:
    [N, C, M, E]
where
    N = the name of the piece
    C = "T" if the piece color is white, "F" otherwise
    M = "T" if the piece has moved, "F" otherwise
    E = "T" if the en passant rule applies to this piece, "F" otherwise
"""


def make_piece(name: str, is_white: bool, has_moved: bool, can_ep: bool):
    """
    Constructs a Piece string.

    Parameters:
        name (str): A letter representing the name of the piece.
        is_white (bool): Whether the piece is white or black.
        has_moved (bool): Whether the piece has moved.
        can_ep (bool): Whether the en passant rule applies to the piece
    """
    assert name in ["P", "R", "N", "B", "Q", "K"]

    piece = ""
    piece += name
    piece += "T" if is_white else "F"
    piece += "T" if has_moved else "F"
    piece += "T" if can_ep else "F"
    return piece


def get_name(p: Piece) -> str:
    return p[0]


def is_white(p: Piece) -> bool:
    return p[1] == "T"


def has_moved(p: Piece) -> bool:
    return p[2] == "T"


def can_ep(p: Piece) -> bool:
    return p[3] == "T"


class Board:
    """
    Represents a chess board.

    Attributes:
        board (list[list[Piece | None]]): An 8x8 array representing a board. The board is indexed by [rank][file].
        white_king (tuple[int, int]): Position of the white king.
        black_king (tuple[int, int]): Position of the black king.
        white_pieces (dict[tuple[int, int], Piece]): Map of positions to white pieces.
        black_pieces (dict[tuple[int, int], Piece]): Map of positions to white pieces.
    """

    def __init__(self) -> None:
        self.board: list[list[Piece | None]] = [
            [None for _ in range(8)] for _ in range(8)
        ]
        self.white_king: tuple[int, int]
        self.black_king: tuple[int, int]
        self.white_pieces: dict[tuple[int, int], Piece] = {}
        self.black_pieces: dict[tuple[int, int], Piece] = {}

        # add white pawns
        pawn = make_piece("P", True, False, False)
        for i in range(8):
            self._add_piece(pawn, (1, i))

        # add white rooks
        rook = make_piece("R", True, False, False)
        self._add_piece(rook, (0, 0))
        self._add_piece(rook, (0, 7))

        # add white knights
        knight = make_piece("N", True, False, False)
        self._add_piece(knight, (0, 1))
        self._add_piece(knight, (0, 6))

        # add white bishops
        bishop = make_piece("B", True, False, False)
        self._add_piece(bishop, (0, 2))
        self._add_piece(bishop, (0, 5))

        # add white queen
        queen = make_piece("Q", True, False, False)
        self._add_piece(queen, (0, 3))

        # add white king
        king = make_piece("K", True, False, False)
        self._add_piece(king, (0, 4))

        # add black pawns
        pawn = make_piece("P", False, False, False)
        for i in range(8):
            self._add_piece(pawn, (6, i))

        # add black rooks
        rook = make_piece("R", False, False, False)
        self._add_piece(rook, (7, 0))
        self._add_piece(rook, (7, 7))

        # add black knights
        knight = make_piece("N", False, False, False)
        self._add_piece(knight, (7, 1))
        self._add_piece(knight, (7, 6))

        # add black bishops
        bishop = make_piece("B", False, False, False)
        self._add_piece(bishop, (7, 2))
        self._add_piece(bishop, (7, 5))

        # add black queen
        queen = make_piece("Q", False, False, False)
        self._add_piece(queen, (7, 3))

        # add black king
        king = make_piece("K", False, False, False)
        self._add_piece(king, (7, 4))

    def get_moves(self, get_white: bool) -> set[Move]:
        moves = self._get_psuedo_moves(get_white)

        invalid_moves: set[Move] = set()
        for move in moves:
            command = self.get_move_command(move)
            command[0](self)
            if self.is_checked(get_white):
                invalid_moves.add(move)
            command[1](self)

        for move in invalid_moves:
            moves.remove(move)

        return moves

    def get_move_command(
        self, move: Move
    ) -> tuple[Callable[[Self], None], Callable[[Self], None]]:
        if move == "0-0T" or move == "0-0F":
            white = move[3] == "T"
            rank = 0 if white else 7

            king = self.board[rank][4]
            rook = self.board[rank][7]

            def apply(self: Self) -> None:
                self.board[rank][6] = make_piece("K", white, True, False)
                self.board[rank][5] = make_piece("R", white, True, False)

                self.board[rank][4] = None
                self.board[rank][7] = None

            def undo(self: Self) -> None:
                self.board[rank][4] = king
                self.board[rank][7] = rook

                self.board[rank][6] = None
                self.board[rank][5] = None

        elif move == "0-0-0T" or move == "0-0-0F":
            white = move[3] == "T"
            rank = 0 if white else 7

            king = self.board[rank][4]
            rook = self.board[rank][0]

            def apply(self: Self) -> None:
                self.board[rank][2] = make_piece("K", white, True, False)
                self.board[rank][3] = make_piece("R", white, True, False)

                self.board[rank][4] = None
                self.board[rank][0] = None

            def undo(self: Self) -> None:
                self.board[rank][4] = king
                self.board[rank][0] = rook

                self.board[rank][2] = None
                self.board[rank][3] = None

        elif is_en_passant(move):
            initial_position = get_initial_position(move)
            final_position = get_final_position(move)
            initial_piece = self.board[initial_position[0]][initial_position[1]]
            final_piece = self.board[final_position[0]][final_position[1]]
            captured_piece = self.board[initial_position[0]][final_position[1]]

            assert initial_piece is not None, "Move targets a nonexistent piece."

            def apply(self: Self) -> None:
                updated_piece = make_piece(
                    get_name(initial_piece), is_white(initial_piece), True, False
                )
                self.board[initial_position[0]][initial_position[1]] = None
                self.board[final_position[0]][final_position[1]] = updated_piece
                self.board[initial_position[0]][final_position[1]] = None

            def undo(self: Self) -> None:
                self.board[initial_position[0]][initial_position[1]] = initial_piece
                self.board[final_position[0]][final_position[1]] = None
                self.board[initial_position[0]][final_position[1]] = captured_piece

        else:
            initial_position = get_initial_position(move)
            final_position = get_final_position(move)
            initial_piece = self.board[initial_position[0]][initial_position[1]]
            final_piece = self.board[final_position[0]][final_position[1]]

            assert initial_piece is not None, "Move targets a nonexistent piece."

            def apply(self: Self) -> None:
                name = get_name(initial_piece)
                white = is_white(initial_piece)
                moved = has_moved(initial_piece)
                ep = (
                    name == "P"
                    and not moved
                    and (final_position[0] == 3 or final_position[0] == 4)
                )
                updated_piece = make_piece(name, white, True, ep)

                self.board[initial_position[0]][initial_position[1]] = None
                self.board[final_position[0]][final_position[1]] = updated_piece

            def undo(self: Self) -> None:
                self.board[initial_position[0]][initial_position[1]] = initial_piece
                self.board[final_position[0]][final_position[1]] = final_piece

        return apply, undo

    def is_checked(self, check_white: bool) -> bool:
        if check_white:
            moves = self._get_psuedo_moves(False)
        else:
            moves = self._get_psuedo_moves(True)

        return "K" in map(get_captured_piece, moves)

    def _add_piece(self, piece: Piece, position: tuple[int, int]) -> None:
        self.board[position[0]][position[1]] = piece

        if is_white(piece):
            self.white_pieces[position] = piece
        else:
            self.black_pieces[position] = piece

        if get_name(piece) == "K":
            if is_white(piece):
                self.white_king = position
            else:
                self.black_king = position

    def _get_psuedo_moves(self, get_white: bool) -> set[Move]:
        moves: set[Move] = set()

        if get_white:
            positions = self.white_pieces.keys()
        else:
            positions = self.black_pieces.keys()

        # get regular moves
        for position in positions:
            piece = self.board[position[0]][position[1]]
            assert piece is not None, "Positions and board are not aligned."

            piece_name = get_name(piece)
            if piece_name == "K":
                moves.update(self._get_king_moves(piece, position))
            elif piece_name == "Q":
                moves.update(self._get_queen_moves(piece, position))
            elif piece_name == "B":
                moves.update(self._get_bishop_moves(piece, position))
            elif piece_name == "N":
                moves.update(self._get_knight_moves(piece, position))
            elif piece_name == "R":
                moves.update(self._get_rook_moves(piece, position))
            else:
                moves.update(self._get_pawn_moves(piece, position))

        # get castle moves
        if get_white:
            king = self.board[0][4]
            q_rook = self.board[0][0]
            k_rook = self.board[0][7]
            q_squares = [self.board[0][1], self.board[0][2], self.board[0][3]]
            k_squares = [self.board[0][5], self.board[0][6]]
        else:
            king = self.board[7][4]
            q_rook = self.board[7][0]
            k_rook = self.board[7][7]
            q_squares = [self.board[7][1], self.board[7][2], self.board[7][3]]
            k_squares = [self.board[7][5], self.board[7][6]]
        if king is not None and get_name(king) == "K" and not has_moved(king):
            if (
                q_rook is not None
                and get_name(q_rook) == "R"
                and not has_moved(q_rook)
                and all(s is None for s in q_squares)
            ):
                move = "0-0-0"
                move += "T" if get_white else "F"
                moves.add(move)
            if (
                k_rook is not None
                and get_name(k_rook) == "R"
                and not has_moved(k_rook)
                and all(s is None for s in k_squares)
            ):
                move = "0-0"
                move += "T" if get_white else "F"
                moves.add(move)

        # get en passant moves
        if get_white:
            ep_positions = [
                pos for pos, pce in self.black_pieces.items() if can_ep(pce)
            ]
            pawn_positions = [
                pos for pos, pce in self.white_pieces.items() if get_name(pce) == "P"
            ]
            white_multiplier = 1
        else:
            ep_positions = [
                pos for pos, pce in self.white_pieces.items() if can_ep(pce)
            ]
            pawn_positions = [
                pos for pos, pce in self.black_pieces.items() if get_name(pce) == "P"
            ]
            white_multiplier = -1

        for p in pawn_positions:
            if (
                (p[0], p[1] - 1) in ep_positions
                and _is_in_bounds((p[0] + 1 * white_multiplier, p[1] - 1))
                and self.board[p[0] + 1 * white_multiplier][p[1] - 1] is None
            ):
                pawn = self.board[p[0]][p[1]]
                assert pawn is not None, "Positions and board are not aligned."

                move = make_move(
                    get_name(pawn),
                    p,
                    (p[0] + 1 * white_multiplier, p[1] - 1),
                    True,
                    "P",
                )
                moves.add(move)
            if (
                (p[0], p[1] + 1) in ep_positions
                and _is_in_bounds((p[0] + 1 * white_multiplier, p[1] + 1))
                and self.board[p[0] + 1 * white_multiplier][p[1] + 1] is None
            ):
                pawn = self.board[p[0]][p[1]]
                assert pawn is not None, "Positions and board are not aligned."

                move = make_move(
                    get_name(pawn),
                    p,
                    (p[0] + 1 * white_multiplier, p[1] + 1),
                    True,
                    "P",
                )
                moves.add(move)

        return moves

    def _get_pawn_moves(self, pawn: Piece, position: tuple[int, int]) -> set[Move]:
        moves: set[Move] = set()
        rank = position[0]
        file = position[1]
        white_multiplier = 1 if is_white(pawn) else -1

        # foward move
        if _is_in_bounds((rank + 1 * white_multiplier, file)):
            square = self.board[rank + 1 * white_multiplier][file]
            if square is None:
                # if pawn reaches edge, get promotion moves
                if rank + 1 * white_multiplier == 7 or rank + 1 * white_multiplier == 0:
                    for promotion in ["Q", "B", "N", "R"]:
                        move = make_move(
                            get_name(pawn),
                            position,
                            (rank + 1 * white_multiplier, file),
                            False,
                            promotion=promotion,
                        )
                        moves.add(move)
                # else get regular move
                else:
                    move = make_move(
                        get_name(pawn),
                        position,
                        (rank + 1 * white_multiplier, file),
                        False,
                    )
                    moves.add(move)

        # second forward move
        if (
            _is_in_bounds((rank + 2 * white_multiplier, file))
            and self.board[rank + 1 * white_multiplier][file] is None
            and not has_moved(pawn)
        ):
            square = self.board[rank + 2 * white_multiplier][file]
            if square is None:
                move = make_move(
                    get_name(pawn), position, (rank + 2 * white_multiplier, file), False
                )
                moves.add(move)

        # diagonal attacks
        if _is_in_bounds((rank + 1 * white_multiplier, file - 1)):
            square = self.board[rank + 1 * white_multiplier][file - 1]
            if square is not None and is_white(square) != is_white(pawn):
                move = make_move(
                    get_name(pawn),
                    position,
                    (rank + 1 * white_multiplier, file - 1),
                    False,
                    get_name(square),
                )
                moves.add(move)

        if _is_in_bounds((rank + 1 * white_multiplier, file + 1)):
            square = self.board[rank + 1 * white_multiplier][file + 1]
            if square is not None and is_white(square) != is_white(pawn):
                move = make_move(
                    get_name(pawn),
                    position,
                    (rank + 1 * white_multiplier, file + 1),
                    False,
                    get_name(square),
                )
                moves.add(move)

        return moves

    def _get_rook_moves(self, rook: Piece, position: tuple[int, int]) -> set[Move]:
        moves: set[Move] = set()
        moves.update(self._get_horizontal_slide_moves(rook, position))
        moves.update(self._get_vertical_slide_moves(rook, position))
        return moves

    def _get_knight_moves(self, knight: Piece, position: tuple[int, int]) -> set[Move]:
        moves: set[Move] = set()
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
            if _is_in_bounds(final):
                square = self.board[final[0]][final[1]]
                move = _move_or_capture_or_halt(knight, square, position, final)
                if move is not None:
                    moves.add(move)

        return moves

    def _get_bishop_moves(self, bishop: Piece, position: tuple[int, int]) -> set[Move]:
        moves: set[Move] = set()
        moves.update(self._get_diagonal_slide_moves(bishop, position))
        return moves

    def _get_queen_moves(self, queen: Piece, position: tuple[int, int]) -> set[Move]:
        moves: set[Move] = set()
        moves.update(self._get_horizontal_slide_moves(queen, position))
        moves.update(self._get_vertical_slide_moves(queen, position))
        moves.update(self._get_diagonal_slide_moves(queen, position))
        return moves

    def _get_king_moves(self, king: Piece, position: tuple[int, int]) -> set[Move]:
        moves: set[Move] = set()
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
            if _is_in_bounds(final):
                square = self.board[final[0]][final[1]]
                move = _move_or_capture_or_halt(king, square, position, final)
                if move is not None:
                    moves.add(move)

        return moves

    def _get_vertical_slide_moves(
        self, piece: Piece, position: tuple[int, int]
    ) -> set[Move]:
        moves: set[Move] = set()
        file = position[1]

        up_index = position[0] + 1
        while _is_in_bounds((up_index, file)):
            square = self.board[up_index][file]
            move = _move_or_capture_or_halt(piece, square, position, (up_index, file))
            if move is None:
                break
            else:
                moves.add(move)
            up_index += 1

        down_index = position[0] - 1
        while _is_in_bounds((down_index, file)):
            square = self.board[down_index][file]
            move = _move_or_capture_or_halt(piece, square, position, (down_index, file))
            if move is None:
                break
            else:
                moves.add(move)
            down_index -= 1

        return moves

    def _get_horizontal_slide_moves(
        self, piece: Piece, position: tuple[int, int]
    ) -> set[Move]:
        moves: set[Move] = set()
        rank = position[0]

        right_index = position[1] + 1
        while _is_in_bounds((rank, right_index)):
            square = self.board[rank][right_index]
            move = _move_or_capture_or_halt(
                piece, square, position, (rank, right_index)
            )
            if move is None:
                break
            else:
                moves.add(move)
            right_index += 1

        left_index = position[1] - 1
        while _is_in_bounds((rank, left_index)):
            square = self.board[rank][left_index]
            move = _move_or_capture_or_halt(piece, square, position, (rank, left_index))
            if move is None:
                break
            else:
                moves.add(move)
            left_index -= 1

        return moves

    def _get_diagonal_slide_moves(
        self, piece: Piece, position: tuple[int, int]
    ) -> set[Move]:
        moves: set[Move] = set()
        file = position[1]
        rank = position[0]

        up_index = rank + 1
        left_index = file - 1
        while _is_in_bounds((up_index, left_index)):
            square = self.board[up_index][left_index]
            move = _move_or_capture_or_halt(
                piece, square, position, (up_index, left_index)
            )
            if move is None:
                break
            else:
                moves.add(move)
            up_index += 1
            left_index -= 1

        up_index = rank + 1
        right_index = file + 1
        while _is_in_bounds((up_index, right_index)):
            square = self.board[up_index][right_index]
            move = _move_or_capture_or_halt(
                piece, square, position, (up_index, right_index)
            )
            if move is None:
                break
            else:
                moves.add(move)
            up_index += 1
            right_index += 1

        down_index = rank - 1
        right_index = file + 1
        while _is_in_bounds((down_index, right_index)):
            square = self.board[down_index][right_index]
            move = _move_or_capture_or_halt(
                piece, square, position, (down_index, right_index)
            )
            if move is None:
                break
            else:
                moves.add(move)
            down_index -= 1
            right_index += 1

        down_index = rank - 1
        left_index = file - 1
        while _is_in_bounds((down_index, left_index)):
            square = self.board[down_index][left_index]
            move = _move_or_capture_or_halt(
                piece, square, position, (down_index, left_index)
            )
            if move is None:
                break
            else:
                moves.add(move)
            down_index -= 1
            left_index -= 1

        return moves


def _is_in_bounds(position: tuple[int, int]):
    return (position[0] >= 0 and position[0] <= 7) and (
        position[1] >= 0 and position[1] <= 7
    )


def _move_or_capture_or_halt(
    piece: Piece, square: Piece | None, initial: tuple[int, int], final: tuple[int, int]
) -> Move | None:
    if square is None:
        return make_move(get_name(piece), initial, final, False)
    elif is_white(square) != is_white(piece):
        return make_move(get_name(piece), initial, final, False, get_name(square))
    else:
        return None
