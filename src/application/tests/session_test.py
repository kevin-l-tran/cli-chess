from helpers import make, sq

from src.application import move_parser
from src.application import session, session_types
from src.engine import moves, game
from src.engine.board import Piece, make_piece
from src.application.move_parser import get_canonical

Move = moves.Move


class FakeBoard:
    def __init__(self, pieces: dict[tuple[int, int], Piece] | None = None) -> None:
        self._pieces = dict(pieces or {})

    def piece_at(self, position: tuple[int, int]) -> Piece | None:
        return self._pieces.get(position)


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

    def undo_halfmove(self) -> None:
        self.undo_halfmove_calls += 1

        if self._undo_halfmove_error is not None:
            raise self._undo_halfmove_error

        if not self.moves_list:
            raise game.NoMoveToUndoError()

        self.moves_list.pop()
        self._moves = set(self._undo_halfmove_moves)

    def undo_fullmove(self) -> None:
        self.undo_fullmove_calls += 1

        if self._undo_fullmove_error is not None:
            raise self._undo_fullmove_error

        if len(self.moves_list) < 2:
            raise game.NoMoveToUndoError()

        self.moves_list.pop()
        self.moves_list.pop()
        self._moves = set(self._undo_fullmove_moves)

    def resign(self) -> None:
        self.resign_calls += 1

        if self._resign_error is not None:
            raise self._resign_error

        self.outcome = self._resign_outcome
        self._moves = set()

    def checked_king_position(self) -> tuple[int, int] | None:
        return self._checked_king_square


def make_session(
    game: FakeGame, *, opponent: session_types.OpponentType = "local"
) -> session.GameSession:
    config = session_types.SessionConfig(player_side="white", opponent=opponent)
    return session.GameSession(config=config, game=game)


def test_confirm_move_draft_applies_resolved_move_clears_draft_and_refreshes_legal_moves() -> (
    None
):
    move = make("P", "e2", "e4")
    reply = make("P", "e7", "e5")
    fake_game = FakeGame(initial_moves={move}, next_moves={reply})
    game_session = make_session(fake_game)

    game_session._state.move_text = "Pe2-e4"
    game_session._state.parse_result = move_parser.parse("Pe2-e4", {move})
    game_session._state.last_error_message = "old error"

    result = game_session.confirm_move_draft(offer_draw=True)

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


def test_confirm_move_draft_empty_failure_returns_stable_feedback_without_calling_engine() -> (
    None
):
    move = make("P", "e2", "e4")
    fake_game = FakeGame(initial_moves={move})
    game_session = make_session(fake_game)

    game_session._state.move_text = ""
    game_session._state.parse_result = move_parser.parse("", {move})
    game_session._state.last_move_from = sq("a2")
    game_session._state.last_move_to = sq("a4")

    result = game_session.confirm_move_draft()

    assert fake_game.make_move_calls == []
    assert result == session.MoveAttemptResult(
        ok=False,
        status="empty",
        message="Enter a move first.",
    )
    assert game_session._state.last_error_message == "Enter a move first."
    assert game_session._state.move_text == ""
    assert game_session._state.parse_result == move_parser.parse("", {move})
    assert game_session._state.last_move_from == sq("a2")
    assert game_session._state.last_move_to == sq("a4")
    assert game_session._legal_moves == {move}


def test_confirm_move_draft_ambiguous_failure_returns_stable_feedback_without_calling_engine() -> (
    None
):
    move_a = make("P", "e2", "e4")
    move_b = make("P", "e2", "e3")
    legal_moves = {move_a, move_b}
    parse_result = move_parser.parse("Pe", legal_moves)
    fake_game = FakeGame(initial_moves=legal_moves)
    game_session = make_session(fake_game)

    game_session._state.move_text = "Pe"
    game_session._state.parse_result = parse_result
    game_session._state.last_move_from = sq("a2")
    game_session._state.last_move_to = sq("a4")

    result = game_session.confirm_move_draft()

    assert fake_game.make_move_calls == []
    assert result == session.MoveAttemptResult(
        ok=False,
        status="ambiguous",
        message="Move is ambiguous.",
    )
    assert game_session._state.last_error_message == "Move is ambiguous."
    assert game_session._state.move_text == "Pe"
    assert game_session._state.parse_result == parse_result
    assert game_session._state.last_move_from == sq("a2")
    assert game_session._state.last_move_to == sq("a4")
    assert game_session._legal_moves == legal_moves


def test_confirm_move_draft_no_match_failure_returns_stable_feedback_without_calling_engine() -> (
    None
):
    move = make("P", "e2", "e4")
    parse_result = move_parser.parse("zzzz", {move})
    fake_game = FakeGame(initial_moves={move})
    game_session = make_session(fake_game)

    game_session._state.move_text = "zzzz"
    game_session._state.parse_result = parse_result
    game_session._state.last_move_from = sq("a2")
    game_session._state.last_move_to = sq("a4")

    result = game_session.confirm_move_draft()

    assert fake_game.make_move_calls == []
    assert result == session.MoveAttemptResult(
        ok=False,
        status="no_match",
        message="No legal move matches the current draft.",
    )
    assert (
        game_session._state.last_error_message
        == "No legal move matches the current draft."
    )
    assert game_session._state.move_text == "zzzz"
    assert game_session._state.parse_result == parse_result
    assert game_session._state.last_move_from == sq("a2")
    assert game_session._state.last_move_to == sq("a4")
    assert game_session._legal_moves == {move}


def test_confirm_move_draft_illegal_failure_sets_feedback_and_preserves_existing_draft() -> (
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

    result = game_session.confirm_move_draft()

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


def test_confirm_move_draft_game_over_failure_returns_game_over_status_without_calling_engine() -> (
    None
):
    move = make("P", "e2", "e4")
    parse_result = move_parser.parse("Pe2-e4", {move})
    fake_game = FakeGame(
        initial_moves={move},
        outcome="1-0",
    )
    game_session = make_session(fake_game)

    game_session._state.move_text = "Pe2-e4"
    game_session._state.parse_result = parse_result

    result = game_session.confirm_move_draft()

    assert fake_game.make_move_calls == []
    assert result == session.MoveAttemptResult(
        ok=False,
        status="game_over",
        message="Game has concluded.",
    )
    assert game_session._state.last_error_message == "Game has concluded."
    assert game_session._state.move_text == "Pe2-e4"
    assert game_session._state.parse_result.status == "no_match"
    assert game_session._state.parse_result.raw_text == "Pe2-e4"
    assert game_session._legal_moves == set()
    assert game_session._state.outcome_banner == "White wins."


def test_confirm_move_draft_unexpected_error_returns_generic_result_message() -> None:
    move = make("P", "e2", "e4")
    parse_result = move_parser.parse("Pe2-e4", {move})
    fake_game = FakeGame(
        initial_moves={move},
        error=RuntimeError("boom"),
    )
    game_session = make_session(fake_game)

    game_session._state.move_text = "Pe2-e4"
    game_session._state.parse_result = parse_result

    result = game_session.confirm_move_draft()

    assert fake_game.make_move_calls == [(move, False)]
    assert result == session.MoveAttemptResult(
        ok=False,
        status="error",
        message="Could not apply move.",
    )

    assert game_session._state.last_error_message == "Could not apply move."

    # Unexpected failure also preserves the user's draft.
    assert game_session._state.move_text == "Pe2-e4"
    assert game_session._state.parse_result == parse_result


def test_undo_halfmove_success_clears_draft_refreshes_legal_moves_and_rewinds_highlight() -> (
    None
):
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
    game_session._state.last_error_message = "old error"

    result = game_session.undo(scope="halfmove")

    assert fake_game.undo_halfmove_calls == 1
    assert fake_game.undo_fullmove_calls == 0
    assert result == session.UndoResult(
        ok=True,
        status="undone",
        message="Move undone.",
    )

    assert game_session._state.last_error_message is None
    assert game_session._state.move_text == ""
    assert game_session._state.parse_result is not None
    assert game_session._state.parse_result.status == "empty"
    assert game_session._legal_moves == {after_first}

    # Highlight should now point at the remaining last move in history.
    assert game_session._state.last_move_from == sq("e2")
    assert game_session._state.last_move_to == sq("e4")


def test_undo_unavailable_returns_failure_preserves_draft_and_clears_stale_highlight() -> (
    None
):
    current = make("P", "e2", "e4")
    fake_game = FakeGame(initial_moves={current}, history=[])
    game_session = make_session(fake_game)

    game_session._state.move_text = "Pe2-e4"
    game_session._state.parse_result = move_parser.parse("Pe2-e4", {current})
    game_session._state.last_move_from = sq("a2")
    game_session._state.last_move_to = sq("a4")

    result = game_session.undo(scope="halfmove")

    assert fake_game.undo_halfmove_calls == 1
    assert result == session.UndoResult(
        ok=False,
        status="unavailable",
        message="No move to undo.",
    )

    assert game_session._state.last_error_message == "No move to undo."
    assert game_session._state.move_text == "Pe2-e4"
    assert game_session._state.parse_result == move_parser.parse("Pe2-e4", {current})
    assert game_session._state.last_move_from is None
    assert game_session._state.last_move_to is None
    assert game_session._legal_moves == {current}


def test_undo_unexpected_error_returns_generic_failure_and_preserves_draft() -> None:
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

    result = game_session.undo(scope="halfmove")

    assert fake_game.undo_halfmove_calls == 1
    assert result == session.UndoResult(
        ok=False,
        status="error",
        message="Could not undo move.",
    )
    assert game_session._state.last_error_message == "Could not undo move."

    # Failure preserves the draft and leaves highlight derived from current history.
    assert game_session._state.move_text == "Pe7-e5"
    assert game_session._state.parse_result == move_parser.parse("Pe7-e5", {current})
    assert game_session._state.last_move_from == sq("e2")
    assert game_session._state.last_move_to == sq("e4")
    assert game_session._legal_moves == {current}


def test_undo_defaults_to_fullmove_for_bot_sessions() -> None:
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
        message="Turn undone.",
    )
    assert game_session._legal_moves == {restored}
    assert game_session._state.last_move_from is None
    assert game_session._state.last_move_to is None


def test_resign_success_returns_result_clears_draft_and_updates_game_over_state() -> (
    None
):
    current = make("P", "e2", "e4")
    fake_game = FakeGame(
        initial_moves={current},
        resign_outcome="0-1",
    )
    game_session = make_session(fake_game)

    game_session._state.move_text = "Pe2-e4"
    game_session._state.parse_result = move_parser.parse("Pe2-e4", {current})
    game_session._state.last_error_message = "old error"

    result = game_session.resign()

    assert fake_game.resign_calls == 1
    assert result == session.ResignResult(
        ok=True,
        status="resigned",
        message="White resigns.",
    )

    assert game_session._state.last_error_message is None
    assert game_session._state.move_text == ""
    assert game_session._state.parse_result is not None
    assert game_session._state.parse_result.status == "empty"
    assert game_session._legal_moves == set()
    assert game_session._state.outcome_banner == "Black wins."


def test_resign_success_for_black_returns_black_resigns_message_and_keeps_last_move_highlight() -> (
    None
):
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
    game_session._state.last_error_message = "old error"

    result = game_session.resign()

    assert fake_game.resign_calls == 1
    assert result == session.ResignResult(
        ok=True,
        status="resigned",
        message="Black resigns.",
    )

    assert game_session._state.last_error_message is None
    assert game_session._state.move_text == ""
    assert game_session._state.parse_result is not None
    assert game_session._state.parse_result.status == "empty"
    assert game_session._legal_moves == set()
    assert game_session._state.outcome_banner == "White wins."
    assert game_session._state.last_move_from == sq("e2")
    assert game_session._state.last_move_to == sq("e4")


def test_resign_game_over_failure_preserves_draft_and_returns_failure_result() -> None:
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

    result = game_session.resign()

    assert fake_game.resign_calls == 1
    assert result == session.ResignResult(
        ok=False,
        status="game_over",
        message="Game has concluded.",
    )

    assert game_session._state.last_error_message == "Game has concluded."
    assert game_session._state.move_text == "Pe2-e4"
    assert game_session._state.parse_result.status == "no_match"
    assert game_session._state.parse_result.raw_text == "Pe2-e4"
    assert game_session._legal_moves == set()
    assert game_session._state.outcome_banner == "White wins."


def test_resign_game_over_failure_with_draw_outcome_sets_draw_banner() -> None:
    current = make("P", "e2", "e4")
    parse_result = move_parser.parse("Pe2-e4", {current})
    fake_game = FakeGame(
        initial_moves={current},
        outcome="1/2-1/2",
        resign_error=game.GameConcludedError("1/2-1/2"),
    )
    game_session = make_session(fake_game)

    game_session._state.move_text = "Pe2-e4"
    game_session._state.parse_result = parse_result

    result = game_session.resign()

    assert fake_game.resign_calls == 1
    assert result == session.ResignResult(
        ok=False,
        status="game_over",
        message="Game has concluded.",
    )
    assert game_session._state.last_error_message == "Game has concluded."
    assert game_session._state.move_text == "Pe2-e4"
    assert game_session._state.parse_result.status == "no_match"
    assert game_session._state.parse_result.raw_text == "Pe2-e4"
    assert game_session._legal_moves == set()
    assert game_session._state.outcome_banner == "Draw."


def test_resign_unexpected_error_returns_generic_failure_and_preserves_draft() -> None:
    current = make("P", "e2", "e4")
    parse_result = move_parser.parse("Pe2-e4", {current})
    fake_game = FakeGame(
        initial_moves={current},
        resign_error=RuntimeError("boom"),
    )
    game_session = make_session(fake_game)

    game_session._state.move_text = "Pe2-e4"
    game_session._state.parse_result = parse_result

    result = game_session.resign()

    assert fake_game.resign_calls == 1
    assert result == session.ResignResult(
        ok=False,
        status="error",
        message="Could not resign game.",
    )

    assert game_session._state.last_error_message == "Could not resign game."
    assert game_session._state.move_text == "Pe2-e4"
    assert game_session._state.parse_result == parse_result
    assert game_session._legal_moves == {current}
    assert game_session._state.outcome_banner is None


def test_snapshot_projects_current_render_state() -> None:
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
    game_session._state.last_error_message = "old error"

    snapshot = game_session.snapshot()

    assert snapshot.side_to_move == "black"
    assert snapshot.flipped is False
    assert snapshot.cursor == (0, 0)

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

    assert snapshot.check_square == sq("e8")
    assert snapshot.is_checked is True
    assert snapshot.outcome_banner is None
    assert snapshot.last_error_message == "old error"


def test_snapshot_uses_parser_matches_for_candidates_and_autocompletions() -> None:
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


def test_snapshot_flipped_reflects_player_side_and_orientation_override() -> None:
    move = make("P", "e2", "e4")
    fake_game = FakeGame(initial_moves={move})
    config = session_types.SessionConfig(player_side="black")
    game_session = session.GameSession(config=config, game=fake_game)

    assert game_session.snapshot().flipped is True

    game_session._state.orientation_override = True

    assert game_session.snapshot().flipped is False


def test_restart_game_preserves_existing_config_and_clears_session_owned_state() -> (
    None
):
    previous = make("P", "e2", "e4")
    current = make("P", "e7", "e5")
    fake_game = FakeGame(
        initial_moves={current},
        history=[(previous, None)],
        outcome="1-0",
    )
    config = session_types.SessionConfig(player_side="black", opponent="local")
    game_session = session.GameSession(config=config, game=fake_game)

    game_session._state.cursor = sq("c3")
    game_session._state.move_text = "Pe7-e5"
    game_session._state.parse_result = move_parser.parse("Pe7-e5", {current})
    game_session._state.orientation_override = True
    game_session._state.last_error_message = "old error"

    listeners_before = []
    game_session.subscribe(listeners_before.append)
    old_game = game_session._game

    game_session.restart_game()

    assert game_session._config == config
    assert game_session._game is not old_game
    assert game_session._listeners == [listeners_before.append]

    assert game_session._state.cursor == (0, 0)
    assert game_session._state.move_text == ""
    assert game_session._state.parse_result.status == "empty"
    assert game_session._state.orientation_override is False
    assert game_session._state.last_move_from is None
    assert game_session._state.last_move_to is None
    assert game_session._state.last_error_message is None
    assert game_session._state.outcome_banner is None

    assert game_session._game.moves_list == []
    assert game_session._legal_moves == game_session._game.get_moves()
    assert game_session.snapshot().flipped is True


def test_restart_game_with_new_config_replaces_config_and_uses_new_default_orientation() -> (
    None
):
    current = make("P", "e2", "e4")
    fake_game = FakeGame(initial_moves={current})
    original = session_types.SessionConfig(player_side="white", opponent="local")
    replacement = session_types.SessionConfig(player_side="black", opponent="bot")
    game_session = session.GameSession(config=original, game=fake_game)

    game_session._state.orientation_override = True
    game_session._state.move_text = "Pe2-e4"
    game_session._state.parse_result = move_parser.parse("Pe2-e4", {current})

    game_session.restart_game(config=replacement)

    assert game_session._config == replacement
    assert game_session.snapshot().flipped is True
    assert game_session._state.orientation_override is False
    assert game_session._state.move_text == ""
    assert game_session._state.parse_result.status == "empty"
    assert game_session._legal_moves == game_session._game.get_moves()


def test_set_move_text_empty_reparses_to_empty_snapshot_state() -> None:
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


def test_set_move_text_no_match_updates_snapshot_state() -> None:
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


def test_set_move_text_ambiguous_updates_autocompletions_and_candidates() -> None:
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


def test_set_move_text_resolved_updates_canonical_text_and_candidate() -> None:
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


def test_clear_move_text_clears_existing_draft_and_resets_snapshot_state() -> None:
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


def test_click_square_empty_draft_on_movable_source_authors_source_prefix() -> None:
    move_a = make("P", "e2", "e4")
    move_b = make("P", "e2", "e3")
    legal_moves = {move_a, move_b}
    fake_game = FakeGame(initial_moves=legal_moves)
    game_session = make_session(fake_game)

    game_session.click_square(sq("e2"))

    snapshot = game_session.snapshot()

    assert game_session._state.cursor == sq("e2")
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


def test_click_square_second_click_on_target_refines_to_resolved_move() -> None:
    move_a = make("P", "e2", "e4")
    move_b = make("P", "e2", "e3")
    legal_moves = {move_a, move_b}
    fake_game = FakeGame(initial_moves=legal_moves)
    game_session = make_session(fake_game)

    game_session.click_square(sq("e2"))
    game_session.click_square(sq("e4"))

    snapshot = game_session.snapshot()

    assert game_session._state.cursor == sq("e4")
    assert game_session._state.move_text == "Pe2-e4"
    assert snapshot.move_draft == session_types.MoveDraftView(
        text="Pe2-e4",
        status="resolved",
        canonical_text="Pe2-e4",
    )
    assert snapshot.candidate_moves == {
        (sq("e2"), sq("e4")),
    }
    assert snapshot.move_autocompletions == [
        "Pe2-e4",
    ]


def test_click_square_replaces_partial_draft_with_new_source_when_new_square_is_movable() -> (
    None
):
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

    assert game_session._state.cursor == sq("g1")
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


def test_click_square_on_no_match_typed_draft_replaces_with_clicked_source_prefix() -> (
    None
):
    move_a = make("P", "e2", "e4")
    move_b = make("P", "e2", "e3")
    legal_moves = {move_a, move_b}
    fake_game = FakeGame(initial_moves=legal_moves)
    game_session = make_session(fake_game)

    game_session.set_move_text("zzzz")
    assert game_session._state.parse_result.status == "no_match"

    game_session.click_square(sq("e2"))

    snapshot = game_session.snapshot()

    assert game_session._state.cursor == sq("e2")
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


def test_click_square_game_over_only_updates_cursor_and_preserves_draft() -> None:
    move = make("P", "e2", "e4")
    fake_game = FakeGame(initial_moves={move}, outcome="1-0")
    game_session = make_session(fake_game)

    game_session._state.move_text = "Pe2-e4"
    game_session._state.parse_result = move_parser.parse("Pe2-e4", set())

    game_session.click_square(sq("e2"))

    assert game_session._state.cursor == sq("e2")
    assert game_session._state.move_text == "Pe2-e4"
    assert game_session._state.parse_result == move_parser.parse("Pe2-e4", set())
