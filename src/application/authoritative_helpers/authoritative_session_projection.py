from typing import cast

from src.application import viewer_types as vt
from src.application.helpers.move_parser import get_canonical, get_spellings
from src.engine.board import Piece, get_name, is_white
from src.engine.game import Game
from src.engine.moves import (
    Move,
    get_final_position,
    get_initial_position,
    get_promotion,
)
from src.shared.ids import LobbyId, PlayerId
from src.shared.protocol_types import ConnectionState, PlayerSide, PromotionPiece

from .authoritative_permissions import ViewerPermissions
from .authoritative_session_types import (
    CommittedSessionState,
    SessionPhase,
    TerminalState,
    TimeControl,
)
from .authoritative_timing import ClockState


class AuthoritativeSessionProjection:
    @staticmethod
    def snapshot(
        *,
        game: Game,
        phase: SessionPhase,
        state: CommittedSessionState,
        draw_offered_by: PlayerSide | None,
        clock_state: ClockState | None,
        time_control: TimeControl | None,
    ) -> vt.AuthoritativeSnapshot:
        check_square = game.checked_king_position()
        return vt.AuthoritativeSnapshot(
            board_glyphs=_build_board_glyphs(game),
            side_to_move=phase.side_to_move,
            last_move_from=state.last_move_from,
            last_move_to=state.last_move_to,
            check_square=check_square,
            move_list=move_history(game),
            draw_offered_by=draw_offered_by,
            is_player_checked=check_square is not None,
            is_game_over=phase.is_game_over,
            timed_game=_build_timed_game(clock_state, time_control),
            outcome=_build_outcome(phase.terminal),
            feedback=state.feedback,
        )

    @staticmethod
    def preview_hints(
        *,
        legal_moves: set[Move],
        phase: SessionPhase,
        current_ply: int,
        include_preview_hints: bool,
    ) -> vt.MovePreviewHints | None:
        if not include_preview_hints or phase.is_game_over:
            return None

        return vt.MovePreviewHints(
            base_ply=current_ply,
            legal_moves=sorted(
                (_build_preview_candidate(move, legal_moves) for move in legal_moves),
                key=lambda candidate: candidate.canonical_text,
            ),
        )

    @staticmethod
    def viewer_session_view(
        *,
        lobby_id: LobbyId,
        viewer_id: PlayerId,
        current_ply: int,
        connection_state: ConnectionState,
        status_text: str | None,
        permissions: ViewerPermissions,
        snapshot: vt.AuthoritativeSnapshot,
        preview_hints: vt.MovePreviewHints | None,
    ) -> vt.ViewerSessionView:
        return vt.ViewerSessionView(
            lobby_id=lobby_id,
            viewer_id=viewer_id,
            viewer_role=permissions.viewer_role,
            viewer_side=permissions.viewer_side,
            current_ply=current_ply,
            connection_state=connection_state,
            can_submit_for_side=permissions.can_submit_for_side,
            can_offer_draw=permissions.can_offer_draw,
            can_accept_draw=permissions.can_accept_draw,
            can_resign=permissions.can_resign,
            can_request_undo=permissions.can_request_undo,
            status_text=status_text,
            snapshot=snapshot,
            preview_hints=preview_hints,
        )


def move_history(game: Game) -> list[vt.MoveListItem]:
    return [
        vt.MoveListItem(ply=ply, notation=get_canonical(move))
        for ply, (move, _) in enumerate(game.moves_list, start=1)
    ]


def _build_board_glyphs(game: Game) -> list[list[str]]:
    def piece_to_glyph(piece: Piece | None) -> str:
        if piece is None:
            return "."
        name = get_name(piece)
        return name if is_white(piece) else name.lower()

    return [
        [piece_to_glyph(game.board.piece_at((file, rank))) for file in range(8)]
        for rank in range(7, -1, -1)
    ]


def _format_clock(ms: int) -> str:
    total_seconds = max(0, ms) // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02d}"


def _build_timed_game(
    clock_state: ClockState | None,
    time_control: TimeControl | None,
) -> vt.TimedGameView | None:
    if clock_state is None or time_control is None:
        return None

    return vt.TimedGameView(
        white=vt.ClockView(
            remaining_ms=clock_state.white_remaining_ms,
            display_text=_format_clock(clock_state.white_remaining_ms),
            is_active=clock_state.active_side == "white",
            is_flagged=clock_state.timeout_side == "white",
        ),
        black=vt.ClockView(
            remaining_ms=clock_state.black_remaining_ms,
            display_text=_format_clock(clock_state.black_remaining_ms),
            is_active=clock_state.active_side == "black",
            is_flagged=clock_state.timeout_side == "black",
        ),
        active_side=clock_state.active_side,
        timeout_side=clock_state.timeout_side,
        increment_seconds=time_control.increment_seconds,
    )


def _build_outcome(terminal: TerminalState | None) -> vt.OutcomeView | None:
    if terminal is None:
        return None

    if terminal.reason == "timeout":
        banner = (
            "Black wins on time."
            if terminal.winner == "black"
            else "White wins on time."
        )
    elif terminal.reason == "resignation":
        banner = (
            "White resigns. Black wins."
            if terminal.winner == "black"
            else "Black resigns. White wins."
        )
    elif terminal.reason == "draw":
        banner = "Draw."
    else:
        banner = (
            "White wins by checkmate."
            if terminal.winner == "white"
            else "Black wins by checkmate."
        )

    return vt.OutcomeView(
        winner=terminal.winner,
        reason=terminal.reason,
        banner=banner,
    )


def _build_preview_candidate(
    move: Move,
    legal_moves: set[Move],
) -> vt.MovePreviewCandidate:
    from_square = get_initial_position(move)
    to_square = get_final_position(move)
    promotion_piece = cast(PromotionPiece, get_promotion(move))

    return vt.MovePreviewCandidate(
        canonical_text=get_canonical(move),
        aliases=get_spellings(move, legal_moves),
        from_square=from_square,
        to_square=to_square,
        promotion_piece=promotion_piece,
        promotion_prompt_position=to_square if promotion_piece is not None else None,
    )
