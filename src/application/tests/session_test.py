from collections.abc import Iterable

import pytest

from src.application.session_helpers.session_types import (
    SessionConfig,
    TimeControl,
)
from src.application.session import GameSession
from src.application.command_types import CommandResult
from src.application.move_parser import get_canonical
from src.engine.game import (
    GameConcludedError,
    IllegalMoveError,
    NoDrawOfferError,
)
from src.shared.ids import LobbyId, PlayerId, RequestId


LOCAL = PlayerId("local-controller")
WHITE = PlayerId("white-player")
BLACK = PlayerId("black-player")
SPECTATOR = PlayerId("spectator")


class FakeClock:
    def __init__(self, now_ms: int = 0) -> None:
        self.now_ms = now_ms

    def __call__(self) -> int:
        return self.now_ms

    def advance(self, delta_ms: int) -> None:
        self.now_ms += delta_ms


def req(value: str) -> RequestId:
    return RequestId(value)


def local_session() -> GameSession:
    return GameSession.local(lobby_id=LobbyId("local-test"))


def online_session() -> GameSession:
    return GameSession(
        SessionConfig(
            lobby_id=LobbyId("online-test"),
            mode="online",
        ),
        player_sides={
            WHITE: "white",
            BLACK: "black",
        },
    )


def canonical_legal_moves(session: GameSession) -> list[str]:
    return sorted(get_canonical(move) for move in session.legal_moves)


def first_legal_move_text(session: GameSession) -> str:
    moves = canonical_legal_moves(session)
    assert moves, "expected at least one legal move in an active session"
    return moves[0]


def submit_first_legal(
    session: GameSession,
    player_id: PlayerId,
    request_id: str,
    *,
    offer_draw: bool = False,
) -> tuple[CommandResult, str]:
    move_text = first_legal_move_text(session)
    result = session.submit_move(
        player_id,
        move_text,
        request_id=req(request_id),
        expected_ply=session.current_ply(),
        offer_draw=offer_draw,
    )
    return result, move_text


def assert_no_extra_moves(session: GameSession, expected_ply: int) -> None:
    assert session.current_ply() == expected_ply
    assert len(session.move_history) == expected_ply


def test_local_submit_legal_move_updates_committed_snapshot() -> None:
    session = local_session()

    result, move_text = submit_first_legal(session, LOCAL, "move-1")

    assert result.ok is True
    assert result.status == "accepted"
    assert result.message == f"Played {move_text}."
    assert_no_extra_moves(session, 1)
    assert result.view is not None
    assert result.view.current_ply == 1
    assert result.view.snapshot.side_to_move == "black"
    assert result.view.snapshot.last_move_from is not None
    assert result.view.snapshot.last_move_to is not None
    assert result.view.snapshot.move_list[-1].ply == 1
    assert result.view.snapshot.feedback is not None
    assert result.view.snapshot.feedback.kind == "action"
    assert result.view.snapshot.feedback.text == f"Played {move_text}."


def test_submit_empty_move_returns_validation_error_without_mutating() -> None:
    session = local_session()

    result = session.submit_move(
        LOCAL,
        "",
        request_id=req("empty-move"),
        expected_ply=session.current_ply(),
    )

    assert result.ok is False
    assert result.status == "invalid_move"
    assert result.message == "Enter a move first."
    assert_no_extra_moves(session, 0)
    assert result.view is not None
    assert result.view.current_ply == 0
    assert result.view.snapshot.feedback is not None
    assert result.view.snapshot.feedback.kind == "error"
    assert result.view.snapshot.feedback.text == "Enter a move first."


@pytest.mark.parametrize("move_text", ["not-a-move", "zzzz"])
def test_submit_unmatched_move_returns_invalid_move_without_mutating(
    move_text: str,
) -> None:
    session = local_session()

    result = session.submit_move(
        LOCAL,
        move_text,
        request_id=req(f"bad-{move_text}"),
        expected_ply=session.current_ply(),
    )

    assert result.ok is False
    assert result.status == "invalid_move"
    assert result.message == "No legal move matches the submitted text."
    assert_no_extra_moves(session, 0)


def test_submit_rejects_stale_expected_ply_as_viewer_specific_status() -> None:
    session = local_session()
    move_text = first_legal_move_text(session)

    result = session.submit_move(
        LOCAL,
        move_text,
        request_id=req("stale-ply"),
        expected_ply=session.current_ply() + 1,
    )

    assert result.ok is False
    assert result.status == "stale_position"
    assert result.message == "Position changed."
    assert_no_extra_moves(session, 0)
    assert result.view is not None
    assert result.view.status_text == "Position changed."
    # Stale-position feedback is command-local and should not become public game feedback.
    assert result.view.snapshot.feedback is None


def test_duplicate_submit_returns_cached_result_without_reapplying_move() -> None:
    session = local_session()
    move_text = first_legal_move_text(session)

    first = session.submit_move(
        LOCAL,
        move_text,
        request_id=req("same-request"),
        expected_ply=0,
    )
    duplicate = session.submit_move(
        LOCAL,
        move_text,
        request_id=req("same-request"),
        expected_ply=0,
    )

    assert first.ok is True
    assert duplicate.ok is True
    assert duplicate.status == "duplicate"
    assert duplicate.message == first.message
    assert_no_extra_moves(session, 1)
    assert duplicate.view is not None
    assert duplicate.view.current_ply == 1


def test_duplicate_request_id_with_different_payload_is_conflict() -> None:
    session = local_session()
    move_text = first_legal_move_text(session)

    first = session.submit_move(
        LOCAL,
        move_text,
        request_id=req("conflicting-request"),
        expected_ply=0,
    )
    conflict = session.submit_move(
        LOCAL,
        move_text,
        request_id=req("conflicting-request"),
        expected_ply=0,
        offer_draw=True,
    )

    assert first.ok is True
    assert conflict.ok is False
    assert conflict.status == "duplicate_conflict"
    assert conflict.message == "Request ID was already used for a different command."
    assert_no_extra_moves(session, 1)
    assert conflict.view is not None
    assert conflict.view.status_text == conflict.message


def test_online_only_side_to_move_can_submit() -> None:
    session = online_session()

    black_result, _ = submit_first_legal(session, BLACK, "black-too-early")
    white_result, _ = submit_first_legal(session, WHITE, "white-first")
    white_again, _ = submit_first_legal(session, WHITE, "white-again")
    black_result_after_white, _ = submit_first_legal(session, BLACK, "black-second")

    assert black_result.ok is False
    assert black_result.status == "not_your_turn"
    assert black_result.view is not None
    assert black_result.view.status_text == "Not your turn."

    assert white_result.ok is True
    assert white_again.ok is False
    assert white_again.status == "not_your_turn"
    assert black_result_after_white.ok is True
    assert_no_extra_moves(session, 2)


def test_spectator_cannot_submit_or_request_undo() -> None:
    session = online_session()

    submit_result, _ = submit_first_legal(session, SPECTATOR, "spectator-submit")
    undo_result = session.request_undo(SPECTATOR, request_id=req("spectator-undo"))

    assert submit_result.ok is False
    assert submit_result.status == "not_your_turn"
    assert submit_result.view is not None
    assert submit_result.view.viewer_role == "spectator"
    assert submit_result.view.can_submit_for_side is None

    assert undo_result.ok is False
    assert undo_result.status == "not_player"
    assert undo_result.message == "Only a player may request undo."
    assert undo_result.view is not None
    assert undo_result.view.status_text == undo_result.message
    assert_no_extra_moves(session, 0)


def test_snapshot_permissions_are_viewer_specific() -> None:
    session = online_session()

    white_view = session.snapshot_for(WHITE)
    black_view = session.snapshot_for(BLACK)
    spectator_view = session.snapshot_for(SPECTATOR)

    assert white_view.viewer_role == "white"
    assert white_view.viewer_side == "white"
    assert white_view.can_submit_for_side == "white"

    assert black_view.viewer_role == "black"
    assert black_view.viewer_side == "black"
    assert black_view.can_submit_for_side is None

    assert spectator_view.viewer_role == "spectator"
    assert spectator_view.viewer_side is None
    assert spectator_view.can_submit_for_side is None
    assert spectator_view.can_offer_draw is False
    assert spectator_view.can_accept_draw is False
    assert spectator_view.can_resign is False
    assert spectator_view.can_request_undo is False


def test_online_preview_hints_are_omitted_but_local_hints_are_available() -> None:
    local_view = local_session().snapshot_for(LOCAL)
    online_view = online_session().snapshot_for(WHITE)

    assert local_view.preview_hints is not None
    assert local_view.preview_hints.base_ply == local_view.current_ply
    assert local_view.preview_hints.legal_moves

    assert online_view.preview_hints is None


def test_draw_offer_and_acceptance_conclude_game() -> None:
    session = online_session()

    offer_result, _ = submit_first_legal(
        session,
        WHITE,
        "white-offers-draw",
        offer_draw=True,
    )
    accept_result = session.accept_draw_offer(
        BLACK,
        request_id=req("black-accepts-draw"),
        expected_ply=session.current_ply(),
    )

    assert offer_result.ok is True
    assert offer_result.message is not None
    assert offer_result.message.endswith("Draw offered.")
    assert offer_result.view is not None
    assert offer_result.view.snapshot.draw_offered_by == "white"

    assert accept_result.ok is True
    assert accept_result.status == "accepted"
    assert accept_result.message == "Draw offer accepted."
    assert accept_result.view is not None
    assert accept_result.view.snapshot.is_game_over is True
    assert accept_result.view.snapshot.outcome is not None
    assert accept_result.view.snapshot.outcome.reason == "draw"
    assert accept_result.view.snapshot.outcome.winner is None
    assert session.terminal_state is not None
    assert session.terminal_state.reason == "draw"
    assert not session.legal_moves


def test_draw_offer_cannot_be_accepted_by_offering_side() -> None:
    session = online_session()
    submit_first_legal(session, WHITE, "white-offers-draw", offer_draw=True)

    result = session.accept_draw_offer(
        WHITE,
        request_id=req("white-accepts-own-draw"),
        expected_ply=session.current_ply(),
    )

    assert result.ok is False
    assert result.status == "draw_unavailable"
    assert result.message == "No draw offer is available."
    assert result.view is not None
    assert result.view.snapshot.is_game_over is False
    assert result.view.snapshot.feedback is not None
    assert result.view.snapshot.feedback.kind == "error"


def test_accept_draw_without_offer_is_rejected() -> None:
    session = online_session()

    result = session.accept_draw_offer(
        WHITE,
        request_id=req("no-offer"),
        expected_ply=session.current_ply(),
    )

    assert result.ok is False
    assert result.status == "draw_unavailable"
    assert result.message == "No draw offer is available."
    assert_no_extra_moves(session, 0)


def test_resign_sets_terminal_state_and_blocks_later_moves() -> None:
    session = online_session()
    move_text = first_legal_move_text(session)

    resign_result = session.resign(WHITE, request_id=req("white-resigns"))
    blocked_move = session.submit_move(
        BLACK,
        move_text,
        request_id=req("move-after-resign"),
        expected_ply=session.current_ply(),
    )

    assert resign_result.ok is True
    assert resign_result.status == "accepted"
    assert resign_result.message == "White resigns."
    assert resign_result.view is not None
    assert resign_result.view.snapshot.is_game_over is True
    assert resign_result.view.snapshot.outcome is not None
    assert resign_result.view.snapshot.outcome.reason == "resignation"
    assert resign_result.view.snapshot.outcome.winner == "black"
    assert session.terminal_state is not None
    assert session.terminal_state.reason == "resignation"
    assert session.terminal_state.winner == "black"

    assert blocked_move.ok is False
    assert blocked_move.status == "game_over"
    assert blocked_move.message == "Game has concluded."
    assert_no_extra_moves(session, 0)


def test_resign_is_limited_to_side_to_move() -> None:
    session = online_session()

    result = session.resign(BLACK, request_id=req("black-resigns-too-early"))

    assert result.ok is False
    assert result.status == "not_your_turn"
    assert result.message == "Resignation is currently limited to the side to move."
    assert result.view is not None
    assert result.view.status_text == result.message
    assert result.view.snapshot.feedback is None
    assert_no_extra_moves(session, 0)


def test_local_undo_halfmove_removes_last_move() -> None:
    session = local_session()
    submit_first_legal(session, LOCAL, "move-1")
    submit_first_legal(session, LOCAL, "move-2")

    result = session.request_undo(
        LOCAL,
        request_id=req("undo-halfmove"),
        scope="halfmove",
    )

    assert result.ok is True
    assert result.status == "accepted"
    assert result.message == "Move undone."
    assert_no_extra_moves(session, 1)
    assert result.view is not None
    assert result.view.current_ply == 1
    assert result.view.snapshot.feedback is not None
    assert result.view.snapshot.feedback.kind == "action"
    assert result.view.snapshot.feedback.text == "Move undone."


def test_local_undo_fullmove_removes_last_two_halfmoves() -> None:
    session = local_session()
    submit_first_legal(session, LOCAL, "move-1")
    submit_first_legal(session, LOCAL, "move-2")

    result = session.request_undo(
        LOCAL,
        request_id=req("undo-fullmove"),
        scope="fullmove",
    )

    assert result.ok is True
    assert result.status == "accepted"
    assert result.message == "Turn undone."
    assert_no_extra_moves(session, 0)
    assert result.view is not None
    assert result.view.snapshot.side_to_move == "white"


def test_undo_without_enough_moves_is_rejected_without_mutating() -> None:
    session = local_session()

    no_move_result = session.request_undo(
        LOCAL,
        request_id=req("undo-empty"),
        scope="halfmove",
    )
    submit_first_legal(session, LOCAL, "move-1")
    one_halfmove_result = session.request_undo(
        LOCAL,
        request_id=req("undo-one-halfmove-as-fullmove"),
        scope="fullmove",
    )

    assert no_move_result.ok is False
    assert no_move_result.status == "undo_unavailable"
    assert no_move_result.message == "No move to undo."

    assert one_halfmove_result.ok is False
    assert one_halfmove_result.status == "undo_unavailable"
    assert one_halfmove_result.message == "No move to undo."
    assert_no_extra_moves(session, 1)


def test_online_undo_is_rejected_by_policy() -> None:
    session = online_session()

    result = session.request_undo(
        WHITE,
        request_id=req("online-undo"),
        scope="fullmove",
    )

    assert result.ok is False
    assert result.status == "undo_unavailable"
    assert result.message == "Can't undo in an online game."
    assert result.view is not None
    assert result.view.snapshot.feedback is not None
    assert result.view.snapshot.feedback.kind == "error"
    assert result.view.snapshot.feedback.text == "Can't undo in an online game."
    assert_no_extra_moves(session, 0)


def test_command_results_always_include_view_for_handled_commands() -> None:
    session = online_session()
    move_text = first_legal_move_text(session)

    results: Iterable[CommandResult] = (
        session.submit_move(
            BLACK,
            move_text,
            request_id=req("wrong-turn"),
            expected_ply=session.current_ply(),
        ),
        session.accept_draw_offer(
            WHITE,
            request_id=req("draw-without-offer"),
            expected_ply=session.current_ply(),
        ),
        session.request_undo(WHITE, request_id=req("online-undo-no-view-loss")),
        session.resign(WHITE, request_id=req("resign-with-view")),
    )

    for result in results:
        assert result.view is not None


def test_submit_ambiguous_move_returns_ambiguous_move_without_mutating() -> None:
    session = local_session()

    result = session.submit_move(
        LOCAL,
        "Pe2",
        request_id=req("ambiguous-move"),
        expected_ply=session.current_ply(),
    )

    assert result.ok is False
    assert result.status == "ambiguous_move"
    assert result.message == "Move is ambiguous."
    assert_no_extra_moves(session, 0)
    assert result.view is not None
    assert result.view.current_ply == 0


def test_submit_move_maps_illegal_move_error_without_mutating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = local_session()
    move_text = first_legal_move_text(session)

    def raise_illegal(*args: object, **kwargs: object) -> None:
        raise IllegalMoveError("illegal move")

    monkeypatch.setattr(session.game, "make_move", raise_illegal)

    result = session.submit_move(
        LOCAL,
        move_text,
        request_id=req("engine-illegal"),
        expected_ply=session.current_ply(),
    )

    assert result.ok is False
    assert result.status == "invalid_move"
    assert result.message == "Could not apply illegal move."
    assert_no_extra_moves(session, 0)
    assert result.view is not None
    assert result.view.snapshot.feedback is not None
    assert result.view.snapshot.feedback.kind == "error"
    assert result.view.snapshot.feedback.text == "Could not apply illegal move."


def test_submit_move_maps_engine_game_concluded_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = local_session()
    move_text = first_legal_move_text(session)

    def raise_game_concluded(*args: object, **kwargs: object) -> None:
        raise GameConcludedError("1-0")

    monkeypatch.setattr(session.game, "make_move", raise_game_concluded)

    result = session.submit_move(
        LOCAL,
        move_text,
        request_id=req("engine-game-over"),
        expected_ply=session.current_ply(),
    )

    assert result.ok is False
    assert result.status == "game_over"
    assert result.message == "Game has concluded."
    assert_no_extra_moves(session, 0)


def test_submit_move_maps_unexpected_engine_error_without_mutating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = local_session()
    move_text = first_legal_move_text(session)

    def raise_unexpected(*args: object, **kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(session.game, "make_move", raise_unexpected)

    result = session.submit_move(
        LOCAL,
        move_text,
        request_id=req("engine-boom"),
        expected_ply=session.current_ply(),
    )

    assert result.ok is False
    assert result.status == "error"
    assert result.message == "Could not apply move."
    assert_no_extra_moves(session, 0)
    assert result.view is not None
    assert result.view.snapshot.feedback is not None
    assert result.view.snapshot.feedback.text == "Could not apply move."


def test_non_offer_reply_clears_pending_draw_offer() -> None:
    session = online_session()

    offer_result, _ = submit_first_legal(
        session,
        WHITE,
        "white-offers-draw-for-decline",
        offer_draw=True,
    )
    reply_result, _ = submit_first_legal(
        session,
        BLACK,
        "black-declines-by-moving",
    )

    assert offer_result.ok is True
    assert reply_result.ok is True
    assert reply_result.view is not None
    assert reply_result.view.snapshot.draw_offered_by is None
    assert_no_extra_moves(session, 2)


def test_cannot_counter_offer_while_draw_offer_is_pending() -> None:
    session = online_session()

    offer_result, _ = submit_first_legal(
        session,
        WHITE,
        "white-offers-draw-before-counter",
        offer_draw=True,
    )
    counter_result, _ = submit_first_legal(
        session,
        BLACK,
        "black-counter-offer",
        offer_draw=True,
    )

    assert offer_result.ok is True
    assert counter_result.ok is False
    assert counter_result.status == "draw_unavailable"
    assert counter_result.message == "Draw offers are not available."
    assert counter_result.view is not None
    assert counter_result.view.snapshot.draw_offered_by == "white"
    assert_no_extra_moves(session, 1)


def test_accept_draw_offer_maps_engine_no_offer_to_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = online_session()
    submit_first_legal(
        session, WHITE, "white-offers-before-engine-no-offer", offer_draw=True
    )

    def raise_no_draw_offer() -> None:
        raise NoDrawOfferError(None)

    monkeypatch.setattr(session.game, "accept_draw", raise_no_draw_offer)

    result = session.accept_draw_offer(
        BLACK,
        request_id=req("black-accepts-engine-no-offer"),
        expected_ply=session.current_ply(),
    )

    assert result.ok is False
    assert result.status == "draw_unavailable"
    assert result.message == "No draw offer is available."
    assert result.view is not None
    assert result.view.snapshot.is_game_over is False


def test_accept_draw_offer_maps_engine_game_concluded_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = online_session()
    submit_first_legal(
        session, WHITE, "white-offers-before-engine-game-over", offer_draw=True
    )

    def raise_game_concluded() -> None:
        raise GameConcludedError("1-0")

    monkeypatch.setattr(session.game, "accept_draw", raise_game_concluded)

    result = session.accept_draw_offer(
        BLACK,
        request_id=req("black-accepts-engine-game-over"),
        expected_ply=session.current_ply(),
    )

    assert result.ok is False
    assert result.status == "game_over"
    assert result.message == "Game has concluded."


def test_accept_draw_offer_maps_unexpected_engine_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = online_session()
    submit_first_legal(
        session, WHITE, "white-offers-before-engine-error", offer_draw=True
    )

    def raise_unexpected() -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(session.game, "accept_draw", raise_unexpected)

    result = session.accept_draw_offer(
        BLACK,
        request_id=req("black-accepts-engine-error"),
        expected_ply=session.current_ply(),
    )

    assert result.ok is False
    assert result.status == "error"
    assert result.message == "Could not accept draw offer."
    assert result.view is not None
    assert result.view.snapshot.feedback is not None
    assert result.view.snapshot.feedback.text == "Could not accept draw offer."


def test_black_resignation_sets_white_winner_and_preserves_last_move_highlight() -> (
    None
):
    session = online_session()
    white_move_result, _ = submit_first_legal(
        session, WHITE, "white-moves-before-black-resigns"
    )
    assert white_move_result.view is not None
    last_move_from = white_move_result.view.snapshot.last_move_from
    last_move_to = white_move_result.view.snapshot.last_move_to

    result = session.resign(BLACK, request_id=req("black-resigns-after-white-move"))

    assert result.ok is True
    assert result.status == "accepted"
    assert result.message == "Black resigns."
    assert result.view is not None
    assert result.view.snapshot.is_game_over is True
    assert result.view.snapshot.outcome is not None
    assert result.view.snapshot.outcome.reason == "resignation"
    assert result.view.snapshot.outcome.winner == "white"
    assert result.view.snapshot.last_move_from == last_move_from
    assert result.view.snapshot.last_move_to == last_move_to
    assert_no_extra_moves(session, 1)


def test_resign_maps_engine_game_concluded_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = online_session()

    def raise_game_concluded() -> None:
        raise GameConcludedError("1-0")

    monkeypatch.setattr(session.game, "resign", raise_game_concluded)

    result = session.resign(WHITE, request_id=req("resign-engine-game-over"))

    assert result.ok is False
    assert result.status == "game_over"
    assert result.message == "Game has concluded."
    assert_no_extra_moves(session, 0)


def test_resign_maps_unexpected_engine_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = online_session()

    def raise_unexpected() -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(session.game, "resign", raise_unexpected)

    result = session.resign(WHITE, request_id=req("resign-engine-error"))

    assert result.ok is False
    assert result.status == "error"
    assert result.message == "Could not resign game."
    assert result.view is not None
    assert result.view.snapshot.feedback is not None
    assert result.view.snapshot.feedback.text == "Could not resign game."
    assert_no_extra_moves(session, 0)


def test_halfmove_undo_rewinds_last_move_highlight_to_previous_move() -> None:
    session = local_session()
    first_result, _ = submit_first_legal(session, LOCAL, "highlight-move-1")
    assert first_result.view is not None
    first_last_move_from = first_result.view.snapshot.last_move_from
    first_last_move_to = first_result.view.snapshot.last_move_to

    submit_first_legal(session, LOCAL, "highlight-move-2")

    undo_result = session.request_undo(
        LOCAL,
        request_id=req("highlight-undo-halfmove"),
        scope="halfmove",
    )

    assert undo_result.ok is True
    assert undo_result.view is not None
    assert undo_result.view.current_ply == 1
    assert undo_result.view.snapshot.last_move_from == first_last_move_from
    assert undo_result.view.snapshot.last_move_to == first_last_move_to


def test_request_undo_maps_unexpected_engine_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = local_session()
    submit_first_legal(session, LOCAL, "undo-error-move")

    def raise_unexpected() -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(session.game, "undo_halfmove", raise_unexpected)

    result = session.request_undo(
        LOCAL,
        request_id=req("undo-engine-error"),
        scope="halfmove",
    )

    assert result.ok is False
    assert result.status == "error"
    assert result.message == "Could not undo move."
    assert_no_extra_moves(session, 1)
    assert result.view is not None
    assert result.view.snapshot.feedback is not None
    assert result.view.snapshot.feedback.text == "Could not undo move."


def test_untimed_snapshot_exposes_no_timing_view() -> None:
    view = local_session().snapshot_for(LOCAL)

    assert view.snapshot.timed_game is None


def test_timed_snapshot_projects_initial_clock_data() -> None:
    clock = FakeClock(0)
    session = GameSession.local(
        lobby_id=LobbyId("timed-initial"),
        time_control=TimeControl(initial_seconds=60, increment_seconds=2),
        time_source=clock,
    )

    view = session.snapshot_for(LOCAL)

    assert view.snapshot.timed_game is not None
    timed = view.snapshot.timed_game
    assert timed.white.remaining_ms == 60_000
    assert timed.black.remaining_ms == 60_000
    assert timed.white.display_text == "1:00"
    assert timed.black.display_text == "1:00"
    assert timed.white.is_active is True
    assert timed.black.is_active is False
    assert timed.active_side == "white"
    assert timed.timeout_side is None
    assert timed.increment_seconds == 2


def test_timed_snapshot_advances_active_clock() -> None:
    clock = FakeClock(0)
    session = GameSession.local(
        lobby_id=LobbyId("timed-advance"),
        time_control=TimeControl(initial_seconds=60, increment_seconds=0),
        time_source=clock,
    )

    clock.advance(5_000)
    view = session.snapshot_for(LOCAL)

    assert view.snapshot.timed_game is not None
    timed = view.snapshot.timed_game
    assert timed.white.remaining_ms == 55_000
    assert timed.black.remaining_ms == 60_000
    assert timed.white.display_text == "0:55"
    assert timed.black.display_text == "1:00"
    assert timed.white.is_active is True
    assert timed.black.is_active is False


def test_submit_move_applies_increment_and_switches_active_side() -> None:
    clock = FakeClock(0)
    session = GameSession.local(
        lobby_id=LobbyId("timed-submit"),
        time_control=TimeControl(initial_seconds=30, increment_seconds=2),
        time_source=clock,
    )
    move_text = first_legal_move_text(session)

    clock.advance(5_000)
    result = session.submit_move(
        LOCAL,
        move_text,
        request_id=req("timed-move"),
        expected_ply=session.current_ply(),
    )

    assert result.ok is True
    assert result.view is not None
    assert result.view.snapshot.timed_game is not None
    timed = result.view.snapshot.timed_game
    assert timed.white.remaining_ms == 27_000
    assert timed.black.remaining_ms == 30_000
    assert timed.white.display_text == "0:27"
    assert timed.black.display_text == "0:30"
    assert timed.white.is_active is False
    assert timed.black.is_active is True
    assert timed.active_side == "black"


def test_timeout_blocks_submit_and_sets_terminal_state() -> None:
    clock = FakeClock(0)
    session = GameSession.local(
        lobby_id=LobbyId("timed-timeout"),
        time_control=TimeControl(initial_seconds=5, increment_seconds=0),
        time_source=clock,
    )
    move_text = first_legal_move_text(session)

    clock.advance(5_000)
    result = session.submit_move(
        LOCAL,
        move_text,
        request_id=req("timed-timeout-submit"),
        expected_ply=session.current_ply(),
    )

    assert result.ok is False
    assert result.status == "game_over"
    assert result.message == "Game has concluded."
    assert_no_extra_moves(session, 0)
    assert result.view is not None
    assert result.view.snapshot.outcome is not None
    assert result.view.snapshot.outcome.reason == "timeout"
    assert result.view.snapshot.outcome.winner == "black"
    assert result.view.snapshot.timed_game is not None
    timed = result.view.snapshot.timed_game
    assert timed.white.remaining_ms == 0
    assert timed.black.remaining_ms == 5_000
    assert timed.white.is_flagged is True
    assert timed.black.is_flagged is False
    assert timed.active_side is None
    assert timed.timeout_side == "white"


def test_undo_after_timeout_restores_clock_state() -> None:
    clock = FakeClock(0)
    session = GameSession.local(
        lobby_id=LobbyId("timed-undo-timeout"),
        time_control=TimeControl(initial_seconds=5, increment_seconds=0),
        time_source=clock,
    )
    move_text = first_legal_move_text(session)

    clock.advance(1_000)
    applied = session.submit_move(
        LOCAL,
        move_text,
        request_id=req("timed-move-before-timeout"),
        expected_ply=session.current_ply(),
    )
    assert applied.ok is True

    clock.advance(6_000)
    timeout_view = session.snapshot_for(LOCAL)
    assert timeout_view.snapshot.outcome is not None
    assert timeout_view.snapshot.outcome.reason == "timeout"
    assert timeout_view.snapshot.outcome.winner == "white"

    undo_result = session.request_undo(
        LOCAL,
        request_id=req("timed-undo-after-timeout"),
        scope="halfmove",
    )

    assert undo_result.ok is True
    assert undo_result.view is not None
    assert undo_result.view.snapshot.outcome is None
    assert undo_result.view.snapshot.timed_game is not None
    restored = undo_result.view.snapshot.timed_game
    assert restored.white.remaining_ms == 4_000
    assert restored.black.remaining_ms == 5_000
    assert restored.white.is_active is True
    assert restored.black.is_active is False
    assert restored.active_side == "white"
    assert restored.timeout_side is None
