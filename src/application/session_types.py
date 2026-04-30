from dataclasses import dataclass
from typing import Literal

from .move_parser import ParseStatus


Square = tuple[int, int]

PlayerSide = Literal["white", "black"]
OpponentType = Literal["local", "bot", "online"]
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
    Startup configuration for a chess session.

    Attributes:
        player_side (PlayerSide):
            Which side the human player is considered to control. This can be
            used for turn ownership, board orientation, and future AI or network
            behavior.

        opponent (OpponentType):
            The type of opponent for the session.

            - "local": two players share the same client
            - "bot": a local human plays against an engine-controlled opponent
            - "online": a local human plays a remote opponent; some local-only
            controls such as undo may be unavailable

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
            The set of `(initial position, final position)` tuples that should be
            highlighted as parser-matched candidate moves.

        last_move_from (Square | None):
            Origin square of the most recently applied move, if available.

        last_move_to (Square | None):
            Destination square of the most recently applied move, if available.

        move_list (list[MoveListItem]):
            Render-friendly move history entries for the sidebar or move panel.

        move_draft (MoveDraftView):
            Render-friendly object containing the player's draft text, its parse
            status, and the canonical move text when the draft uniquely resolves.

        move_autocompletions (list[str]):
            Autocomplete-ready move strings that share the same prefix as the
            current draft text.

        promotion_prompt_position (Square | None):
            The destination square of the promoting pawn. Used to anchor the
            promotion picker when the remaining ambiguity is only the promotion
            piece choice.

        check_square (Square | None):
            Square of the current player's king when that side is in check, if any.

        is_player_checked (bool):
            Whether the side to move is currently in check.

        is_game_over (bool):
            Whether the game has concluded.

        can_confirm_move (bool):
            Whether the current draft uniquely resolves to a legal move and can be
            confirmed.

        can_undo_fullmove (bool):
            Whether a fullmove undo is currently available. A fullmove undo removes
            two plies as a turn pair.

        can_undo_halfmove (bool):
            Whether a halfmove undo is currently available. A halfmove undo removes
            one ply.

        can_resign (bool):
            Whether resigning is currently available.

        is_promotion_pending (bool):
            Whether the current draft is waiting for the user to choose a
            promotion piece.

        outcome_banner (str | None):
            Final game result text to display prominently when the game has ended,
            such as resignation or draw.

        last_error_message (str | None):
            Most recent user-facing action failure message. None when there is no
            active error to show.

        last_action_message (str | None):
            Most recent user-facing success or action message. None when there is
            no active action message to show.
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

    is_player_checked: bool
    is_game_over: bool
    can_confirm_move: bool
    can_undo_fullmove: bool
    can_undo_halfmove: bool
    can_resign: bool
    is_promotion_pending: bool

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
