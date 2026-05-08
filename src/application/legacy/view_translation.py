from typing import cast

from src.application import viewer_types as vt
from src.application.legacy import session_types as legacy
from src.shared.ids import LobbyId, PlayerId


def current_ply_from_snapshot(snapshot: legacy.Snapshot) -> int:
    if not snapshot.move_list:
        return 0
    return snapshot.move_list[-1].ply


def authoritative_snapshot_from_legacy(
    snapshot: legacy.Snapshot,
) -> vt.AuthoritativeSnapshot:
    return vt.AuthoritativeSnapshot(
        board_glyphs=snapshot.board_glyphs,
        board_squares=None,
        side_to_move=snapshot.side_to_move,
        last_move_from=snapshot.last_move_from,
        last_move_to=snapshot.last_move_to,
        check_square=snapshot.check_square,
        move_list=[
            vt.MoveListItem(ply=item.ply, notation=item.notation)
            for item in snapshot.move_list
        ],
        draw_offered_by=snapshot.draw_offered_by,
        is_player_checked=snapshot.is_player_checked,
        is_game_over=snapshot.is_game_over,
        timed_game=_timed_game_from_legacy(snapshot.timed_game),
        outcome=_outcome_from_legacy(snapshot.outcome),
        feedback=_feedback_from_legacy(snapshot.feedback),
    )


def local_draft_from_legacy_snapshot(
    snapshot: legacy.Snapshot,
) -> vt.LocalDraftView:
    draft = snapshot.move_draft
    submit_text = draft.canonical_text or draft.text

    return vt.LocalDraftView(
        text=draft.text,
        status=cast(vt.DraftStatus, draft.status),
        canonical_text=draft.canonical_text,
        base_ply=current_ply_from_snapshot(snapshot),
        candidate_moves=snapshot.candidate_moves,
        autocompletions=snapshot.move_autocompletions,
        promotion_prompt_position=snapshot.promotion_prompt_position,
        is_promotion_pending=snapshot.is_promotion_pending,
        submit_text=submit_text if submit_text.strip() else None,
    )


def viewer_view_from_legacy_snapshot(
    snapshot: legacy.Snapshot,
    lobby_id: LobbyId,
    viewer_id: PlayerId,
) -> vt.ViewerSessionView:
    current_ply = current_ply_from_snapshot(snapshot)

    return vt.ViewerSessionView(
        lobby_id=lobby_id,
        viewer_id=viewer_id,
        viewer_role="local_controller",
        viewer_side=None,
        current_ply=current_ply,
        last_event_seq=current_ply,
        connection_state="connected",
        # This means "the viewer may submit a move in this position",
        # not "the current draft is resolved".
        can_submit_move=not snapshot.is_game_over and snapshot.side_to_move is not None,
        can_submit_for_side=snapshot.side_to_move,
        can_offer_draw=snapshot.can_offer_draw,
        can_accept_draw=(
            snapshot.draw_offered_by is not None and not snapshot.is_game_over
        ),
        can_resign=snapshot.can_resign,
        can_request_undo=snapshot.can_undo_halfmove or snapshot.can_undo_fullmove,
        can_spectate=False,
        status_text=None,
        snapshot=authoritative_snapshot_from_legacy(snapshot),
        # The legacy draft adapter reads preview state directly from GameSession,
        # so this can stay empty during the bridge phase.
        preview_hints=None,
    )


def _timed_game_from_legacy(
    timed_game: legacy.TimedGameView | None,
) -> vt.TimedGameView | None:
    if timed_game is None:
        return None

    return vt.TimedGameView(
        white=_clock_from_legacy(timed_game.white),
        black=_clock_from_legacy(timed_game.black),
        active_side=timed_game.active_side,
        timeout_side=timed_game.timeout_side,
        increment_seconds=timed_game.increment_seconds,
    )


def _clock_from_legacy(clock: legacy.ClockView) -> vt.ClockView:
    return vt.ClockView(
        remaining_ms=clock.remaining_ms,
        display_text=clock.display_text,
        is_active=clock.is_active,
        is_flagged=clock.is_flagged,
    )


def _outcome_from_legacy(
    outcome: legacy.OutcomeView | None,
) -> vt.OutcomeView | None:
    if outcome is None:
        return None

    return vt.OutcomeView(
        winner=outcome.winner,
        reason=cast(vt.TerminalReason, outcome.reason),
        banner=outcome.banner,
    )


def _feedback_from_legacy(
    feedback: legacy.FeedbackView | None,
) -> vt.FeedbackView | None:
    if feedback is None:
        return None

    return vt.FeedbackView(
        kind=cast(vt.FeedbackKind, feedback.kind),
        text=feedback.text,
    )
