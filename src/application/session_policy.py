from dataclasses import dataclass
from .move_parser import ParseResult
from .session_types import OpponentType, UndoScope


@dataclass(frozen=True)
class SessionCapabilities:
    """
    UI-facing action availability flags derived for the current session state.

    Each field indicates whether the corresponding action should currently be
    offered by the presentation layer.
    """

    can_confirm_move: bool
    can_undo_halfmove: bool
    can_undo_fullmove: bool
    can_resign: bool


class SessionPolicy:
    """
    Pure policy helpers for session-level action availability.

    `SessionPolicy` derives default undo scope and UI capability flags from
    opponent mode, move count, parse state, and whether the session is terminal.
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
    def can_confirm_move(parse_result: ParseResult, is_game_over: bool) -> bool:
        return parse_result.status == "resolved" and not is_game_over

    @staticmethod
    def can_resign(is_game_over: bool) -> bool:
        return not is_game_over

    @staticmethod
    def can_undo_halfmove(opponent: OpponentType, move_count: int) -> bool:
        return opponent == "local" and move_count > 0

    @staticmethod
    def can_undo_fullmove(opponent: OpponentType, move_count: int) -> bool:
        return opponent != "online" and move_count > 1

    @staticmethod
    def capabilities(
        opponent: OpponentType,
        move_count: int,
        parse_result: ParseResult,
        is_game_over: bool,
    ) -> SessionCapabilities:
        return SessionCapabilities(
            can_confirm_move=SessionPolicy.can_confirm_move(
                parse_result,
                is_game_over=is_game_over,
            ),
            can_undo_halfmove=SessionPolicy.can_undo_halfmove(
                opponent,
                move_count=move_count,
            ),
            can_undo_fullmove=SessionPolicy.can_undo_fullmove(
                opponent,
                move_count=move_count,
            ),
            can_resign=SessionPolicy.can_resign(is_game_over=is_game_over),
        )
