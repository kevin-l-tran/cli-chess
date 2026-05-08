from dataclasses import dataclass
from typing import Literal

from src.shared.ids import LobbyId, PlayerId
from src.shared.protocol_types import (
    ConnectionState,
    ParticipantRole,
    PlayerSide,
    PromotionPiece,
    Square,
)

DraftStatus = Literal[
    "empty",
    "unvalidated",
    "no_match",
    "ambiguous",
    "resolved",
    "stale",
]

TerminalReason = Literal[
    "draw",
    "timeout",
    "checkmate",
    "resignation",
]

FeedbackKind = Literal[
    "error",
    "action",
    "info",
]


@dataclass(frozen=True)
class MoveListItem:
    ply: int
    notation: str


@dataclass(frozen=True)
class ClockView:
    remaining_ms: int
    display_text: str
    is_active: bool
    is_flagged: bool


@dataclass(frozen=True)
class TimedGameView:
    white: ClockView
    black: ClockView
    active_side: PlayerSide | None
    timeout_side: PlayerSide | None
    increment_seconds: int


@dataclass(frozen=True)
class OutcomeView:
    winner: PlayerSide | None
    reason: TerminalReason
    banner: str


@dataclass(frozen=True)
class FeedbackView:
    kind: FeedbackKind
    text: str


@dataclass(frozen=True)
class AuthoritativeSnapshot:
    board_glyphs: list[list[str]]

    side_to_move: PlayerSide | None
    last_move_from: Square | None
    last_move_to: Square | None
    check_square: Square | None

    move_list: list[MoveListItem]

    draw_offered_by: PlayerSide | None
    is_player_checked: bool
    is_game_over: bool

    timed_game: TimedGameView | None
    outcome: OutcomeView | None
    feedback: FeedbackView | None


@dataclass(frozen=True)
class MovePreviewCandidate:
    canonical_text: str
    aliases: set[str]
    from_square: Square
    to_square: Square
    promotion_piece: PromotionPiece | None = None
    promotion_prompt_position: Square | None = None


@dataclass(frozen=True)
class MovePreviewHints:
    base_ply: int
    legal_moves: list[MovePreviewCandidate]


@dataclass(frozen=True)
class LocalDraftView:
    text: str
    status: DraftStatus
    canonical_text: str | None

    candidate_moves: set[tuple[Square, Square]]
    autocompletions: list[str]
    promotion_prompt_position: Square | None

    submit_text: str | None


@dataclass(frozen=True)
class ViewerSessionView:
    lobby_id: LobbyId
    viewer_id: PlayerId
    viewer_role: ParticipantRole
    viewer_side: PlayerSide | None

    current_ply: int

    can_submit_for_side: PlayerSide | None
    can_offer_draw: bool
    can_accept_draw: bool
    can_resign: bool
    can_request_undo: bool

    status_text: str | None
    snapshot: AuthoritativeSnapshot
    preview_hints: MovePreviewHints | None = None

    connection_state: ConnectionState | None = None
