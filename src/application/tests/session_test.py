from helpers import make, sq

from src.application import move_parser
from src.application import session, session_types
from src.application.move_parser import get_canonical
from src.engine import game, moves
from src.engine.board import Piece, make_piece

Move = moves.Move


class FakeBoard:
    def __init__(self, pieces: dict[tuple[int, int], Piece] | None = None) -> None:
        self._pieces = dict(pieces or {})

    def piece_at(self, position: tuple[int, int]) -> Piece | None:
        return self._pieces.get(position)


class FakeClock:
    def __init__(self, now_ms: int = 0) -> None:
        self.now_ms = now_ms

    def __call__(self) -> int:
        return self.now_ms

    def advance(self, delta_ms: int) -> None:
        self.now_ms += delta_ms


class FakeGame(game.Game):
    """
    Minimal game double for application-layer session tests.

    It exposes the engine methods GameSession currently depends on:
    - get_moves()
    - make_move(move, draw_offered=...)
    - undo_halfmove()
    - undo_fullmove()
    - resign()
    - checked_king_position()
    - board.piece_at(...)

    It also maintains a lightweight moves_list history so session refresh logic
    can derive last-move highlight state.
    """

    def __init__(
        self,
        *,
        initial_moves: set[Move],
        next_moves: set[Move] | None = None,
        error: Exception | None = None,
        history: list[tuple[Move, object | None]] | None = None,
        undo_halfmove_moves: set[Move] | None = None,
        undo_fullmove_moves: set[Move] | None = None,
        undo_halfmove_error: Exception | None = None,
        undo_fullmove_error: Exception | None = None,
        outcome: str = "",
        resign_error: Exception | None = None,
        resign_outcome: str = "0-1",
        is_white_turn: bool = True,
        next_is_white_turn: bool | None = None,
        undo_halfmove_is_white_turn: bool | None = None,
        undo_fullmove_is_white_turn: bool | None = None,
        checked_king_square: tuple[int, int] | None = None,
        board_pieces: dict[tuple[int, int], Piece] | None = None,
    ) -> None:
        self._moves = set(initial_moves)
        self._next_moves = set(initial_moves if next_moves is None else next_moves)
        self._error = error
        self._undo_halfmove_moves = set(
            self._moves if undo_halfmove_moves is None else undo_halfmove_moves
        )
        self._undo_fullmove_moves = set(
            self._moves if undo_fullmove_moves is None else undo_fullmove_moves
        )
        self._undo_halfmove_error = undo_halfmove_error
        self._undo_fullmove_error = undo_fullmove_error

        self.outcome = outcome
        self._resign_error = resign_error
        self._resign_outcome = resign_outcome
        self.is_white_turn = is_white_turn
        self._next_is_white_turn = next_is_white_turn
        self._undo_halfmove_is_white_turn = undo_halfmove_is_white_turn
        self._undo_fullmove_is_white_turn = undo_fullmove_is_white_turn
        self._checked_king_square = checked_king_square
        self.board = FakeBoard(board_pieces)

        self.moves_list: list[tuple[Move, object | None]] = list(history or [])  # type: ignore

        self.make_move_calls: list[tuple[Move, bool]] = []
        self.undo_halfmove_calls = 0
        self.undo_fullmove_calls = 0
        self.resign_calls = 0

    def get_moves(self) -> set[Move]:
        return set(self._moves)

    def make_move(self, move: Move, draw_offered: bool) -> None:
        self.make_move_calls.append((move, draw_offered))

        if self._error is not None:
            raise self._error

        self._moves = set(self._next_moves)
        self.moves_list.append((move, None))
        self.is_white_turn = (
            (not self.is_white_turn)
            if self._next_is_white_turn is None
            else self._next_is_white_turn
        )

    def undo_halfmove(self) -> None:
        self.undo_halfmove_calls += 1

        if self._undo_halfmove_error is not None:
            raise self._undo_halfmove_error

        if not self.moves_list:
            raise game.NoMoveToUndoError()

        self.moves_list.pop()
        self._moves = set(self._undo_halfmove_moves)
        self.is_white_turn = (
            (not self.is_white_turn)
            if self._undo_halfmove_is_white_turn is None
            else self._undo_halfmove_is_white_turn
        )

    def undo_fullmove(self) -> None:
        self.undo_fullmove_calls += 1

        if self._undo_fullmove_error is not None:
            raise self._undo_fullmove_error

        if len(self.moves_list) < 2:
            raise game.NoMoveToUndoError()

        self.moves_list.pop()
        self.moves_list.pop()
        self._moves = set(self._undo_fullmove_moves)
        if self._undo_fullmove_is_white_turn is not None:
            self.is_white_turn = self._undo_fullmove_is_white_turn

    def resign(self) -> None:
        self.resign_calls += 1

        if self._resign_error is not None:
            raise self._resign_error

        self.outcome = self._resign_outcome
        self._moves = set()

    def checked_king_position(self) -> tuple[int, int] | None:
        return self._checked_king_square


def make_session(
    fake_game: FakeGame,
    *,
    opponent: session_types.OpponentType = "local",
    time_control: session_types.TimeControl | None = None,
    time_source=None,
) -> session.GameSession:
    config = session_types.SessionConfig(
        player_side="white",
        opponent=opponent,
        time_control=time_control,
    )
    return session.GameSession(config=config, game=fake_game, time_source=time_source)


def assert_snapshot_flags(
    snapshot: session_types.Snapshot,
    *,
    is_game_over: bool,
    can_confirm_move: bool,
    can_undo_halfmove: bool,
    can_undo_fullmove: bool,
    can_resign: bool,
    is_promotion_pending: bool,
    is_player_checked: bool | None = None,
) -> None:
    assert snapshot.is_game_over is is_game_over
    assert snapshot.can_confirm_move is can_confirm_move
    assert snapshot.can_undo_halfmove is can_undo_halfmove
    assert snapshot.can_undo_fullmove is can_undo_fullmove
    assert snapshot.can_resign is can_resign
    assert snapshot.is_promotion_pending is is_promotion_pending
    if is_player_checked is not None:
        assert snapshot.is_player_checked is is_player_checked


def assert_timed_game(
    snapshot: session_types.Snapshot,
    *,
    white_remaining_ms: int,
    black_remaining_ms: int,
    active_side: session_types.PlayerSide | None,
    timeout_side: session_types.PlayerSide | None,
    increment_seconds: int,
    white_display_text: str,
    black_display_text: str,
    white_active: bool,
    black_active: bool,
    white_flagged: bool = False,
    black_flagged: bool = False,
) -> None:
    assert snapshot.timed_game is not None
    timed = snapshot.timed_game
    assert timed.white.remaining_ms == white_remaining_ms
    assert timed.black.remaining_ms == black_remaining_ms
    assert timed.white.display_text == white_display_text
    assert timed.black.display_text == black_display_text
    assert timed.white.is_active is white_active
    assert timed.black.is_active is black_active
    assert timed.white.is_flagged is white_flagged
    assert timed.black.is_flagged is black_flagged
    assert timed.active_side == active_side
    assert timed.timeout_side == timeout_side
    assert timed.increment_seconds == increment_seconds


def assert_outcome(
    snapshot: session_types.Snapshot,
    *,
    winner: session_types.PlayerSide | None,
    reason: session_types.TerminalReason,
    banner: str,
) -> None:
    assert snapshot.outcome is not None
    assert snapshot.outcome.winner == winner
    assert snapshot.outcome.reason == reason
    assert snapshot.outcome.banner == banner


def assert_feedback(
    feedback: session_types.FeedbackView | None,
    *,
    kind: session_types.FeedbackKind,
    text: str,
) -> None:
    assert feedback == session_types.FeedbackView(kind=kind, text=text)



class TestConfirmMoveDraft:
    def test_applies_resolved_move_sets_action_message_and_refreshes_legal_moves(
        self,
    ) -> None:
        move = make("P", "e2", "e4")
        reply = make("P", "e7", "e5")
        fake_game = FakeGame(initial_moves={move}, next_moves={reply})
        game_session = make_session(fake_game)

        game_session._state.move_text = "Pe2-e4"
        game_session._state.parse_result = move_parser.parse("Pe2-e4", {move})
        game_session._state.feedback = session_types.FeedbackView(kind="error", text="old error")

        result = game_session.confirm_move_draft(offer_draw=True)

        assert fake_game.make_move_calls == [(move, True)]
        assert result == session.MoveAttemptResult(
            ok=True,
            status="applied",
        )

        assert game_session._state.last_move_from == sq("e2")
        assert game_session._state.last_move_to == sq("e4")
        assert_feedback(game_session._state.feedback, kind="action", text="Played Pe2-e4.")

        assert game_session._state.move_text == ""
        assert game_session._state.parse_result.status == "empty"
        assert game_session._legal_moves == {reply}

        snapshot = game_session.snapshot()
        assert_feedback(snapshot.feedback, kind="action", text="Played Pe2-e4.")
        assert_snapshot_flags(
            snapshot,
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=True,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )

    def test_empty_failure_sets_error_and_clears_stale_action(self) -> None:
        move = make("P", "e2", "e4")
        fake_game = FakeGame(initial_moves={move})
        game_session = make_session(fake_game)

        game_session._state.move_text = ""
        game_session._state.parse_result = move_parser.parse("", {move})
        game_session._state.feedback = session_types.FeedbackView(kind="action", text="old action")
        game_session._state.last_move_from = sq("a2")
        game_session._state.last_move_to = sq("a4")

        result = game_session.confirm_move_draft()

        assert fake_game.make_move_calls == []
        assert result == session.MoveAttemptResult(
            ok=False,
            status="empty",
        )
        assert_feedback(game_session._state.feedback, kind="error", text="Enter a move first.")
        assert game_session._state.move_text == ""
        assert game_session._state.parse_result == move_parser.parse("", {move})
        assert game_session._state.last_move_from == sq("a2")
        assert game_session._state.last_move_to == sq("a4")
        assert game_session._legal_moves == {move}

        assert_snapshot_flags(
            game_session.snapshot(),
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )

    def test_ambiguous_failure_returns_stable_feedback_without_calling_engine(
        self,
    ) -> None:
        move_a = make("P", "e2", "e4")
        move_b = make("P", "e2", "e3")
        legal_moves = {move_a, move_b}
        parse_result = move_parser.parse("Pe", legal_moves)
        fake_game = FakeGame(initial_moves=legal_moves)
        game_session = make_session(fake_game)

        game_session._state.move_text = "Pe"
        game_session._state.parse_result = parse_result
        game_session._state.feedback = session_types.FeedbackView(kind="action", text="old action")
        game_session._state.last_move_from = sq("a2")
        game_session._state.last_move_to = sq("a4")

        result = game_session.confirm_move_draft()

        assert fake_game.make_move_calls == []
        assert result == session.MoveAttemptResult(
            ok=False,
            status="ambiguous",
        )
        assert_feedback(game_session._state.feedback, kind="error", text="Move is ambiguous.")
        assert game_session._state.move_text == "Pe"
        assert game_session._state.parse_result == parse_result
        assert game_session._state.last_move_from == sq("a2")
        assert game_session._state.last_move_to == sq("a4")
        assert game_session._legal_moves == legal_moves

        assert_snapshot_flags(
            game_session.snapshot(),
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )

    def test_no_match_failure_returns_stable_feedback_without_calling_engine(
        self,
    ) -> None:
        move = make("P", "e2", "e4")
        parse_result = move_parser.parse("zzzz", {move})
        fake_game = FakeGame(initial_moves={move})
        game_session = make_session(fake_game)

        game_session._state.move_text = "zzzz"
        game_session._state.parse_result = parse_result
        game_session._state.feedback = session_types.FeedbackView(kind="action", text="old action")
        game_session._state.last_move_from = sq("a2")
        game_session._state.last_move_to = sq("a4")

        result = game_session.confirm_move_draft()

        assert fake_game.make_move_calls == []
        assert result == session.MoveAttemptResult(
            ok=False,
            status="no_match",
        )
        assert_feedback(
            game_session._state.feedback,
            kind="error",
            text="No legal move matches the current draft.",
        )
        assert game_session._state.move_text == "zzzz"
        assert game_session._state.parse_result == parse_result
        assert game_session._state.last_move_from == sq("a2")
        assert game_session._state.last_move_to == sq("a4")
        assert game_session._legal_moves == {move}

    def test_illegal_failure_sets_feedback_and_preserves_existing_draft(self) -> None:
        move = make("P", "e2", "e4")
        parse_result = move_parser.parse("Pe2-e4", {move})
        fake_game = FakeGame(
            initial_moves={move},
            error=game.IllegalMoveError("illegal move"),
        )
        game_session = make_session(fake_game)

        game_session._state.move_text = "Pe2-e4"
        game_session._state.parse_result = parse_result
        game_session._state.feedback = session_types.FeedbackView(kind="action", text="old action")
        game_session._state.last_move_from = sq("a2")
        game_session._state.last_move_to = sq("a4")

        result = game_session.confirm_move_draft()

        assert fake_game.make_move_calls == [(move, False)]
        assert result == session.MoveAttemptResult(
            ok=False,
            status="illegal",
        )

        assert_feedback(game_session._state.feedback, kind="error", text="Could not apply illegal move.")

        assert game_session._state.move_text == "Pe2-e4"
        assert game_session._state.parse_result == parse_result
        assert game_session._state.last_move_from == sq("a2")
        assert game_session._state.last_move_to == sq("a4")
        assert game_session._legal_moves == {move}

        assert_snapshot_flags(
            game_session.snapshot(),
            is_game_over=False,
            can_confirm_move=True,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )

    def test_game_over_failure_returns_game_over_status_without_calling_engine(
        self,
    ) -> None:
        move = make("P", "e2", "e4")
        parse_result = move_parser.parse("Pe2-e4", {move})
        fake_game = FakeGame(initial_moves={move}, outcome="1-0")
        game_session = make_session(fake_game)

        game_session._state.move_text = "Pe2-e4"
        game_session._state.parse_result = parse_result
        game_session._state.feedback = session_types.FeedbackView(kind="action", text="old action")

        result = game_session.confirm_move_draft()

        assert fake_game.make_move_calls == []
        assert result == session.MoveAttemptResult(
            ok=False,
            status="game_over",
        )
        assert_feedback(game_session._state.feedback, kind="error", text="Game has concluded.")
        assert game_session._state.move_text == "Pe2-e4"
        assert game_session._state.parse_result.status == "no_match"
        assert game_session._state.parse_result.raw_text == "Pe2-e4"
        assert game_session._legal_moves == set()
        assert_outcome(
            game_session.snapshot(),
            winner="white",
            reason="checkmate",
            banner="White wins by checkmate.",
        )

        assert_snapshot_flags(
            game_session.snapshot(),
            is_game_over=True,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=False,
            is_promotion_pending=False,
        )

    def test_unexpected_error_returns_generic_result_message(self) -> None:
        move = make("P", "e2", "e4")
        parse_result = move_parser.parse("Pe2-e4", {move})
        fake_game = FakeGame(initial_moves={move}, error=RuntimeError("boom"))
        game_session = make_session(fake_game)

        game_session._state.move_text = "Pe2-e4"
        game_session._state.parse_result = parse_result
        game_session._state.feedback = session_types.FeedbackView(kind="action", text="old action")

        result = game_session.confirm_move_draft()

        assert fake_game.make_move_calls == [(move, False)]
        assert result == session.MoveAttemptResult(
            ok=False,
            status="error",
        )
        assert_feedback(game_session._state.feedback, kind="error", text="Could not apply move.")
        assert game_session._state.move_text == "Pe2-e4"
        assert game_session._state.parse_result == parse_result


class TestUndo:
    def test_halfmove_success_sets_action_message_and_rewinds_highlight(self) -> None:
        first = make("P", "e2", "e4")
        second = make("P", "e7", "e5")
        after_first = make("N", "g8", "f6")
        current = make("N", "g1", "f3")
        fake_game = FakeGame(
            initial_moves={current},
            history=[(first, None), (second, None)],
            undo_halfmove_moves={after_first},
        )
        game_session = make_session(fake_game)

        game_session._state.move_text = "Ng1-f3"
        game_session._state.parse_result = move_parser.parse("Ng1-f3", {current})
        game_session._state.feedback = session_types.FeedbackView(kind="error", text="old error")

        result = game_session.undo(scope="halfmove")

        assert fake_game.undo_halfmove_calls == 1
        assert fake_game.undo_fullmove_calls == 0
        assert result == session.UndoResult(
            ok=True,
            status="undone",
        )

        assert_feedback(game_session._state.feedback, kind="action", text="Move undone.")
        assert game_session._state.move_text == ""
        assert game_session._state.parse_result.status == "empty"
        assert game_session._legal_moves == {after_first}
        assert game_session._state.last_move_from == sq("e2")
        assert game_session._state.last_move_to == sq("e4")

        assert_snapshot_flags(
            game_session.snapshot(),
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=True,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )

    def test_unavailable_returns_failure_preserves_draft_and_clears_stale_highlight(
        self,
    ) -> None:
        current = make("P", "e2", "e4")
        fake_game = FakeGame(initial_moves={current}, history=[])
        game_session = make_session(fake_game)

        game_session._state.move_text = "Pe2-e4"
        game_session._state.parse_result = move_parser.parse("Pe2-e4", {current})
        game_session._state.feedback = session_types.FeedbackView(kind="action", text="old action")
        game_session._state.last_move_from = sq("a2")
        game_session._state.last_move_to = sq("a4")

        result = game_session.undo(scope="halfmove")

        assert fake_game.undo_halfmove_calls == 0
        assert fake_game.undo_fullmove_calls == 0
        assert result == session.UndoResult(
            ok=False,
            status="unavailable",
        )

        assert_feedback(game_session._state.feedback, kind="error", text="No move to undo.")
        assert game_session._state.move_text == "Pe2-e4"
        assert game_session._state.parse_result == move_parser.parse(
            "Pe2-e4", {current}
        )
        assert game_session._state.last_move_from is None
        assert game_session._state.last_move_to is None
        assert game_session._legal_moves == {current}

    def test_unexpected_error_returns_generic_failure_and_preserves_draft(self) -> None:
        last_move = make("P", "e2", "e4")
        current = make("P", "e7", "e5")
        fake_game = FakeGame(
            initial_moves={current},
            history=[(last_move, None)],
            undo_halfmove_error=RuntimeError("boom"),
        )
        game_session = make_session(fake_game)

        game_session._state.move_text = "Pe7-e5"
        game_session._state.parse_result = move_parser.parse("Pe7-e5", {current})
        game_session._state.feedback = session_types.FeedbackView(kind="action", text="old action")

        result = game_session.undo(scope="halfmove")

        assert fake_game.undo_halfmove_calls == 1
        assert result == session.UndoResult(
            ok=False,
            status="error",
        )
        assert_feedback(game_session._state.feedback, kind="error", text="Could not undo move.")
        assert game_session._state.move_text == "Pe7-e5"
        assert game_session._state.parse_result == move_parser.parse(
            "Pe7-e5", {current}
        )
        assert game_session._state.last_move_from == sq("e2")
        assert game_session._state.last_move_to == sq("e4")
        assert game_session._legal_moves == {current}

    def test_defaults_to_fullmove_for_bot_sessions(self) -> None:
        white_move = make("P", "e2", "e4")
        black_move = make("P", "e7", "e5")
        restored = make("P", "d2", "d4")
        fake_game = FakeGame(
            initial_moves={make("N", "g1", "f3")},
            history=[(white_move, None), (black_move, None)],
            undo_fullmove_moves={restored},
        )
        game_session = make_session(fake_game, opponent="bot")

        result = game_session.undo()

        assert fake_game.undo_halfmove_calls == 0
        assert fake_game.undo_fullmove_calls == 1
        assert result == session.UndoResult(
            ok=True,
            status="undone",
        )
        assert_feedback(game_session._state.feedback, kind="action", text="Turn undone.")
        assert game_session._legal_moves == {restored}
        assert game_session._state.last_move_from is None
        assert game_session._state.last_move_to is None

        assert_snapshot_flags(
            game_session.snapshot(),
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )

    def test_online_sessions_reject_undo_and_expose_no_undo_flags(self) -> None:
        prior = make("P", "e2", "e4")
        current = make("P", "e7", "e5")
        fake_game = FakeGame(initial_moves={current}, history=[(prior, None)])
        game_session = make_session(fake_game, opponent="online")

        result = game_session.undo()

        assert fake_game.undo_halfmove_calls == 0
        assert fake_game.undo_fullmove_calls == 0
        assert result == session.UndoResult(
            ok=False,
            status="unavailable",
        )
        assert_feedback(
            game_session.snapshot().feedback,
            kind="error",
            text="Can't undo in an online game.",
        )
        assert_snapshot_flags(
            game_session.snapshot(),
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )


class TestResign:
    def test_success_returns_result_clears_draft_and_updates_game_over_state(
        self,
    ) -> None:
        current = make("P", "e2", "e4")
        fake_game = FakeGame(initial_moves={current}, resign_outcome="0-1")
        game_session = make_session(fake_game)

        game_session._state.move_text = "Pe2-e4"
        game_session._state.parse_result = move_parser.parse("Pe2-e4", {current})
        game_session._state.feedback = session_types.FeedbackView(kind="error", text="old error")

        result = game_session.resign()

        assert fake_game.resign_calls == 1
        assert result == session.ResignResult(
            ok=True,
            status="resigned",
        )

        assert_feedback(game_session._state.feedback, kind="action", text="White resigns.")
        assert game_session._state.move_text == ""
        assert game_session._state.parse_result.status == "empty"
        assert game_session._legal_moves == set()
        assert_outcome(
            game_session.snapshot(),
            winner="black",
            reason="resignation",
            banner="White resigns. Black wins.",
        )

        assert_snapshot_flags(
            game_session.snapshot(),
            is_game_over=True,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=False,
            is_promotion_pending=False,
        )

    def test_success_for_black_returns_black_resigns_message_and_keeps_last_move_highlight(
        self,
    ) -> None:
        previous = make("P", "e2", "e4")
        current = make("P", "e7", "e5")
        fake_game = FakeGame(
            initial_moves={current},
            history=[(previous, None)],
            resign_outcome="1-0",
        )
        game_session = make_session(fake_game)

        game_session._state.move_text = "Pe7-e5"
        game_session._state.parse_result = move_parser.parse("Pe7-e5", {current})
        game_session._state.feedback = session_types.FeedbackView(kind="error", text="old error")

        result = game_session.resign()

        assert fake_game.resign_calls == 1
        assert result == session.ResignResult(
            ok=True,
            status="resigned",
        )

        assert_feedback(game_session._state.feedback, kind="action", text="Black resigns.")
        assert game_session._state.move_text == ""
        assert game_session._state.parse_result.status == "empty"
        assert game_session._legal_moves == set()
        assert_outcome(
            game_session.snapshot(),
            winner="white",
            reason="resignation",
            banner="Black resigns. White wins.",
        )
        assert game_session._state.last_move_from == sq("e2")
        assert game_session._state.last_move_to == sq("e4")

        assert_snapshot_flags(
            game_session.snapshot(),
            is_game_over=True,
            can_confirm_move=False,
            can_undo_halfmove=True,
            can_undo_fullmove=False,
            can_resign=False,
            is_promotion_pending=False,
        )

    def test_game_over_failure_preserves_draft_and_returns_failure_result(self) -> None:
        current = make("P", "e2", "e4")
        parse_result = move_parser.parse("Pe2-e4", {current})
        fake_game = FakeGame(
            initial_moves={current},
            outcome="1-0",
            resign_error=game.GameConcludedError("1-0"),
        )
        game_session = make_session(fake_game)

        game_session._state.move_text = "Pe2-e4"
        game_session._state.parse_result = parse_result
        game_session._state.feedback = session_types.FeedbackView(kind="action", text="old action")

        result = game_session.resign()

        assert fake_game.resign_calls == 0
        assert result == session.ResignResult(
            ok=False,
            status="game_over",
        )

        assert_feedback(game_session._state.feedback, kind="error", text="Game has concluded.")
        assert game_session._state.move_text == "Pe2-e4"
        assert game_session._state.parse_result.status == "no_match"
        assert game_session._state.parse_result.raw_text == "Pe2-e4"
        assert game_session._legal_moves == set()
        assert_outcome(
            game_session.snapshot(),
            winner="white",
            reason="checkmate",
            banner="White wins by checkmate.",
        )

    def test_unexpected_error_returns_generic_failure_and_preserves_draft(self) -> None:
        current = make("P", "e2", "e4")
        parse_result = move_parser.parse("Pe2-e4", {current})
        fake_game = FakeGame(initial_moves={current}, resign_error=RuntimeError("boom"))
        game_session = make_session(fake_game)

        game_session._state.move_text = "Pe2-e4"
        game_session._state.parse_result = parse_result
        game_session._state.feedback = session_types.FeedbackView(kind="action", text="old action")

        result = game_session.resign()

        assert fake_game.resign_calls == 1
        assert result == session.ResignResult(
            ok=False,
            status="error",
        )

        assert_feedback(game_session._state.feedback, kind="error", text="Could not resign game.")
        assert game_session._state.move_text == "Pe2-e4"
        assert game_session._state.parse_result == parse_result
        assert game_session._legal_moves == {current}
        assert game_session.snapshot().outcome is None


class TestSnapshotProjection:
    def test_projects_current_render_state(self) -> None:
        previous = make("P", "e2", "e4")
        current_a = make("P", "e7", "e5")
        current_b = make("N", "g8", "f6")
        legal_moves = {current_a, current_b}
        parse_result = move_parser.parse("", legal_moves)
        board_pieces = {
            sq("a8"): make_piece("R", False, False),
            sq("e8"): make_piece("K", False, False),
            sq("e1"): make_piece("K", True, False),
        }
        fake_game = FakeGame(
            initial_moves=legal_moves,
            history=[(previous, None)],
            is_white_turn=False,
            checked_king_square=sq("e8"),
            board_pieces=board_pieces,
        )
        game_session = make_session(fake_game)

        game_session._state.move_text = ""
        game_session._state.parse_result = parse_result
        game_session._state.feedback = session_types.FeedbackView(kind="action", text="Move undone.")

        snapshot = game_session.snapshot()

        assert snapshot.side_to_move == "black"
        assert len(snapshot.board_glyphs) == 8
        assert all(len(rank) == 8 for rank in snapshot.board_glyphs)
        assert snapshot.board_glyphs[0][0] == "r"  # a8
        assert snapshot.board_glyphs[0][4] == "k"  # e8
        assert snapshot.board_glyphs[7][4] == "K"  # e1

        assert snapshot.last_move_from == sq("e2")
        assert snapshot.last_move_to == sq("e4")
        assert snapshot.move_list == [
            session_types.MoveListItem(ply=1, notation=get_canonical(previous))
        ]

        assert snapshot.move_draft == session_types.MoveDraftView(
            text="",
            status="empty",
            canonical_text=None,
        )
        assert snapshot.move_autocompletions == []
        assert snapshot.candidate_moves == set()
        assert snapshot.promotion_prompt_position is None

        assert snapshot.check_square == sq("e8")
        assert snapshot.outcome is None
        assert_feedback(snapshot.feedback, kind="action", text="Move undone.")
        assert_snapshot_flags(
            snapshot,
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=True,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
            is_player_checked=True,
        )

    def test_uses_parser_matches_for_candidates_autocompletions_and_flags(self) -> None:
        move_a = make("P", "e2", "e4")
        move_b = make("P", "e2", "e3")
        legal_moves = {move_a, move_b}
        fake_game = FakeGame(initial_moves=legal_moves)
        game_session = make_session(fake_game)

        game_session._state.move_text = "Pe"
        game_session._state.parse_result = move_parser.parse("Pe", legal_moves)

        snapshot = game_session.snapshot()

        assert snapshot.move_draft == session_types.MoveDraftView(
            text="Pe",
            status="ambiguous",
            canonical_text=None,
        )
        assert snapshot.candidate_moves == {
            (sq("e2"), sq("e3")),
            (sq("e2"), sq("e4")),
        }
        assert snapshot.move_autocompletions == [
            "Pe2-e3",
            "Pe2-e4",
            "Pe2e3",
            "Pe2e4",
        ]
        assert snapshot.promotion_prompt_position is None
        assert_snapshot_flags(
            snapshot,
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )

    def test_exposes_opponent_sensitive_undo_flags(self) -> None:
        first = make("P", "e2", "e4")
        second = make("P", "e7", "e5")
        current = make("N", "g1", "f3")

        local_session = make_session(
            FakeGame(initial_moves={current}, history=[(first, None), (second, None)]),
            opponent="local",
        )
        bot_session = make_session(
            FakeGame(initial_moves={current}, history=[(first, None), (second, None)]),
            opponent="bot",
        )
        online_session = make_session(
            FakeGame(initial_moves={current}, history=[(first, None), (second, None)]),
            opponent="online",
        )

        assert_snapshot_flags(
            local_session.snapshot(),
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=True,
            can_undo_fullmove=True,
            can_resign=True,
            is_promotion_pending=False,
        )
        assert_snapshot_flags(
            bot_session.snapshot(),
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=True,
            can_resign=True,
            is_promotion_pending=False,
        )
        assert_snapshot_flags(
            online_session.snapshot(),
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )


class TestLifecycle:
    def test_restart_game_preserves_existing_config_and_clears_session_owned_state(
        self,
    ) -> None:
        previous = make("P", "e2", "e4")
        current = make("P", "e7", "e5")
        fake_game = FakeGame(
            initial_moves={current}, history=[(previous, None)], outcome="1-0"
        )
        config = session_types.SessionConfig(player_side="black", opponent="local")
        game_session = session.GameSession(config=config, game=fake_game)

        game_session._state.move_text = "Pe7-e5"
        game_session._state.parse_result = move_parser.parse("Pe7-e5", {current})
        game_session._state.feedback = session_types.FeedbackView(kind="error", text="old error")

        old_game = game_session._game
        game_session.restart_game()

        assert game_session._config == config
        assert game_session._game is not old_game
        assert game_session._state.move_text == ""
        assert game_session._state.parse_result.status == "empty"
        assert game_session._state.last_move_from is None
        assert game_session._state.last_move_to is None
        assert_feedback(game_session._state.feedback, kind="action", text="Game restarted.")
        assert game_session.snapshot().outcome is None
        assert game_session._game.moves_list == []
        assert game_session._legal_moves == game_session._game.get_moves()
        assert_snapshot_flags(
            game_session.snapshot(),
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )

    def test_restart_game_with_new_config_replaces_config_and_sets_action_message(
        self,
    ) -> None:
        current = make("P", "e2", "e4")
        fake_game = FakeGame(initial_moves={current})
        original = session_types.SessionConfig(player_side="white", opponent="local")
        replacement = session_types.SessionConfig(player_side="black", opponent="bot")
        game_session = session.GameSession(config=original, game=fake_game)

        game_session._state.move_text = "Pe2-e4"
        game_session._state.parse_result = move_parser.parse("Pe2-e4", {current})

        game_session.restart_game(config=replacement)

        assert game_session._config == replacement
        assert game_session._state.move_text == ""
        assert game_session._state.parse_result.status == "empty"
        assert_feedback(game_session._state.feedback, kind="action", text="Game restarted.")
        assert game_session._legal_moves == game_session._game.get_moves()


class TestDraftEditing:
    def test_feedback_persists_across_draft_editing_until_next_command_attempt(
        self,
    ) -> None:
        move_a = make("P", "e2", "e4")
        move_b = make("P", "e2", "e3")
        legal_moves = {move_a, move_b}
        fake_game = FakeGame(initial_moves=legal_moves)
        game_session = make_session(fake_game)

        game_session._state.feedback = session_types.FeedbackView(kind="action", text="Move undone.")
        game_session.set_move_text("Pe")
        assert_feedback(game_session.snapshot().feedback, kind="action", text="Move undone.")

        game_session.clear_move_text()
        assert_feedback(game_session.snapshot().feedback, kind="action", text="Move undone.")

        game_session.click_square(sq("e2"))
        assert_feedback(game_session.snapshot().feedback, kind="action", text="Move undone.")

    def test_set_move_text_empty_reparses_to_empty_snapshot_state(self) -> None:
        move = make("P", "e2", "e4")
        fake_game = FakeGame(initial_moves={move})
        game_session = make_session(fake_game)

        game_session.set_move_text("")

        expected = move_parser.parse("", {move})
        snapshot = game_session.snapshot()

        assert game_session._state.move_text == ""
        assert game_session._state.parse_result == expected
        assert snapshot.move_draft == session_types.MoveDraftView(
            text="",
            status=expected.status,
            canonical_text=expected.canonical_text,
        )
        assert snapshot.move_autocompletions == expected.matching_spellings
        assert snapshot.candidate_moves == set(expected.source_to_target_highlights)
        assert_snapshot_flags(
            snapshot,
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )

    def test_set_move_text_no_match_updates_snapshot_state(self) -> None:
        move = make("P", "e2", "e4")
        fake_game = FakeGame(initial_moves={move})
        game_session = make_session(fake_game)

        game_session.set_move_text("zzzz")

        expected = move_parser.parse("zzzz", {move})
        snapshot = game_session.snapshot()

        assert game_session._state.move_text == "zzzz"
        assert game_session._state.parse_result == expected
        assert snapshot.move_draft == session_types.MoveDraftView(
            text="zzzz",
            status=expected.status,
            canonical_text=expected.canonical_text,
        )
        assert snapshot.move_autocompletions == expected.matching_spellings
        assert snapshot.candidate_moves == set(expected.source_to_target_highlights)
        assert_snapshot_flags(
            snapshot,
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )

    def test_set_move_text_ambiguous_updates_autocompletions_and_candidates(
        self,
    ) -> None:
        move_a = make("P", "e2", "e4")
        move_b = make("P", "e2", "e3")
        legal_moves = {move_a, move_b}
        fake_game = FakeGame(initial_moves=legal_moves)
        game_session = make_session(fake_game)

        game_session.set_move_text("Pe")

        expected = move_parser.parse("Pe", legal_moves)
        snapshot = game_session.snapshot()

        assert game_session._state.parse_result == expected
        assert snapshot.move_draft == session_types.MoveDraftView(
            text="Pe",
            status=expected.status,
            canonical_text=expected.canonical_text,
        )
        assert snapshot.move_autocompletions == expected.matching_spellings
        assert snapshot.candidate_moves == set(expected.source_to_target_highlights)
        assert_snapshot_flags(
            snapshot,
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )

    def test_set_move_text_resolved_updates_canonical_text_candidate_and_flags(
        self,
    ) -> None:
        move = make("P", "e2", "e4")
        fake_game = FakeGame(initial_moves={move})
        game_session = make_session(fake_game)

        game_session.set_move_text("Pe2-e4")

        expected = move_parser.parse("Pe2-e4", {move})
        snapshot = game_session.snapshot()

        assert game_session._state.parse_result == expected
        assert snapshot.move_draft == session_types.MoveDraftView(
            text="Pe2-e4",
            status=expected.status,
            canonical_text=expected.canonical_text,
        )
        assert snapshot.move_autocompletions == expected.matching_spellings
        assert snapshot.candidate_moves == set(expected.source_to_target_highlights)
        assert_snapshot_flags(
            snapshot,
            is_game_over=False,
            can_confirm_move=True,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )

    def test_clear_move_text_clears_existing_draft_and_resets_snapshot_state(
        self,
    ) -> None:
        move_a = make("P", "e2", "e4")
        move_b = make("P", "e2", "e3")
        legal_moves = {move_a, move_b}
        fake_game = FakeGame(initial_moves=legal_moves)
        game_session = make_session(fake_game)

        game_session.set_move_text("Pe")
        game_session.clear_move_text()

        expected = move_parser.parse("", legal_moves)
        snapshot = game_session.snapshot()

        assert game_session._state.move_text == ""
        assert game_session._state.parse_result == expected
        assert snapshot.move_draft == session_types.MoveDraftView(
            text="",
            status=expected.status,
            canonical_text=expected.canonical_text,
        )
        assert snapshot.move_autocompletions == expected.matching_spellings
        assert snapshot.candidate_moves == set(expected.source_to_target_highlights)
        assert_snapshot_flags(
            snapshot,
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )


class TestClickDrafting:
    def test_empty_draft_on_movable_source_authors_source_prefix(self) -> None:
        move_a = make("P", "e2", "e4")
        move_b = make("P", "e2", "e3")
        legal_moves = {move_a, move_b}
        fake_game = FakeGame(initial_moves=legal_moves)
        game_session = make_session(fake_game)

        game_session.click_square(sq("e2"))
        snapshot = game_session.snapshot()

        assert game_session._state.move_text == "Pe2"
        assert snapshot.move_draft == session_types.MoveDraftView(
            text="Pe2",
            status="ambiguous",
            canonical_text=None,
        )
        assert snapshot.candidate_moves == {
            (sq("e2"), sq("e3")),
            (sq("e2"), sq("e4")),
        }
        assert snapshot.move_autocompletions == [
            "Pe2-e3",
            "Pe2-e4",
            "Pe2e3",
            "Pe2e4",
        ]
        assert_snapshot_flags(
            snapshot,
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )

    def test_second_click_on_target_refines_to_resolved_move(self) -> None:
        move_a = make("P", "e2", "e4")
        move_b = make("P", "e2", "e3")
        legal_moves = {move_a, move_b}
        fake_game = FakeGame(initial_moves=legal_moves)
        game_session = make_session(fake_game)

        game_session.click_square(sq("e2"))
        game_session.click_square(sq("e4"))
        snapshot = game_session.snapshot()

        assert game_session._state.move_text == "Pe2-e4"
        assert snapshot.move_draft == session_types.MoveDraftView(
            text="Pe2-e4",
            status="resolved",
            canonical_text="Pe2-e4",
        )
        assert snapshot.candidate_moves == {(sq("e2"), sq("e4"))}
        assert snapshot.move_autocompletions == ["Pe2-e4"]
        assert_snapshot_flags(
            snapshot,
            is_game_over=False,
            can_confirm_move=True,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )

    def test_replaces_partial_draft_with_new_source_when_new_square_is_movable(
        self,
    ) -> None:
        e2e4 = make("P", "e2", "e4")
        e2e3 = make("P", "e2", "e3")
        g1f3 = make("N", "g1", "f3")
        g1h3 = make("N", "g1", "h3")
        legal_moves = {e2e4, e2e3, g1f3, g1h3}
        fake_game = FakeGame(initial_moves=legal_moves)
        game_session = make_session(fake_game)

        game_session.click_square(sq("e2"))
        game_session.click_square(sq("g1"))
        snapshot = game_session.snapshot()

        assert game_session._state.move_text == "Ng1"
        assert snapshot.move_draft == session_types.MoveDraftView(
            text="Ng1",
            status="ambiguous",
            canonical_text=None,
        )
        assert snapshot.candidate_moves == {
            (sq("g1"), sq("f3")),
            (sq("g1"), sq("h3")),
        }

    def test_on_no_match_typed_draft_replaces_with_clicked_source_prefix(self) -> None:
        move_a = make("P", "e2", "e4")
        move_b = make("P", "e2", "e3")
        legal_moves = {move_a, move_b}
        fake_game = FakeGame(initial_moves=legal_moves)
        game_session = make_session(fake_game)

        game_session.set_move_text("zzzz")
        assert game_session._state.parse_result.status == "no_match"

        game_session.click_square(sq("e2"))
        snapshot = game_session.snapshot()

        assert game_session._state.move_text == "Pe2"
        assert snapshot.move_draft == session_types.MoveDraftView(
            text="Pe2",
            status="ambiguous",
            canonical_text=None,
        )
        assert snapshot.candidate_moves == {
            (sq("e2"), sq("e3")),
            (sq("e2"), sq("e4")),
        }

    def test_click_on_game_over_position_reparses_against_empty_legal_moves(self) -> None:
        move = make("P", "e2", "e4")
        fake_game = FakeGame(initial_moves={move}, outcome="1-0")
        game_session = make_session(fake_game)

        game_session._state.move_text = "Pe2-e4"
        game_session._state.parse_result = move_parser.parse("Pe2-e4", set())

        game_session.click_square(sq("e2"))

        assert game_session._state.move_text == ""
        assert game_session._state.parse_result == move_parser.parse("", set())
        assert_outcome(
            game_session.snapshot(),
            winner="white",
            reason="checkmate",
            banner="White wins by checkmate.",
        )

    def test_dead_end_click_self_clears_draft(self) -> None:
        move_a = make("P", "e2", "e4")
        move_b = make("P", "e2", "e3")
        legal_moves = {move_a, move_b}
        fake_game = FakeGame(initial_moves=legal_moves)
        game_session = make_session(fake_game)

        game_session.click_square(sq("e2"))
        assert game_session._state.move_text == "Pe2"

        game_session.click_square(sq("a1"))
        snapshot = game_session.snapshot()

        assert game_session._state.move_text == ""
        assert snapshot.move_draft == session_types.MoveDraftView(
            text="",
            status="empty",
            canonical_text=None,
        )
        assert snapshot.candidate_moves == set()
        assert snapshot.move_autocompletions == []
        assert snapshot.promotion_prompt_position is None
        assert_snapshot_flags(
            snapshot,
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )


class TestPromotionDrafting:
    def test_click_square_promotion_source_does_not_show_prompt_until_destination_is_chosen(
        self,
    ) -> None:
        q = make("P", "e7", "e8", promotion="Q")
        r = make("P", "e7", "e8", promotion="R")
        b = make("P", "e7", "e8", promotion="B")
        n = make("P", "e7", "e8", promotion="N")
        legal_moves = {q, r, b, n}
        fake_game = FakeGame(initial_moves=legal_moves)
        game_session = make_session(fake_game)

        game_session.click_square(sq("e7"))
        snapshot = game_session.snapshot()

        assert game_session._state.move_text == "Pe7"
        assert snapshot.move_draft == session_types.MoveDraftView(
            text="Pe7",
            status="ambiguous",
            canonical_text=None,
        )
        assert snapshot.candidate_moves == {(sq("e7"), sq("e8"))}
        assert snapshot.promotion_prompt_position is None
        assert_snapshot_flags(
            snapshot,
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )

    def test_click_square_promotion_destination_sets_ambiguous_promotion_prefix_and_prompt(
        self,
    ) -> None:
        q = make("P", "e7", "e8", promotion="Q")
        r = make("P", "e7", "e8", promotion="R")
        b = make("P", "e7", "e8", promotion="B")
        n = make("P", "e7", "e8", promotion="N")
        legal_moves = {q, r, b, n}
        fake_game = FakeGame(initial_moves=legal_moves)
        game_session = make_session(fake_game)

        game_session.click_square(sq("e7"))
        game_session.click_square(sq("e8"))
        snapshot = game_session.snapshot()

        assert game_session._state.move_text == "Pe7-e8="
        assert snapshot.move_draft == session_types.MoveDraftView(
            text="Pe7-e8=",
            status="ambiguous",
            canonical_text=None,
        )
        assert snapshot.candidate_moves == {(sq("e7"), sq("e8"))}
        assert snapshot.move_autocompletions == [
            "Pe7-e8=B",
            "Pe7-e8=N",
            "Pe7-e8=Q",
            "Pe7-e8=R",
        ]
        assert snapshot.promotion_prompt_position == sq("e8")
        assert_snapshot_flags(
            snapshot,
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=True,
        )

    def test_select_promotion_piece_resolves_draft_and_clears_prompt(self) -> None:
        q = make("P", "e7", "e8", promotion="Q")
        r = make("P", "e7", "e8", promotion="R")
        b = make("P", "e7", "e8", promotion="B")
        n = make("P", "e7", "e8", promotion="N")
        legal_moves = {q, r, b, n}
        fake_game = FakeGame(initial_moves=legal_moves)
        game_session = make_session(fake_game)

        game_session.click_square(sq("e7"))
        game_session.click_square(sq("e8"))
        game_session.select_promotion_piece("Q")
        snapshot = game_session.snapshot()

        assert game_session._state.move_text == "Pe7-e8=Q"
        assert snapshot.move_draft == session_types.MoveDraftView(
            text="Pe7-e8=Q",
            status="resolved",
            canonical_text="Pe7-e8=Q",
        )
        assert snapshot.candidate_moves == {(sq("e7"), sq("e8"))}
        assert snapshot.move_autocompletions == ["Pe7-e8=Q"]
        assert snapshot.promotion_prompt_position is None
        assert_snapshot_flags(
            snapshot,
            is_game_over=False,
            can_confirm_move=True,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )

    def test_select_promotion_piece_without_active_promotion_prompt_is_inert(
        self,
    ) -> None:
        move = make("P", "e2", "e4")
        fake_game = FakeGame(initial_moves={move})
        game_session = make_session(fake_game)

        game_session.set_move_text("Pe2-e4")
        before_parse = game_session._state.parse_result

        game_session.select_promotion_piece("Q")
        snapshot = game_session.snapshot()

        assert game_session._state.move_text == "Pe2-e4"
        assert game_session._state.parse_result == before_parse
        assert snapshot.move_draft == session_types.MoveDraftView(
            text="Pe2-e4",
            status="resolved",
            canonical_text="Pe2-e4",
        )
        assert snapshot.promotion_prompt_position is None
        assert_snapshot_flags(
            snapshot,
            is_game_over=False,
            can_confirm_move=True,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )


class TestTimingProjection:
    def test_untimed_snapshot_exposes_no_timing_view(self) -> None:
        move = make("P", "e2", "e4")
        fake_game = FakeGame(initial_moves={move})
        game_session = make_session(fake_game)

        snapshot = game_session.snapshot()

        assert snapshot.timed_game is None

    def test_timed_snapshot_projects_render_ready_clock_data(self) -> None:
        move = make("P", "e2", "e4")
        fake_clock = FakeClock(0)
        fake_game = FakeGame(initial_moves={move}, is_white_turn=True)
        game_session = make_session(
            fake_game,
            time_control=session_types.TimeControl(
                initial_seconds=60, increment_seconds=2
            ),
            time_source=fake_clock,
        )

        snapshot = game_session.snapshot()

        assert_timed_game(
            snapshot,
            white_remaining_ms=60_000,
            black_remaining_ms=60_000,
            active_side="white",
            timeout_side=None,
            increment_seconds=2,
            white_display_text="1:00",
            black_display_text="1:00",
            white_active=True,
            black_active=False,
        )

    def test_snapshot_advances_active_clock(self) -> None:
        move = make("P", "e2", "e4")
        fake_clock = FakeClock(0)
        fake_game = FakeGame(initial_moves={move}, is_white_turn=True)
        game_session = make_session(
            fake_game,
            time_control=session_types.TimeControl(
                initial_seconds=60, increment_seconds=0
            ),
            time_source=fake_clock,
        )

        fake_clock.advance(5_000)
        snapshot = game_session.snapshot()

        assert_timed_game(
            snapshot,
            white_remaining_ms=55_000,
            black_remaining_ms=60_000,
            active_side="white",
            timeout_side=None,
            increment_seconds=0,
            white_display_text="0:55",
            black_display_text="1:00",
            white_active=True,
            black_active=False,
        )


class TestTimingCommands:
    def test_confirm_move_applies_increment_and_switches_active_side(self) -> None:
        move = make("P", "e2", "e4")
        reply = make("P", "e7", "e5")
        fake_clock = FakeClock(0)
        fake_game = FakeGame(
            initial_moves={move},
            next_moves={reply},
            is_white_turn=True,
            next_is_white_turn=False,
        )
        game_session = make_session(
            fake_game,
            time_control=session_types.TimeControl(
                initial_seconds=30, increment_seconds=2
            ),
            time_source=fake_clock,
        )

        game_session.set_move_text("Pe2-e4")
        fake_clock.advance(5_000)

        result = game_session.confirm_move_draft()
        snapshot = game_session.snapshot()

        assert result == session.MoveAttemptResult(
            ok=True,
            status="applied",
        )
        assert_timed_game(
            snapshot,
            white_remaining_ms=27_000,
            black_remaining_ms=30_000,
            active_side="black",
            timeout_side=None,
            increment_seconds=2,
            white_display_text="0:27",
            black_display_text="0:30",
            white_active=False,
            black_active=True,
        )

    def test_timeout_blocks_move_confirmation(self) -> None:
        move = make("P", "e2", "e4")
        fake_clock = FakeClock(0)
        fake_game = FakeGame(initial_moves={move}, is_white_turn=True)
        game_session = make_session(
            fake_game,
            time_control=session_types.TimeControl(
                initial_seconds=5, increment_seconds=0
            ),
            time_source=fake_clock,
        )

        game_session.set_move_text("Pe2-e4")
        fake_clock.advance(5_000)

        result = game_session.confirm_move_draft()
        snapshot = game_session.snapshot()

        assert result == session.MoveAttemptResult(
            ok=False,
            status="game_over",
        )
        assert_outcome(
            snapshot,
            winner="black",
            reason="timeout",
            banner="Black wins on time.",
        )
        assert_snapshot_flags(
            snapshot,
            is_game_over=True,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=False,
            is_promotion_pending=False,
        )
        assert_timed_game(
            snapshot,
            white_remaining_ms=0,
            black_remaining_ms=5_000,
            active_side=None,
            timeout_side="white",
            increment_seconds=0,
            white_display_text="0:00",
            black_display_text="0:05",
            white_active=False,
            black_active=False,
            white_flagged=True,
            black_flagged=False,
        )

    def test_undo_remains_available_after_timeout_and_restores_clock_state(
        self,
    ) -> None:
        move = make("P", "e2", "e4")
        reply = make("P", "e7", "e5")
        fake_clock = FakeClock(0)
        fake_game = FakeGame(
            initial_moves={move},
            next_moves={reply},
            is_white_turn=True,
            next_is_white_turn=False,
            undo_halfmove_moves={move},
            undo_halfmove_is_white_turn=True,
        )
        game_session = make_session(
            fake_game,
            time_control=session_types.TimeControl(
                initial_seconds=5, increment_seconds=0
            ),
            time_source=fake_clock,
        )

        game_session.set_move_text("Pe2-e4")
        fake_clock.advance(1_000)
        applied = game_session.confirm_move_draft()
        assert applied.ok is True

        fake_clock.advance(6_000)
        timeout_snapshot = game_session.snapshot()
        assert_outcome(
            timeout_snapshot,
            winner="white",
            reason="timeout",
            banner="White wins on time.",
        )
        assert_snapshot_flags(
            timeout_snapshot,
            is_game_over=True,
            can_confirm_move=False,
            can_undo_halfmove=True,
            can_undo_fullmove=False,
            can_resign=False,
            is_promotion_pending=False,
        )

        result = game_session.undo(scope="halfmove")
        restored = game_session.snapshot()

        assert result == session.UndoResult(
            ok=True,
            status="undone",
        )
        assert_snapshot_flags(
            restored,
            is_game_over=False,
            can_confirm_move=False,
            can_undo_halfmove=False,
            can_undo_fullmove=False,
            can_resign=True,
            is_promotion_pending=False,
        )
        assert restored.outcome is None
        assert_timed_game(
            restored,
            white_remaining_ms=4_000,
            black_remaining_ms=5_000,
            active_side="white",
            timeout_side=None,
            increment_seconds=0,
            white_display_text="0:04",
            black_display_text="0:05",
            white_active=True,
            black_active=False,
        )
