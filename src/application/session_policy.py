from .session_types import (
    OpponentType,
    ParseStatus,
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
    def availability(
        opponent: OpponentType,
        move_count: int,
        parse_status: ParseStatus,
        phase: SessionPhase,
    ) -> SessionAvailability:
        return SessionAvailability(
            can_confirm_move=SessionPolicy.can_confirm_move(
                parse_status=parse_status,
                phase=phase,
            ),
            can_undo_halfmove=SessionPolicy.can_undo_halfmove(
                opponent=opponent,
                move_count=move_count,
            ),
            can_undo_fullmove=SessionPolicy.can_undo_fullmove(
                opponent=opponent,
                move_count=move_count,
            ),
            can_resign=SessionPolicy.can_resign(phase=phase),
        )