from dataclasses import dataclass
from typing import Literal

from .move_parser import ParseStatus


Square = tuple[int, int]
PlayerSide = Literal["white", "black"]
OpponentType = Literal["local", "bot"]
MoveAttemptStatus = Literal[
    "applied",
    "empty",
    "no_match",
    "ambiguous",
    "illegal",
    "game_over",
    "error",
]
UndoStatus = Literal["undone", "unavailable", "error"]
UndoScope = Literal["halfmove", "fullmove"]
ResignStatus = Literal["resigned", "game_over", "error"]


@dataclass(frozen=True)
class TimeControl:
    initial_seconds: int
    increment_seconds: int = 0


@dataclass(frozen=True)
class SessionConfig:
    """
    Startup configuration for a local chess session.

    Attributes:
        player_side (PlayerSide):
            Which side the human player is considered to control. This can be
            used for turn/AI behavior.

        opponent (OpponentType):
            The type of opponent for the session. "local" means two players on
            the same client. "bot" reserves the shape needed for future engine
            integration.

        time_control (TimeControl | None):
            Optional chess clock settings for the session. None means untimed.
    """

    player_side: PlayerSide
    opponent: OpponentType = "local"
    time_control: TimeControl | None = None


@dataclass(frozen=True)
class MoveListItem:
    ply: int
    notation: str


@dataclass(frozen=True)
class MoveDraftView:
    text: str
    status: ParseStatus
    canonical_text: str | None


@dataclass(frozen=True)
class Snapshot:
    """
    Render-ready view of the current session state.

    Attributes:
        board_glyphs (list[list[str]]):
            8x8 matrix of piece/empty-square glyphs in board order for rendering.

        side_to_move (PlayerSide):
            The side whose turn it is in the current position.

        candidate_moves (set[tuple[Square, Square]]):
            The set of (initial position, final position) tuples that should be highlighted.

        last_move_from (Square | None):
            Origin square of the most recently applied move, if available.

        last_move_to (Square | None):
            Destination square of the most recently applied move, if available.

        move_list (list[MoveListItem]):
            Render-friendly move history entries for the sidebar or move panel.

        move_draft (MoveDraftView):
            Render-friendly object containing the player's move string, it's parse result,
            and a legal matching canonical move string, if it resolves to one.

        move_autocompletions (list[str]):
            A list of autocomplete-ready move strings that share the same prefix as
            the player's inputted move string.

        promotion_prompt_position (Square | None):
            The destination square of the promoting pawn. Used to anchor the promotion popup.

        is_checked (bool):
            Whether the current side is checked by the opponent.

        check_square (Square | None):
            Square of the king currently in check, if any. Useful for danger
            highlighting in the UI.

        outcome_banner (str | None):
            Final game result text to display prominently when the game has ended,
            such as checkmate, resignation, or draw.

        last_error_message (str | None):
            Most recent user-facing action failure message, such as an illegal
            move reason. None when there is no active error to show.

        last_action_message (str | None):
            The most recent user-facing action message produced by the
            session, such as an applied-move or undone-move message.
            `None` means there is no active action to display.
    """

    board_glyphs: list[list[str]]
    side_to_move: PlayerSide
    candidate_moves: set[tuple[Square, Square]]

    last_move_from: Square | None
    last_move_to: Square | None

    move_list: list[MoveListItem]
    move_draft: MoveDraftView
    move_autocompletions: list[str]
    promotion_prompt_position: Square | None

    check_square: Square | None

    is_opponent_checked: bool
    is_game_over: bool
    can_confirm_move: bool
    can_undo: bool
    can_resign: bool
    is_promotion_pending: bool
    default_undo_scope: UndoScope

    outcome_banner: str | None
    last_error_message: str | None
    last_action_message: str | None


@dataclass(frozen=True)
class MoveAttemptResult:
    ok: bool
    status: MoveAttemptStatus
    message: str | None


@dataclass(frozen=True)
class UndoResult:
    ok: bool
    status: UndoStatus
    message: str | None


@dataclass(frozen=True)
class ResignResult:
    ok: bool
    status: ResignStatus
    message: str | None
