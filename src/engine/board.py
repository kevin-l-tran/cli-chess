from typing import Callable, Self
from .moves import (
    Move,
    get_castle,
    get_final_position,
    get_initial_position,
    get_promotion,
    is_en_passant,
    make_move,
)


Piece = str
"""
Represents a chess piece. The complete representation of a piece has the form:
    [N, C, M]
where
    N = the name of the piece
    C = "T" if the piece color is white, "F" otherwise
    M = "T" if the piece has moved, "F" otherwise
"""

Position = tuple[int, int]
"""Board positions are represented as (file, rank)."""


def make_piece(name: str, is_white: bool, has_moved: bool) -> Piece:
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


def is_white(p: Piece) -> bool:
    return p[1] == "T"


def has_moved(p: Piece) -> bool:
    return p[2] == "T"


# Deltas are expressed as (delta_file, delta_rank).
QUEEN_DELTAS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
BISHOP_DELTAS = [(1, 1), (-1, -1), (-1, 1), (1, -1)]
ROOK_DELTAS = [(0, 1), (1, 0), (-1, 0), (0, -1)]
KING_DELTAS = [
    (1, 1),
    (1, 0),
    (1, -1),
    (0, 1),
    (0, -1),
    (-1, 1),
    (-1, 0),
    (-1, -1),
]
KNIGHT_DELTAS = [
    (2, 1),
    (2, -1),
    (-2, 1),
    (-2, -1),
    (1, 2),
    (-1, 2),
    (1, -2),
    (-1, -2),
]


class Board:
    """
    Represents a chess board.

    Attributes:
        board (list[list[Piece | None]]): An 8x8 array representing a board. The board is indexed by [rank][file].
        white_king (tuple[int, int]): Position of the white king as (file, rank).
        black_king (tuple[int, int]): Position of the black king as (file, rank).
        en_passant_pawn (tuple[int, int] | None): Position of the pawn whom en passant can be applied to, as (file, rank).
        white_pieces (dict[tuple[int, int], Piece]): Map of positions to white pieces using (file, rank).
        black_pieces (dict[tuple[int, int], Piece]): Map of positions to black pieces using (file, rank).
    """

    def __init__(self) -> None:
        self.board: list[list[Piece | None]] = [
            [None for _ in range(8)] for _ in range(8)
        ]
        self.white_king: Position
        self.black_king: Position
        self.en_passant_pawn: Position | None = None
        self.white_pieces: dict[Position, Piece] = {}
        self.black_pieces: dict[Position, Piece] = {}

        # add white pawns
        pawn = make_piece("P", True, False)
        for file in range(8):
            self._add_piece(pawn, (file, 1))

        # add white rooks
        rook = make_piece("R", True, False)
        self._add_piece(rook, (0, 0))
        self._add_piece(rook, (7, 0))

        # add white knights
        knight = make_piece("N", True, False)
        self._add_piece(knight, (1, 0))
        self._add_piece(knight, (6, 0))

        # add white bishops
        bishop = make_piece("B", True, False)
        self._add_piece(bishop, (2, 0))
        self._add_piece(bishop, (5, 0))

        # add white queen
        queen = make_piece("Q", True, False)
        self._add_piece(queen, (3, 0))

        # add white king
        king = make_piece("K", True, False)
        self._add_piece(king, (4, 0))

        # add black pawns
        pawn = make_piece("P", False, False)
        for file in range(8):
            self._add_piece(pawn, (file, 6))

        # add black rooks
        rook = make_piece("R", False, False)
        self._add_piece(rook, (0, 7))
        self._add_piece(rook, (7, 7))

        # add black knights
        knight = make_piece("N", False, False)
        self._add_piece(knight, (1, 7))
        self._add_piece(knight, (6, 7))

        # add black bishops
        bishop = make_piece("B", False, False)
        self._add_piece(bishop, (2, 7))
        self._add_piece(bishop, (5, 7))

        # add black queen
        queen = make_piece("Q", False, False)
        self._add_piece(queen, (3, 7))

        # add black king
        king = make_piece("K", False, False)
        self._add_piece(king, (4, 7))

    def get_moves(self, get_white: bool) -> set[Move]:
        # generate psuedo moves
        moves = self._get_psuedo_moves(get_white)

        # remove invalid castle moves
        rank = 0 if get_white else 7
        k_castle_squares = [(4, rank), (5, rank), (6, rank)]
        q_castle_squares = [(4, rank), (3, rank), (2, rank)]

        attacked_squares = self._get_squares_attacked_by(not get_white)
        if attacked_squares.intersection(k_castle_squares):
            castle_move = make_move("K", (4, rank), (6, rank), False)
            moves.discard(castle_move)
        if attacked_squares.intersection(q_castle_squares):
            castle_move = make_move("K", (4, rank), (2, rank), False)
            moves.discard(castle_move)

        # remove moves that result in king capture
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
        prev_ep_pawn = self.en_passant_pawn

        if get_castle(move) is not None:
            initial_king_position = get_initial_position(move)
            final_king_position = get_final_position(move)

            initial_king = self._get_square(initial_king_position)
            assert initial_king is not None, "Castle targets a nonexistent king."

            white = is_white(initial_king)
            updated_king = make_piece("K", white, True)

            king_file, king_rank = initial_king_position

            if get_castle(move) == "0-0":
                initial_rook_position = (7, king_rank)
                final_rook_position = (5, king_rank)
            else:
                initial_rook_position = (0, king_rank)
                final_rook_position = (3, king_rank)

            initial_rook = self._get_square(initial_rook_position)
            assert initial_rook is not None, "Castle targets a nonexistent rook."
            updated_rook = make_piece("R", white, True)

            def apply(self: Self) -> None:
                self._make_move(
                    updated_king, initial_king_position, final_king_position
                )
                self._make_move(
                    updated_rook, initial_rook_position, final_rook_position
                )

            def undo(self: Self) -> None:
                self._undo_move(
                    initial_king,
                    initial_king_position,
                    final_king_position,
                    prev_ep_pawn,
                )
                self._undo_move(
                    initial_rook,
                    initial_rook_position,
                    final_rook_position,
                    prev_ep_pawn,
                )

        elif is_en_passant(move):
            initial_position = get_initial_position(move)
            final_position = get_final_position(move)
            captured_position = (final_position[0], initial_position[1])
            initial_pawn = self._get_square(initial_position)
            captured_pawn = self._get_square(captured_position)

            assert initial_pawn is not None, "En passant targets a nonexistent pawn."
            assert captured_pawn is not None, "En passant captures a nonexistent pawn."

            updated_pawn = make_piece(
                get_name(initial_pawn), is_white(initial_pawn), True
            )

            def apply(self: Self) -> None:
                # move capturing pawn
                self._make_move(updated_pawn, initial_position, final_position)

                # remove captured pawn
                self._set_square(captured_position, None)
                if is_white(initial_pawn):
                    self.black_pieces.pop(captured_position)
                else:
                    self.white_pieces.pop(captured_position)

            def undo(self: Self) -> None:
                # move capturing pawn
                self._undo_move(
                    initial_pawn, initial_position, final_position, prev_ep_pawn
                )

                # add captured pawn
                self._set_square(captured_position, captured_pawn)
                if is_white(initial_pawn):
                    self.black_pieces[captured_position] = captured_pawn
                else:
                    self.white_pieces[captured_position] = captured_pawn

        else:
            initial_position = get_initial_position(move)
            final_position = get_final_position(move)
            initial_piece = self._get_square(initial_position)
            captured_piece = self._get_square(final_position)

            assert initial_piece is not None, "Move targets a nonexistent piece."

            name = get_promotion(move) or get_name(initial_piece)
            white = is_white(initial_piece)
            updated_piece = make_piece(name, white, True)
            set_ep = (
                get_name(initial_piece) == "P"
                and abs(final_position[1] - initial_position[1]) == 2
            )

            def apply(self: Self) -> None:
                self._make_move(
                    updated_piece,
                    initial_position,
                    final_position,
                    final_position if set_ep else None,
                )

            def undo(self: Self) -> None:
                self._undo_move(
                    initial_piece,
                    initial_position,
                    final_position,
                    prev_ep_pawn,
                    captured_piece,
                )

        return apply, undo

    def is_checked(self, check_white: bool) -> bool:
        if check_white:
            king_pos = self.white_king
        else:
            king_pos = self.black_king

        attacked = self._get_squares_attacked_by(not check_white)
        return king_pos in attacked

    def piece_at(self, position: Position) -> Piece | None:
        return self.board[position[1]][position[0]]

    def king_position(self, white: bool) -> Position:
        return self.white_king if white else self.black_king

    def _get_square(self, position: Position) -> Piece | None:
        return self.board[position[1]][position[0]]

    def _set_square(self, position: Position, piece: Piece | None) -> None:
        self.board[position[1]][position[0]] = piece

    def _add_delta(self, position: Position, delta: Position) -> Position:
        return (position[0] + delta[0], position[1] + delta[1])

    def _get_squares_attacked_by(self, white: bool) -> set[Position]:
        pieces = self.white_pieces if white else self.black_pieces

        positions: set[Position] = set()
        for pos, pce in pieces.items():
            name = get_name(pce)
            if name == "K":
                positions.update(self._get_king_squares(pos))
            elif name == "Q":
                positions.update(self._get_queen_squares(pos))
            elif name == "B":
                positions.update(self._get_bishop_squares(pos))
            elif name == "N":
                positions.update(self._get_knight_squares(pos))
            elif name == "R":
                positions.update(self._get_rook_squares(pos))
            else:  # pawns attack diagonally
                rank_step = 1 if white else -1
                pawn_positions = [
                    (pos[0] + 1, pos[1] + rank_step),
                    (pos[0] - 1, pos[1] + rank_step),
                ]
                for p in pawn_positions:
                    if _is_in_bounds(p):
                        positions.add(p)

        return positions

    def _add_piece(self, piece: Piece, position: Position) -> None:
        self._set_square(position, piece)

        if is_white(piece):
            self.white_pieces[position] = piece
        else:
            self.black_pieces[position] = piece

        if get_name(piece) == "K":
            if is_white(piece):
                self.white_king = position
            else:
                self.black_king = position

    def _make_move(
        self,
        updated_piece: Piece,
        initial: Position,
        final: Position,
        set_ep: Position | None = None,
    ) -> None:
        # move updated piece
        self._set_square(initial, None)
        self._set_square(final, updated_piece)

        # update dicts:
        if is_white(updated_piece):
            self.white_pieces.pop(initial, None)
            self.black_pieces.pop(final, None)
            self.white_pieces[final] = updated_piece
            if get_name(updated_piece) == "K":
                self.white_king = final
        else:
            self.black_pieces.pop(initial, None)
            self.white_pieces.pop(final, None)
            self.black_pieces[final] = updated_piece
            if get_name(updated_piece) == "K":
                self.black_king = final

        self.en_passant_pawn = set_ep

    def _undo_move(
        self,
        original_piece: Piece,
        initial: Position,
        final: Position,
        prev_ep_pawn: Position | None,
        captured_piece: Piece | None = None,
    ) -> None:
        # revert moved piece
        self._set_square(initial, original_piece)

        # add back captured piece
        self._set_square(final, captured_piece)

        # update dicts:
        if is_white(original_piece):
            self.white_pieces.pop(final, None)
            self.white_pieces[initial] = original_piece
            if captured_piece:
                self.black_pieces[final] = captured_piece
            if get_name(original_piece) == "K":
                self.white_king = initial
        else:
            self.black_pieces.pop(final, None)
            self.black_pieces[initial] = original_piece
            if captured_piece:
                self.white_pieces[final] = captured_piece
            if get_name(original_piece) == "K":
                self.black_king = initial

        # revert en passant pawn
        self.en_passant_pawn = prev_ep_pawn

    def _get_psuedo_moves(self, get_white: bool) -> set[Move]:
        moves: set[Move] = set()

        positions = self.white_pieces.keys() if get_white else self.black_pieces.keys()

        # get regular moves
        for position in positions:
            piece = self._get_square(position)
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
        rank = 0 if get_white else 7
        king = self._get_square((4, rank))
        q_rook = self._get_square((0, rank))
        k_rook = self._get_square((7, rank))
        q_squares = [
            self._get_square((1, rank)),
            self._get_square((2, rank)),
            self._get_square((3, rank)),
        ]
        k_squares = [self._get_square((5, rank)), self._get_square((6, rank))]

        if (
            king is not None
            and get_name(king) == "K"
            and not has_moved(king)
            and is_white(king) == get_white
        ):
            if (
                q_rook is not None
                and get_name(q_rook) == "R"
                and not has_moved(q_rook)
                and is_white(q_rook) == get_white
                and all(s is None for s in q_squares)
            ):
                king_pos = self.white_king if get_white else self.black_king
                move = make_move("K", king_pos, (2, rank), False)
                moves.add(move)
            if (
                k_rook is not None
                and get_name(k_rook) == "R"
                and not has_moved(k_rook)
                and is_white(k_rook) == get_white
                and all(s is None for s in k_squares)
            ):
                king_pos = self.white_king if get_white else self.black_king
                move = make_move("K", king_pos, (6, rank), False)
                moves.add(move)

        # get en passant moves
        if self.en_passant_pawn is not None:
            if get_white:
                pawn_positions = [
                    pos
                    for pos, pce in self.white_pieces.items()
                    if get_name(pce) == "P"
                ]
                rank_step = 1
            else:
                pawn_positions = [
                    pos
                    for pos, pce in self.black_pieces.items()
                    if get_name(pce) == "P"
                ]
                rank_step = -1

            ep_pawn_pos = self.en_passant_pawn
            ep_attackers = [
                (ep_pawn_pos[0] - 1, ep_pawn_pos[1]),
                (ep_pawn_pos[0] + 1, ep_pawn_pos[1]),
            ]

            for pos in ep_attackers:
                final_pos = (ep_pawn_pos[0], pos[1] + rank_step)
                if pos in pawn_positions and _is_in_bounds(final_pos):
                    pawn = self._get_square(pos)
                    assert pawn is not None, "Positions and board are not aligned."

                    move = make_move(
                        get_name(pawn),
                        pos,
                        final_pos,
                        True,
                        "P",
                    )
                    moves.add(move)

        return moves

    def _get_pawn_moves(self, pawn: Piece, position: Position) -> set[Move]:
        moves: set[Move] = set()
        file = position[0]
        rank = position[1]
        rank_step = 1 if is_white(pawn) else -1
        final_positions: list[Position] = []

        one_forward = (file, rank + rank_step)
        if _is_in_bounds(one_forward):
            square = self._get_square(one_forward)
            if square is None:
                final_positions.append(one_forward)

        two_forward = (file, rank + 2 * rank_step)
        if (
            _is_in_bounds(two_forward)
            and self._get_square(one_forward) is None
            and not has_moved(pawn)
        ):
            square = self._get_square(two_forward)
            if square is None:
                final_positions.append(two_forward)

        attack_left = (file - 1, rank + rank_step)
        if _is_in_bounds(attack_left):
            square = self._get_square(attack_left)
            if square is not None and is_white(square) != is_white(pawn):
                final_positions.append(attack_left)

        attack_right = (file + 1, rank + rank_step)
        if _is_in_bounds(attack_right):
            square = self._get_square(attack_right)
            if square is not None and is_white(square) != is_white(pawn):
                final_positions.append(attack_right)

        # check for promotion and add moves
        for final_pos in final_positions:
            square = self._get_square(final_pos)
            captured = get_name(square) if square is not None else None
            if final_pos[1] == 7 or final_pos[1] == 0:
                for promotion in ["Q", "B", "N", "R"]:
                    move = make_move(
                        get_name(pawn), position, final_pos, False, captured, promotion
                    )
                    moves.add(move)
            else:
                move = make_move(get_name(pawn), position, final_pos, False, captured)
                moves.add(move)

        return moves

    def _get_knight_moves(self, knight: Piece, position: Position) -> set[Move]:
        moves: set[Move] = set()

        knight_squares = self._get_knight_squares(position)
        for p in knight_squares:
            square = self._get_square(p)
            move = _move_or_capture_or_halt(knight, square, position, p)
            if move is not None:
                moves.add(move)

        return moves

    def _get_knight_squares(self, initial: Position) -> set[Position]:
        positions: set[Position] = set()

        for d in KNIGHT_DELTAS:
            position = self._add_delta(initial, d)
            if _is_in_bounds(position):
                positions.add(position)

        return positions

    def _get_king_moves(self, king: Piece, position: Position) -> set[Move]:
        moves: set[Move] = set()

        king_squares = self._get_king_squares(position)
        for p in king_squares:
            square = self._get_square(p)
            move = _move_or_capture_or_halt(king, square, position, p)
            if move is not None:
                moves.add(move)

        return moves

    def _get_king_squares(self, initial: Position) -> set[Position]:
        positions: set[Position] = set()

        for d in KING_DELTAS:
            position = self._add_delta(initial, d)
            if _is_in_bounds(position):
                positions.add(position)

        return positions

    def _get_rook_moves(self, rook: Piece, position: Position) -> set[Move]:
        moves: set[Move] = set()

        rook_squares = self._get_rook_squares(position)
        for p in rook_squares:
            square = self._get_square(p)
            move = _move_or_capture_or_halt(rook, square, position, p)
            if move is not None:
                moves.add(move)

        return moves

    def _get_rook_squares(self, position: Position) -> set[Position]:
        positions: set[Position] = set()

        for d in ROOK_DELTAS:
            positions.update(self._get_slide_squares(position, d))

        return positions

    def _get_bishop_moves(self, bishop: Piece, position: Position) -> set[Move]:
        moves: set[Move] = set()

        bishop_squares = self._get_bishop_squares(position)
        for p in bishop_squares:
            square = self._get_square(p)
            move = _move_or_capture_or_halt(bishop, square, position, p)
            if move is not None:
                moves.add(move)

        return moves

    def _get_bishop_squares(self, position: Position) -> set[Position]:
        positions: set[Position] = set()

        for d in BISHOP_DELTAS:
            positions.update(self._get_slide_squares(position, d))

        return positions

    def _get_queen_moves(self, queen: Piece, position: Position) -> set[Move]:
        moves: set[Move] = set()

        queen_squares = self._get_queen_squares(position)
        for p in queen_squares:
            square = self._get_square(p)
            move = _move_or_capture_or_halt(queen, square, position, p)
            if move is not None:
                moves.add(move)

        return moves

    def _get_queen_squares(self, position: Position) -> set[Position]:
        positions: set[Position] = set()

        for d in QUEEN_DELTAS:
            positions.update(self._get_slide_squares(position, d))

        return positions

    def _get_slide_squares(self, initial: Position, delta: Position) -> set[Position]:
        positions: set[Position] = set()
        position = self._add_delta(initial, delta)

        while _is_in_bounds(position):
            positions.add(position)
            if self._get_square(position) is not None:
                break
            position = self._add_delta(position, delta)

        return positions


def _is_in_bounds(position: Position) -> bool:
    return (0 <= position[0] <= 7) and (0 <= position[1] <= 7)


def _move_or_capture_or_halt(
    piece: Piece,
    square: Piece | None,
    initial: Position,
    final: Position,
) -> Move | None:
    if square is None:
        return make_move(get_name(piece), initial, final, False)
    if is_white(square) != is_white(piece):
        return make_move(get_name(piece), initial, final, False, get_name(square))
    return None
