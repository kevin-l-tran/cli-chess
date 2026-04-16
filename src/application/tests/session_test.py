from helpers import make, sq

from src.application import move_parser
from src.application import session, session_types
from src.engine import moves, game

Move = moves.Move


class FakeGame(game.Game):
    """
    Minimal game double for application-layer session tests.

    It exposes the two methods GameSession currently depends on:
    - get_moves()
    - make_move(move, draw_offered=...)
    """

    def __init__(
        self,
        *,
        initial_moves: set[Move],
        next_moves: set[Move] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._moves = set(initial_moves)
        self._next_moves = set(initial_moves if next_moves is None else next_moves)
        self._error = error
        self.make_move_calls: list[tuple[Move, bool]] = []

    def get_moves(self) -> set[Move]:
        return set(self._moves)

    def make_move(self, move: Move, draw_offered: bool) -> None:
        self.make_move_calls.append((move, draw_offered))

        if self._error is not None:
            raise self._error

        self._moves = set(self._next_moves)


def make_session(game: FakeGame) -> session.GameSession:
    config = session_types.SessionConfig(player_side="white")
    return session.GameSession(config=config, game=game)


def test_try_make_move_applies_move_clears_draft_and_refreshes_legal_moves() -> None:
    move = make("P", "e2", "e4")
    reply = make("P", "e7", "e5")
    fake_game = FakeGame(initial_moves={move}, next_moves={reply})
    game_session = make_session(fake_game)

    game_session._state.move_text = "Pe2-e4"
    game_session._state.parse_result = move_parser.parse("Pe2-e4", {move})
    game_session._state.last_error_message = "old error"

    result = game_session.try_make_move(move, offer_draw=True)

    assert fake_game.make_move_calls == [(move, True)]
    assert result == session.MoveAttemptResult(
        ok=True,
        status="applied",
        message=None,
    )

    assert game_session._state.last_move_from == sq("e2")
    assert game_session._state.last_move_to == sq("e4")
    assert game_session._state.last_error_message is None

    assert game_session._state.move_text == ""
    assert game_session._state.parse_result is not None
    assert game_session._state.parse_result.status == "empty"
    assert game_session._state.parse_result.normalized_text == ""

    assert game_session._legal_moves == {reply}


def test_try_make_move_illegal_failure_sets_feedback_and_preserves_existing_draft() -> (
    None
):
    move = make("P", "e2", "e4")
    parse_result = move_parser.parse("Pe2-e4", {move})
    fake_game = FakeGame(
        initial_moves={move},
        error=game.IllegalMoveError("illegal move"),
    )
    game_session = make_session(fake_game)

    game_session._state.move_text = "Pe2-e4"
    game_session._state.parse_result = parse_result
    game_session._state.last_move_from = sq("a2")
    game_session._state.last_move_to = sq("a4")

    result = game_session.try_make_move(move)

    assert fake_game.make_move_calls == [(move, False)]
    assert result == session.MoveAttemptResult(
        ok=False,
        status="illegal",
        message="Could not apply illegal move.",
    )

    assert game_session._state.last_error_message == "Could not apply illegal move."

    # Failure should not clear the user's in-progress draft.
    assert game_session._state.move_text == "Pe2-e4"
    assert game_session._state.parse_result == parse_result

    # Failure should not overwrite prior last-move highlights.
    assert game_session._state.last_move_from == sq("a2")
    assert game_session._state.last_move_to == sq("a4")

    # Cache remains unchanged on failure.
    assert game_session._legal_moves == {move}


def test_try_make_move_game_over_failure_returns_game_over_status() -> None:
    move = make("P", "e2", "e4")
    fake_game = FakeGame(
        initial_moves={move},
        error=game.GameConcludedError("1-0"),
    )
    game_session = make_session(fake_game)

    result = game_session.try_make_move(move)

    assert fake_game.make_move_calls == [(move, False)]
    assert result == session.MoveAttemptResult(
        ok=False,
        status="game_over",
        message="Game has concluded.",
    )
    assert game_session._state.last_error_message == "Game has concluded."


def test_try_make_move_unexpected_error_returns_generic_result_message() -> None:
    move = make("P", "e2", "e4")
    parse_result = move_parser.parse("Pe2-e4", {move})
    fake_game = FakeGame(
        initial_moves={move},
        error=RuntimeError("boom"),
    )
    game_session = make_session(fake_game)

    game_session._state.move_text = "Pe2-e4"
    game_session._state.parse_result = parse_result

    result = game_session.try_make_move(move)

    assert fake_game.make_move_calls == [(move, False)]
    assert result == session.MoveAttemptResult(
        ok=False,
        status="error",
        message="Could not apply move.",
    )

    # This pins the current implementation:
    # returned message is generic, but session feedback stores the exception text.
    assert game_session._state.last_error_message == "Could not apply move."

    # Unexpected failure also preserves the user's draft.
    assert game_session._state.move_text == "Pe2-e4"
    assert game_session._state.parse_result == parse_result
