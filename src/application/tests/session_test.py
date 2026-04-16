from src.application import move_parser
from src.application import session as session_module
from src.engine import moves, game

Move = moves.Move


def sq(name: str) -> tuple[int, int]:
    """Convert algebraic square like 'e4' to engine coordinates (file, rank)."""
    assert len(name) == 2
    file = ord(name[0]) - ord("a")
    rank = int(name[1]) - 1
    return (file, rank)


def make(
    piece: str,
    start: str,
    end: str,
    *,
    capture: str | None = None,
    en_passant: bool = False,
    promotion: str | None = None,
) -> Move:
    return moves.make_move(
        piece_name=piece,
        initial_position=sq(start),
        final_position=sq(end),
        capture_name=capture,
        en_passant=en_passant,
        promotion=promotion,
    )


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


def make_session(game: FakeGame) -> session_module.GameSession:
    config = session_module.SessionConfig(player_side="white")
    return session_module.GameSession(config=config, game=game)


def test_try_make_move_applies_move_clears_draft_and_refreshes_legal_moves() -> None:
    move = make("P", "e2", "e4")
    reply = make("P", "e7", "e5")
    fake_game = FakeGame(initial_moves={move}, next_moves={reply})
    session = make_session(fake_game)

    session._state.move_text = "Pe2-e4"
    session._state.parse_result = move_parser.parse("Pe2-e4", {move})
    session._state.last_error_message = "old error"

    result = session.try_make_move(move, offer_draw=True)

    assert fake_game.make_move_calls == [(move, True)]
    assert result == session_module.MoveAttemptResult(
        ok=True,
        status="applied",
        message=None,
    )

    assert session._state.last_move_from == sq("e2")
    assert session._state.last_move_to == sq("e4")
    assert session._state.last_error_message is None

    assert session._state.move_text == ""
    assert session._state.parse_result is not None
    assert session._state.parse_result.status == "empty"
    assert session._state.parse_result.normalized_text == ""

    assert session._legal_moves == {reply}


def test_try_make_move_illegal_failure_sets_feedback_and_preserves_existing_draft() -> None:
    move = make("P", "e2", "e4")
    parse_result = move_parser.parse("Pe2-e4", {move})
    fake_game = FakeGame(
        initial_moves={move},
        error=session_module.IllegalMoveError("illegal move"),
    )
    session = make_session(fake_game)

    session._state.move_text = "Pe2-e4"
    session._state.parse_result = parse_result
    session._state.last_move_from = sq("a2")
    session._state.last_move_to = sq("a4")

    result = session.try_make_move(move)

    assert fake_game.make_move_calls == [(move, False)]
    assert result == session_module.MoveAttemptResult(
        ok=False,
        status="illegal",
        message="illegal move",
    )

    assert session._state.last_error_message == "illegal move"

    # Failure should not clear the user's in-progress draft.
    assert session._state.move_text == "Pe2-e4"
    assert session._state.parse_result == parse_result

    # Failure should not overwrite prior last-move highlights.
    assert session._state.last_move_from == sq("a2")
    assert session._state.last_move_to == sq("a4")

    # Cache remains unchanged on failure.
    assert session._legal_moves == {move}


def test_try_make_move_game_over_failure_returns_game_over_status() -> None:
    move = make("P", "e2", "e4")
    fake_game = FakeGame(
        initial_moves={move},
        error=session_module.GameConcludedError("1-0"),
    )
    session = make_session(fake_game)

    result = session.try_make_move(move)

    assert fake_game.make_move_calls == [(move, False)]
    assert result == session_module.MoveAttemptResult(
        ok=False,
        status="game_over",
        message="1-0",
    )
    assert session._state.last_error_message == "1-0"


def test_try_make_move_unexpected_error_returns_generic_result_message() -> None:
    move = make("P", "e2", "e4")
    parse_result = move_parser.parse("Pe2-e4", {move})
    fake_game = FakeGame(
        initial_moves={move},
        error=RuntimeError("boom"),
    )
    session = make_session(fake_game)

    session._state.move_text = "Pe2-e4"
    session._state.parse_result = parse_result

    result = session.try_make_move(move)

    assert fake_game.make_move_calls == [(move, False)]
    assert result == session_module.MoveAttemptResult(
        ok=False,
        status="error",
        message="Could not apply move.",
    )

    # This pins the current implementation:
    # returned message is generic, but session feedback stores the exception text.
    assert session._state.last_error_message == "Unexpected error: boom"

    # Unexpected failure also preserves the user's draft.
    assert session._state.move_text == "Pe2-e4"
    assert session._state.parse_result == parse_result