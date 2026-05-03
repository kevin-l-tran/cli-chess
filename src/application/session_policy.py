from .session_types import (
    OpponentType,
    ParseStatus,
    PlayerSide,
    SessionAvailability,
    SessionPhase,
    UndoScope,
)


class SessionPolicy:
    """
    Pure policy helpers for session-level UI availability and simple default choices.

    This module does not mutate session state, call the engine, set feedback, or
    return command failure statuses.
    """

    @staticmethod
    def resolve_undo_scope(
        opponent: OpponentType,
        requested: UndoScope | None,
    ) -> UndoScope | None:
        if opponent == "online":
            return None

        if requested == "halfmove":
            return "halfmove" if opponent == "local" else None

        if requested == "fullmove":
            return "fullmove"

        return "halfmove" if opponent == "local" else "fullmove"

    @staticmethod
    def can_confirm_move(parse_status: ParseStatus, phase: SessionPhase) -> bool:
        return parse_status == "resolved" and not phase.is_game_over

    @staticmethod
    def can_resign(phase: SessionPhase) -> bool:
        return not phase.is_game_over

    @staticmethod
    def can_undo_halfmove(opponent: OpponentType, move_count: int) -> bool:
        return opponent == "local" and move_count > 0

    @staticmethod
    def can_undo_fullmove(opponent: OpponentType, move_count: int) -> bool:
        return opponent != "online" and move_count > 1

    @staticmethod
    def can_offer_draw(
        opponent: OpponentType,
        phase: SessionPhase,
        draw_offered_by: PlayerSide | None,
    ) -> bool:
        return (
            opponent == "local" and not phase.is_game_over and draw_offered_by is None
        )

    @staticmethod
    def availability(
        opponent: OpponentType,
        move_count: int,
        parse_status: ParseStatus,
        phase: SessionPhase,
        draw_offered_by: PlayerSide | None,
    ) -> SessionAvailability:
        return SessionAvailability(
            can_confirm_move=SessionPolicy.can_confirm_move(
                parse_status,
                phase,
            ),
            can_offer_draw=SessionPolicy.can_offer_draw(
                opponent,
                phase,
                draw_offered_by,
            ),
            can_undo_halfmove=SessionPolicy.can_undo_halfmove(
                opponent,
                move_count,
            ),
            can_undo_fullmove=SessionPolicy.can_undo_fullmove(
                opponent,
                move_count,
            ),
            can_resign=SessionPolicy.can_resign(phase),
        )
