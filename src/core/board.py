from typing import Callable, Self
from core.moves import (
    Move,
    get_final_position,
    get_initial_position,
    get_promotion,
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


def make_piece(name: str, is_white: bool, has_moved: bool, can_ep: bool) -> Piece:
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


QUEEN_DELTAS = [
    (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)
]
BISHOP_DELTAS = [
    (1, 1), (-1, -1), (-1, 1), (1, -1)
]
ROOK_DELTAS = [
    (0, 1), (1, 0), (-1, 0), (0, -1)
]
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
        # clear ep status
        if get_white:
            pawn_positions = [
                pos for pos, pwn in self.white_pieces.items() if get_name(pwn) == "P"
            ]
        else:
            pawn_positions = [
                pos for pos, pwn in self.black_pieces.items() if get_name(pwn) == "P"
            ]

        for pos in pawn_positions:
            pawn = self.board[pos[0]][pos[1]]
            assert pawn is not None, "Pieces and board are not aligned."

            new_pawn = make_piece("P", is_white(pawn), has_moved(pawn), False)
            self.board[pos[0]][pos[1]] = new_pawn
            if get_white:
                self.white_pieces[pos] = new_pawn
            else:
                self.black_pieces[pos] = new_pawn

        # generate psuedo moves
        moves = self._get_psuedo_moves(get_white)

        # remove invalid castle moves
        rank = 0 if get_white else 7
        k_castle_squares = [(rank, 4), (rank, 5), (rank, 6)]
        q_castle_squares = [(rank, 4), (rank, 3), (rank, 2)]

        attacked_squares = self._get_squares_attacked_by(not get_white)
        if attacked_squares.intersection(k_castle_squares):
            castle_move = "0-0" + ("T" if get_white else "F")
            moves.discard(castle_move)
        if attacked_squares.intersection(q_castle_squares):
            castle_move = "0-0-0" + ("T" if get_white else "F")
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
        if move == "0-0T" or move == "0-0F":
            white = move[3] == "T"
            rank = 0 if white else 7

            king = self.board[rank][4]
            rook = self.board[rank][7]
            updated_king = make_piece("K", white, True, False)
            updated_rook = make_piece("R", white, True, False)

            assert king is not None, "Castle targets nonexistent king."
            assert rook is not None, "Castle targets nonexistent rook."

            def apply(self: Self) -> None:
                self._make_move(updated_king, (rank, 4), (rank, 6))
                self._make_move(updated_rook, (rank, 7), (rank, 5))

            def undo(self: Self) -> None:
                self._undo_move(king, (rank, 4), (rank, 6))
                self._undo_move(rook, (rank, 7), (rank, 5))

        elif move == "0-0-0T" or move == "0-0-0F":
            white = move[5] == "T"
            rank = 0 if white else 7

            king = self.board[rank][4]
            rook = self.board[rank][0]
            updated_king = make_piece("K", white, True, False)
            updated_rook = make_piece("R", white, True, False)

            assert king is not None, "Castle targets nonexistent king."
            assert rook is not None, "Castle targets nonexistent rook."

            def apply(self: Self) -> None:
                self._make_move(updated_king, (rank, 4), (rank, 2))
                self._make_move(updated_rook, (rank, 0), (rank, 3))

            def undo(self: Self) -> None:
                self._undo_move(king, (rank, 4), (rank, 2))
                self._undo_move(rook, (rank, 0), (rank, 3))

        elif is_en_passant(move):
            initial_position = get_initial_position(move)
            final_position = get_final_position(move)
            initial_pawn = self.board[initial_position[0]][initial_position[1]]
            captured_pawn = self.board[initial_position[0]][final_position[1]]

            assert initial_pawn is not None, "En passant targets a nonexistent pawn."
            assert captured_pawn is not None, "En passant captures a nonexistent pawn."

            updated_pawn = make_piece(
                get_name(initial_pawn), is_white(initial_pawn), True, False
            )

            def apply(self: Self) -> None:
                # move capturing pawn
                self._make_move(updated_pawn, initial_position, final_position)

                # remove captured pawn
                self.board[initial_position[0]][final_position[1]] = None
                if is_white(initial_pawn):
                    self.black_pieces.pop(
                        (initial_position[0], final_position[1]))
                else:
                    self.white_pieces.pop(
                        (initial_position[0], final_position[1]))

            def undo(self: Self) -> None:
                # move capturing pawn
                self._undo_move(initial_pawn, initial_position, final_position)

                # add captured pawn
                self.board[initial_position[0]
                           ][final_position[1]] = captured_pawn
                if is_white(initial_pawn):
                    self.black_pieces[(initial_position[0], final_position[1])] = (
                        captured_pawn
                    )
                else:
                    self.white_pieces[(initial_position[0], final_position[1])] = (
                        captured_pawn
                    )

        else:
            initial_position = get_initial_position(move)
            final_position = get_final_position(move)
            initial_piece = self.board[initial_position[0]
                                       ][initial_position[1]]
            captured_piece = self.board[final_position[0]][final_position[1]]

            assert initial_piece is not None, "Move targets a nonexistent piece."

            name = get_promotion(move) or get_name(initial_piece)
            white = is_white(initial_piece)
            moved = has_moved(initial_piece)
            ep = (
                name == "P"
                and not moved
                and abs(final_position[0] - initial_position[0]) == 2
            )
            updated_piece = make_piece(name, white, True, ep)

            def apply(self: Self) -> None:
                self._make_move(
                    updated_piece, initial_position, final_position)

            def undo(self: Self) -> None:
                self._undo_move(
                    initial_piece, initial_position, final_position, captured_piece
                )

        return apply, undo

    def is_checked(self, check_white: bool) -> bool:
        if check_white:
            king_pos = self.white_king
        else:
            king_pos = self.black_king

        attacked = self._get_squares_attacked_by(not check_white)
        return king_pos in attacked

    def _get_squares_attacked_by(self, white: bool) -> set[tuple[int, int]]:
        if white:
            pieces = self.white_pieces
        else:
            pieces = self.black_pieces

        positions: set[tuple[int, int]] = set()
        for pos, pce in pieces.items():
            name = get_name(pce)
            if name == "K":
                king_positions = self._get_king_squares(pos)
                positions.update(king_positions)
            elif name == "Q":
                queen_positions = self._get_queen_squares(pos)
                positions.update(queen_positions)
            elif name == "B":
                bishop_positions = self._get_bishop_squares(pos)
                positions.update(bishop_positions)
            elif name == "N":
                knight_positions = self._get_knight_squares(pos)
                positions.update(knight_positions)
            elif name == "R":
                rook_positions = self._get_rook_squares(pos)
                positions.update(rook_positions)
            else:  # pawns attack diagonally
                white_multiplier = 1 if white else -1
                pawn_positions = [(pos[0] + 1 * white_multiplier, pos[1] + 1),
                                  (pos[0] + 1 * white_multiplier, pos[1] - 1)]
                for p in pawn_positions:
                    if _is_in_bounds(p):
                        positions.add(p)

        return positions

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

    def _make_move(
        self,
        updated_piece: Piece,
        initial: tuple[int, int],
        final: tuple[int, int],
    ) -> None:
        # move updated piece
        self.board[initial[0]][initial[1]] = None
        self.board[final[0]][final[1]] = updated_piece

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

    def _undo_move(
        self,
        original_piece: Piece,
        initial: tuple[int, int],
        final: tuple[int, int],
        captured_piece: Piece | None = None,
    ) -> None:
        # revert moved piece
        self.board[initial[0]][initial[1]] = original_piece

        # add back captured piece
        self.board[final[0]][final[1]] = captured_piece

        # update dicts:
        if is_white(original_piece):
            self.white_pieces.pop((final[0], final[1]), None)
            self.white_pieces[(initial[0], initial[1])] = original_piece
            if captured_piece:
                self.black_pieces[(final[0], final[1])] = captured_piece
            if get_name(original_piece) == "K":
                self.white_king = (initial[0], initial[1])
        else:
            self.black_pieces.pop((final[0], final[1]), None)
            self.black_pieces[(initial[0], initial[1])] = original_piece
            if captured_piece:
                self.white_pieces[(final[0], final[1])] = captured_piece
            if get_name(original_piece) == "K":
                self.black_king = (initial[0], initial[1])

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
                move = "0-0-0"
                move += "T" if get_white else "F"
                moves.add(move)
            if (
                k_rook is not None
                and get_name(k_rook) == "R"
                and not has_moved(k_rook)
                and is_white(k_rook) == get_white
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
        final_positions: list[tuple[int, int]] = []

        # foward move
        if _is_in_bounds((rank + 1 * white_multiplier, file)):
            square = self.board[rank + 1 * white_multiplier][file]
            if square is None:
                final_positions.append((rank + 1 * white_multiplier, file))

        # second forward move
        if (
            _is_in_bounds((rank + 2 * white_multiplier, file))
            and self.board[rank + 1 * white_multiplier][file] is None
            and not has_moved(pawn)
        ):
            square = self.board[rank + 2 * white_multiplier][file]
            if square is None:
                final_positions.append((rank + 2 * white_multiplier, file))

        # diagonal attacks
        if _is_in_bounds((rank + 1 * white_multiplier, file - 1)):
            square = self.board[rank + 1 * white_multiplier][file - 1]
            if square is not None and is_white(square) != is_white(pawn):
                final_positions.append((rank + 1 * white_multiplier, file - 1))

        if _is_in_bounds((rank + 1 * white_multiplier, file + 1)):
            square = self.board[rank + 1 * white_multiplier][file + 1]
            if square is not None and is_white(square) != is_white(pawn):
                final_positions.append((rank + 1 * white_multiplier, file + 1))

        # check for promotion and add moves
        for final_pos in final_positions:
            square = self.board[final_pos[0]][final_pos[1]]
            captured = get_name(square) if square is not None else None
            if final_pos[0] == 7 or final_pos[0] == 0:
                for promotion in ["Q", "B", "N", "R"]:
                    move = make_move(
                        get_name(
                            pawn), position, final_pos, False, captured, promotion
                    )
                    moves.add(move)
            else:
                move = make_move(get_name(pawn), position,
                                 final_pos, False, captured)
                moves.add(move)

        return moves

    def _get_knight_moves(self, knight: Piece, position: tuple[int, int]) -> set[Move]:
        moves: set[Move] = set()
        
        knight_squares = self._get_knight_squares(position)
        for p in knight_squares:
            square = self.board[p[0]][p[1]]
            move = _move_or_capture_or_halt(knight, square, position, p)
            if move is not None:
                moves.add(move)

        return moves

    def _get_knight_squares(self, initial: tuple[int, int]) -> set[tuple[int, int]]:
        positions: set[tuple[int, int]] = set()

        for d in KNIGHT_DELTAS:
            position = (initial[0] + d[0], initial[1] + d[1])
            if _is_in_bounds(position):
                positions.add(position)

        return positions

    def _get_king_moves(self, king: Piece, position: tuple[int, int]) -> set[Move]:
        moves: set[Move] = set()

        king_squares = self._get_king_squares(position)
        for p in king_squares:
            square = self.board[p[0]][p[1]]
            move = _move_or_capture_or_halt(king, square, position, p)
            if move is not None:
                moves.add(move)

        return moves

    def _get_king_squares(self, initial: tuple[int, int]) -> set[tuple[int, int]]:
        positions: set[tuple[int, int]] = set()

        for d in KING_DELTAS:
            position = (initial[0] + d[0], initial[1] + d[1])
            if _is_in_bounds(position):
                positions.add(position)

        return positions
    
    def _get_rook_moves(self, rook: Piece, position: tuple[int, int]) -> set[Move]:
        moves: set[Move] = set()
        
        rook_squares = self._get_rook_squares(position)
        for p in rook_squares:
            square = self.board[p[0]][p[1]]
            move = _move_or_capture_or_halt(rook, square, position, p)
            if move is not None:
                moves.add(move)

        return moves

    def _get_rook_squares(self, position: tuple[int, int]) -> set[tuple[int, int]]:
        positions: set[tuple[int, int]] = set()
        
        for d in ROOK_DELTAS:
            positions.update(self._get_slide_squares(position, d))

        return positions

    def _get_bishop_moves(self, bishop: Piece, position: tuple[int, int]) -> set[Move]:
        moves: set[Move] = set()
        
        bishop_squares = self._get_bishop_squares(position)
        for p in bishop_squares:
            square = self.board[p[0]][p[1]]
            move = _move_or_capture_or_halt(bishop, square, position, p)
            if move is not None:
                moves.add(move)
                
        return moves

    def _get_bishop_squares(self, position: tuple[int, int]) -> set[tuple[int, int]]:
        positions: set[tuple[int, int]] = set()
        
        for d in BISHOP_DELTAS:
            positions.update(self._get_slide_squares(position, d))

        return positions
    
    def _get_queen_moves(self, queen: Piece, position: tuple[int, int]) -> set[Move]:
        moves: set[Move] = set()
        
        queen_squares = self._get_queen_squares(position)
        for p in queen_squares:
            square = self.board[p[0]][p[1]]
            move = _move_or_capture_or_halt(queen, square, position, p)
            if move is not None:
                moves.add(move)

        return moves
    
    def _get_queen_squares(self, position: tuple[int, int]) -> set[tuple[int, int]]:
        positions: set[tuple[int, int]] = set()
        
        for d in QUEEN_DELTAS:
            positions.update(self._get_slide_squares(position, d))

        return positions

    def _get_slide_squares(self, initial: tuple[int, int], delta: tuple[int, int]) -> set[tuple[int, int]]:
        positions: set[tuple[int, int]] = set()
        position = (initial[0] + delta[0], initial[1] + delta[1])

        while _is_in_bounds(position):
            positions.add(position)
            if self.board[position[0]][position[1]] is not None:
                break
            position = (position[0] + delta[0], position[1] + delta[1])

        return positions


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
