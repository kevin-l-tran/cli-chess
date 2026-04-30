from dataclasses import dataclass
from .move_parser import ParseResult
from .session_types import OpponentType, UndoScope


@dataclass(frozen=True)
class SessionCapabilities:
    can_confirm_move: bool
    can_undo_halfmove: bool
    can_undo_fullmove: bool
    can_resign: bool


class SessionPolicy:
    @staticmethod
    def resolve_undo_scope(
        opponent: OpponentType,
        requested: UndoScope | None,
    ) -> UndoScope | None:
        if opponent == "online":
            return None
        if requested is not None:
            return requested
        return "fullmove" if opponent == "bot" else "halfmove"

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
