import pytest

from src.engine.board import Board, Position, make_piece
from src.engine.evaluations import (
    is_check,
    is_checkmate,
    is_draw,
    is_draw_offer,
    make_evaluation,
)
from src.engine.game import (
    Game,
    GameConcludedError,
    IllegalMoveError,
    NoDrawOfferError,
    NoMoveToUndoError,
)
from src.engine.moves import Move, make_move


def snapshot(
    game: Game,
) -> tuple[
    str,
    bool,
    tuple[tuple[str | None, ...], ...],
    tuple[tuple[Position, str], ...],
    tuple[tuple[Position, str], ...],
    tuple[tuple[str, int], ...],
    int,
    int,
]:
    return (
        game.outcome,
        game.is_white_turn,
        tuple(tuple(rank) for rank in game.board.board),
        tuple(sorted(game.board.white_pieces.items())),
        tuple(sorted(game.board.black_pieces.items())),
        tuple(sorted(game.encountered_positions.items())),
        len(game.moves_list),
        len(game.commands_list),
    )


def move(
    piece: str,
    initial: Position,
    final: Position,
    capture: str | None = None,
    promotion: str | None = None,
) -> Move:
    return make_move(piece, initial, final, False, capture, promotion)


def play(
    game: Game,
    piece: str,
    initial: Position,
    final: Position,
    capture: str | None = None,
    promotion: str | None = None,
    *,
    offer_draw: bool = False,
) -> Move:
    played = move(piece, initial, final, capture, promotion)
    game.make_move(played, offer_draw)
    return played


def empty_board() -> Board:
    board = Board()
    board.board = [[None for _ in range(8)] for _ in range(8)]
    board.white_pieces = {}
    board.black_pieces = {}
    board.en_passant_pawn = None
    return board


def game_from_pieces(
    pieces: list[tuple[str, bool, Position]], *, white_turn: bool
) -> Game:
    game = Game()
    board = empty_board()
    for name, is_white, position in pieces:
        board._add_piece(make_piece(name, is_white, False), position)
    game.board = board
    game.is_white_turn = white_turn
    game.moves_list = []
    game.commands_list = []
    game.outcome = ""
    game.encountered_positions = {game._get_position_hash(): 1}
    return game


def test_new_game_tracks_initial_state_and_position() -> None:
    game = Game()

    assert game.is_white_turn is True
    assert game.outcome == ""
    assert game.moves_list == []
    assert game.commands_list == []
    assert game.encountered_positions == {game._get_position_hash(): 1}
    assert len(game.get_moves()) == 20


def test_make_move_applies_legal_move_records_evaluation_and_toggles_turn() -> None:
    game = Game()
    e2e4 = move("P", (4, 1), (4, 3))

    game.make_move(e2e4, False)

    assert game.is_white_turn is False
    assert game.board.piece_at((4, 1)) is None
    assert game.board.piece_at((4, 3)) == make_piece("P", True, True)
    assert game.board.en_passant_pawn == (4, 3)
    assert game.moves_list == [(e2e4, make_evaluation(False, False, False, False))]
    assert len(game.commands_list) == 1
    assert game.encountered_positions[game._get_position_hash()] == 1


def test_make_move_rejects_illegal_move_without_mutating_game() -> None:
    game = Game()
    before = snapshot(game)
    black_move_on_white_turn = move("P", (4, 6), (4, 4))

    with pytest.raises(IllegalMoveError):
        game.make_move(black_move_on_white_turn, False)

    assert snapshot(game) == before


def test_draw_offer_can_be_inspected_and_accepted_by_opponent() -> None:
    game = Game()

    play(game, "P", (4, 1), (4, 3), offer_draw=True)

    assert game.pending_draw_offer_side_is_white() is True
    _, evaluation = game.moves_list[-1]
    assert is_draw_offer(evaluation) is True

    game.accept_draw()

    assert game.outcome == "1/2-1/2"
    assert game.pending_draw_offer_side_is_white() is None


def test_draw_offer_expires_after_opponent_plays_without_offering_draw() -> None:
    game = Game()

    play(game, "P", (4, 1), (4, 3), offer_draw=True)
    play(game, "P", (4, 6), (4, 4))

    assert game.pending_draw_offer_side_is_white() is None
    with pytest.raises(NoDrawOfferError):
        game.accept_draw()


def test_accept_draw_requires_pending_offer() -> None:
    game = Game()

    with pytest.raises(NoDrawOfferError):
        game.accept_draw()

    play(game, "P", (4, 1), (4, 3))
    with pytest.raises(NoDrawOfferError):
        game.accept_draw()


def test_resign_sets_winner_and_blocks_more_moves() -> None:
    game = Game()
    game.resign()

    assert game.outcome == "0-1"
    with pytest.raises(GameConcludedError):
        game.make_move(move("P", (4, 1), (4, 3)), False)
    with pytest.raises(GameConcludedError):
        game.resign()
    with pytest.raises(GameConcludedError):
        game.accept_draw()


def test_undo_halfmove_restores_position_turn_history_and_outcome() -> None:
    game = Game()
    before = snapshot(game)
    play(game, "P", (4, 1), (4, 3))

    game.undo_halfmove()

    assert snapshot(game) == before


def test_undo_halfmove_requires_history() -> None:
    game = Game()

    with pytest.raises(NoMoveToUndoError):
        game.undo_halfmove()


def test_undo_fullmove_restores_two_halfmoves() -> None:
    game = Game()
    before = snapshot(game)

    play(game, "P", (4, 1), (4, 3))
    play(game, "P", (4, 6), (4, 4))
    game.undo_fullmove()

    assert snapshot(game) == before


def test_undo_fullmove_requires_two_halfmoves() -> None:
    game = Game()
    play(game, "P", (4, 1), (4, 3))

    with pytest.raises(NoMoveToUndoError):
        game.undo_fullmove()


def test_fools_mate_records_checkmate_and_concludes_game() -> None:
    game = Game()

    play(game, "P", (5, 1), (5, 2))  # f2-f3
    play(game, "P", (4, 6), (4, 4))  # e7-e5
    play(game, "P", (6, 1), (6, 3))  # g2-g4
    play(game, "Q", (3, 7), (7, 3))  # Qd8-h4#

    _, evaluation = game.moves_list[-1]
    assert is_check(evaluation) is True
    assert is_checkmate(evaluation) is True
    assert is_draw(evaluation) is False
    assert game.checked_king_position() == (4, 0)
    assert game.outcome == "0-1"

    with pytest.raises(GameConcludedError):
        game.make_move(move("P", (0, 1), (0, 2)), False)


def test_stalemate_records_draw_and_concludes_game() -> None:
    game = game_from_pieces(
        [
            ("K", True, (5, 6)),  # White king f7
            ("Q", True, (6, 4)),  # White queen g5
            ("K", False, (7, 7)),  # Black king h8
        ],
        white_turn=True,
    )

    play(game, "Q", (6, 4), (6, 5))  # Qg5-g6 stalemate

    _, evaluation = game.moves_list[-1]
    assert is_check(evaluation) is False
    assert is_checkmate(evaluation) is False
    assert is_draw(evaluation) is True
    assert game.outcome == "1/2-1/2"
    assert game.get_moves() == set()


def test_threefold_repetition_records_draw_on_third_repeated_position() -> None:
    game = Game()
    moves = [
        ("N", (6, 0), (5, 2)),  # Ng1-f3
        ("N", (6, 7), (5, 5)),  # Ng8-f6
        ("N", (5, 2), (6, 0)),  # Nf3-g1
        ("N", (5, 5), (6, 7)),  # Nf6-g8
        ("N", (6, 0), (5, 2)),  # Ng1-f3
        ("N", (6, 7), (5, 5)),  # Ng8-f6
        ("N", (5, 2), (6, 0)),  # Nf3-g1
        ("N", (5, 5), (6, 7)),  # Nf6-g8
        ("N", (6, 0), (5, 2)),  # Ng1-f3
        ("N", (6, 7), (5, 5)),  # Ng8-f6, repeats this position for the third time
    ]

    for index, args in enumerate(moves, start=1):
        play(game, *args)
        if index < len(moves):
            assert game.outcome == ""

    _, evaluation = game.moves_list[-1]
    assert is_draw(evaluation) is True
    assert game.outcome == "1/2-1/2"


def test_fifty_move_rule_draws_on_100th_stale_halfmove() -> None:
    game = game_from_pieces(
        [
            ("K", True, (4, 0)),
            ("N", True, (6, 0)),
            ("K", False, (4, 7)),
        ],
        white_turn=True,
    )
    stale_move = move("N", (0, 0), (1, 2))
    game.moves_list = [
        (stale_move, make_evaluation(False, False, False, False)) for _ in range(99)
    ]

    play(game, "N", (6, 0), (5, 2))

    _, evaluation = game.moves_list[-1]
    assert is_draw(evaluation) is True
    assert game.outcome == "1/2-1/2"
