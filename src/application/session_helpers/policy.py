from src.shared.protocol_types import GameMode, PlayerSide

from .session_types import SessionPhase, UndoScope


class SessionPolicy:
    @staticmethod
    def resolve_undo_scope(mode: GameMode, requested: UndoScope | None) -> UndoScope | None:
        if mode == "online":
            return None
        if requested == "halfmove":
            return "halfmove" if mode == "local" else None
        if requested == "fullmove":
            return "fullmove"
        return "halfmove" if mode == "local" else "fullmove"

    @staticmethod
    def can_resign(phase: SessionPhase) -> bool:
        return not phase.is_game_over

    @staticmethod
    def can_undo_halfmove(mode: GameMode, move_count: int) -> bool:
        return mode == "local" and move_count > 0

    @staticmethod
    def can_undo_fullmove(mode: GameMode, move_count: int) -> bool:
        return mode != "online" and move_count > 1

    @staticmethod
    def can_offer_draw(
        mode: GameMode,
        phase: SessionPhase,
        draw_offered_by: PlayerSide | None,
    ) -> bool:
        return (
            mode in ("local", "online")
            and not phase.is_game_over
            and draw_offered_by is None
        )
