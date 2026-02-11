import pytest

from src.core.board import Board


def perft(depth: int, board: Board, is_white_turn: bool) -> int:
    if depth < 1:
        return 0
    
    moves = board.get_moves(is_white_turn)

    if depth == 1:
        return len(moves)
    
    count = 0
    for move in moves:
        commands = board.get_move_command(move)
        commands[0](board) # apply
        count += perft(depth - 1, board, not is_white_turn)
        commands[1](board) # undo

    return count


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