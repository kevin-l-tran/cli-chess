from typing import Any

import pytest

from src.engine.board import Board, get_name, has_moved, is_white, make_piece
from src.engine.moves import make_move


def perft(depth: int, board: Board, is_white_turn: bool) -> int:
    if depth < 1:
        return 0

    moves = board.get_moves(is_white_turn)

    if depth == 1:
        return len(moves)

    count = 0
    for move in moves:
        commands = board.get_move_command(move)
        commands[0](board)  # apply
        count += perft(depth - 1, board, not is_white_turn)
        commands[1](board)  # undo

    return count


def empty_board() -> Board:
    board = Board()
    board.board = [[None for _ in range(8)] for _ in range(8)]
    board.white_pieces.clear()
    board.black_pieces.clear()
    board.en_passant_pawn = None
    board._add_piece(make_piece("K", True, False), (4, 0))
    board._add_piece(make_piece("K", False, False), (4, 7))
    return board


def snapshot(board: Board) -> dict[str, Any]:
    return {
        "board": tuple(tuple(row) for row in board.board),
        "white_pieces": dict(board.white_pieces),
        "black_pieces": dict(board.black_pieces),
        "white_king": board.white_king,
        "black_king": board.black_king,
        "en_passant_pawn": board.en_passant_pawn,
    }


def assert_board_consistent(board: Board) -> None:
    seen_white: dict[tuple[int, int], str] = {}
    seen_black: dict[tuple[int, int], str] = {}

    for rank in range(8):
        for file in range(8):
            position = (file, rank)
            piece = board.piece_at(position)
            if piece is None:
                assert position not in board.white_pieces
                assert position not in board.black_pieces
            elif is_white(piece):
                assert board.white_pieces[position] == piece
                assert position not in board.black_pieces
                seen_white[position] = piece
            else:
                assert board.black_pieces[position] == piece
                assert position not in board.white_pieces
                seen_black[position] = piece

    assert board.white_pieces == seen_white
    assert board.black_pieces == seen_black
    assert board.piece_at(board.white_king) is not None
    assert board.piece_at(board.black_king) is not None
    assert get_name(board.piece_at(board.white_king)) == "K"  # type: ignore[arg-type]
    assert get_name(board.piece_at(board.black_king)) == "K"  # type: ignore[arg-type]
    assert is_white(board.piece_at(board.white_king))  # type: ignore[arg-type]
    assert not is_white(board.piece_at(board.black_king))  # type: ignore[arg-type]


def apply_move(board: Board, move: str) -> None:
    apply, _ = board.get_move_command(move)
    apply(board)


def test_perft_depth1() -> None:
    board = Board()
    assert perft(1, board, True) == 20


def test_perft_depth2() -> None:
    board = Board()
    assert perft(2, board, True) == 400


def test_perft_depth3() -> None:
    board = Board()
    assert perft(3, board, True) == 8902


def test_perft_depth4() -> None:
    board = Board()
    assert perft(4, board, True) == 197281


@pytest.mark.skip(reason="manual run only")
def test_perft_depth5() -> None:
    board = Board()
    assert perft(5, board, True) == 4865609


def test_initial_position_has_expected_piece_maps_and_kings() -> None:
    board = Board()

    assert len(board.white_pieces) == 16
    assert len(board.black_pieces) == 16
    assert board.king_position(True) == (4, 0)
    assert board.king_position(False) == (4, 7)
    assert board.piece_at((0, 0)) == make_piece("R", True, False)
    assert board.piece_at((3, 0)) == make_piece("Q", True, False)
    assert board.piece_at((4, 0)) == make_piece("K", True, False)
    assert board.piece_at((0, 7)) == make_piece("R", False, False)
    assert board.piece_at((3, 7)) == make_piece("Q", False, False)
    assert board.piece_at((4, 7)) == make_piece("K", False, False)
    assert board.en_passant_pawn is None
    assert all(not has_moved(piece) for piece in board.white_pieces.values())
    assert all(not has_moved(piece) for piece in board.black_pieces.values())
    assert_board_consistent(board)


def test_initial_position_legal_moves_are_only_pawns_and_knights() -> None:
    board = Board()
    moves = board.get_moves(True)

    assert len(moves) == 20
    assert make_move("P", (4, 1), (4, 2), False) in moves
    assert make_move("P", (4, 1), (4, 3), False) in moves
    assert make_move("N", (1, 0), (0, 2), False) in moves
    assert make_move("N", (1, 0), (2, 2), False) in moves
    assert make_move("B", (2, 0), (3, 1), False) not in moves
    assert make_move("Q", (3, 0), (3, 1), False) not in moves


def test_quiet_double_pawn_move_sets_en_passant_and_undo_restores_exact_state() -> None:
    board = Board()
    before = snapshot(board)
    move = make_move("P", (4, 1), (4, 3), False)
    apply, undo = board.get_move_command(move)

    apply(board)

    assert board.piece_at((4, 1)) is None
    assert board.piece_at((4, 3)) == make_piece("P", True, True)
    assert board.en_passant_pawn == (4, 3)
    assert_board_consistent(board)

    undo(board)

    assert snapshot(board) == before
    assert_board_consistent(board)


def test_capture_move_updates_piece_maps_and_undo_restores_exact_state() -> None:
    board = empty_board()
    board._add_piece(make_piece("N", True, False), (1, 0))
    board._add_piece(make_piece("P", False, False), (2, 2))
    before = snapshot(board)
    move = make_move("N", (1, 0), (2, 2), False, "P")
    apply, undo = board.get_move_command(move)

    apply(board)

    assert board.piece_at((1, 0)) is None
    assert board.piece_at((2, 2)) == make_piece("N", True, True)
    assert (2, 2) in board.white_pieces
    assert (2, 2) not in board.black_pieces
    assert_board_consistent(board)

    undo(board)

    assert snapshot(board) == before
    assert_board_consistent(board)


def test_pawn_cannot_move_forward_when_blocked_but_can_capture_diagonally() -> None:
    board = empty_board()
    board._add_piece(make_piece("P", True, False), (4, 4))
    board._add_piece(make_piece("N", True, False), (4, 5))
    board._add_piece(make_piece("B", False, False), (3, 5))
    board._add_piece(make_piece("R", False, False), (5, 5))

    moves = board.get_moves(True)

    assert make_move("P", (4, 4), (4, 5), False) not in moves
    assert make_move("P", (4, 4), (3, 5), False, "B") in moves
    assert make_move("P", (4, 4), (5, 5), False, "R") in moves


def test_rook_sliding_moves_stop_after_first_blocker_or_capture() -> None:
    board = empty_board()
    board._add_piece(make_piece("R", True, False), (3, 3))
    board._add_piece(make_piece("P", True, False), (3, 5))
    board._add_piece(make_piece("B", False, False), (6, 3))

    moves = board.get_moves(True)

    assert make_move("R", (3, 3), (3, 4), False) in moves
    assert make_move("R", (3, 3), (3, 5), False) not in moves
    assert make_move("R", (3, 3), (6, 3), False, "B") in moves
    assert make_move("R", (3, 3), (7, 3), False) not in moves


def test_check_detection_uses_attacked_squares() -> None:
    board = empty_board()
    board._add_piece(make_piece("R", False, False), (4, 6))

    assert board.is_checked(True)
    assert not board.is_checked(False)


def test_legal_moves_filter_out_king_moves_that_remain_in_check() -> None:
    board = empty_board()
    board._add_piece(make_piece("R", False, False), (4, 6))

    moves = board.get_moves(True)

    assert make_move("K", (4, 0), (4, 1), False) not in moves
    assert make_move("K", (4, 0), (3, 0), False) in moves
    assert make_move("K", (4, 0), (5, 0), False) in moves


def test_pinned_piece_cannot_move_if_it_exposes_king_to_check() -> None:
    board = empty_board()
    board._add_piece(make_piece("R", True, False), (4, 1))
    board._add_piece(make_piece("R", False, False), (4, 6))

    moves = board.get_moves(True)

    assert make_move("R", (4, 1), (3, 1), False) not in moves
    assert make_move("R", (4, 1), (4, 2), False) in moves
    assert make_move("R", (4, 1), (4, 6), False, "R") in moves


def test_kingside_and_queenside_castling_are_generated_and_undoable() -> None:
    board = empty_board()
    board._add_piece(make_piece("R", True, False), (0, 0))
    board._add_piece(make_piece("R", True, False), (7, 0))
    before = snapshot(board)

    moves = board.get_moves(True)

    assert make_move("K", (4, 0), (6, 0), False) in moves
    assert make_move("K", (4, 0), (2, 0), False) in moves

    apply, undo = board.get_move_command(make_move("K", (4, 0), (6, 0), False))
    apply(board)

    assert board.piece_at((4, 0)) is None
    assert board.piece_at((7, 0)) is None
    assert board.piece_at((6, 0)) == make_piece("K", True, True)
    assert board.piece_at((5, 0)) == make_piece("R", True, True)
    assert board.king_position(True) == (6, 0)
    assert_board_consistent(board)

    undo(board)

    assert snapshot(board) == before
    assert_board_consistent(board)


def test_castling_through_attacked_square_is_not_legal() -> None:
    board = empty_board()
    board._add_piece(make_piece("R", True, False), (7, 0))
    board._add_piece(make_piece("B", False, False), (2, 3))  # attacks f1

    moves = board.get_moves(True)

    assert make_move("K", (4, 0), (6, 0), False) not in moves


def test_en_passant_is_generated_applied_and_undone() -> None:
    board = empty_board()
    board._add_piece(make_piece("P", True, True), (4, 4))
    board._add_piece(make_piece("P", False, True), (3, 4))
    board.en_passant_pawn = (3, 4)
    before = snapshot(board)
    move = make_move("P", (4, 4), (3, 5), True, "P")

    assert move in board.get_moves(True)

    apply, undo = board.get_move_command(move)
    apply(board)

    assert board.piece_at((4, 4)) is None
    assert board.piece_at((3, 4)) is None
    assert board.piece_at((3, 5)) == make_piece("P", True, True)
    assert board.en_passant_pawn is None
    assert_board_consistent(board)

    undo(board)

    assert snapshot(board) == before
    assert_board_consistent(board)


@pytest.mark.parametrize("promotion", ["Q", "B", "N", "R"])
def test_pawn_promotion_moves_are_generated(promotion: str) -> None:
    board = empty_board()
    board._add_piece(make_piece("P", True, True), (0, 6))

    assert make_move("P", (0, 6), (0, 7), False, None, promotion) in board.get_moves(
        True
    )


def test_pawn_promotion_apply_and_undo_restore_exact_state() -> None:
    board = empty_board()
    board._add_piece(make_piece("P", True, True), (0, 6))
    before = snapshot(board)
    move = make_move("P", (0, 6), (0, 7), False, None, "Q")
    apply, undo = board.get_move_command(move)

    apply(board)

    assert board.piece_at((0, 6)) is None
    assert board.piece_at((0, 7)) == make_piece("Q", True, True)
    assert_board_consistent(board)

    undo(board)

    assert snapshot(board) == before
    assert_board_consistent(board)


def test_capture_promotion_moves_include_captured_piece_name() -> None:
    board = empty_board()
    board._add_piece(make_piece("P", True, True), (0, 6))
    board._add_piece(make_piece("R", False, False), (1, 7))

    moves = board.get_moves(True)

    assert make_move("P", (0, 6), (1, 7), False, "R", "Q") in moves
    assert make_move("P", (0, 6), (1, 7), False, "R", "N") in moves


def test_get_moves_does_not_mutate_board_state() -> None:
    board = Board()
    before = snapshot(board)

    _ = board.get_moves(True)
    _ = board.get_moves(False)

    assert snapshot(board) == before
    assert_board_consistent(board)
