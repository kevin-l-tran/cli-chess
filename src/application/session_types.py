from dataclasses import dataclass
from typing import Literal


Square = tuple[int, int]
ParseStatus = Literal["empty", "no_match", "ambiguous", "resolved"]
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
DrawActionStatus = Literal[
    "accepted",
    "declined",
    "unavailable",
    "game_over",
    "error",
]
UndoStatus = Literal["undone", "unavailable", "error"]
UndoScope = Literal["halfmove", "fullmove"]
ResignStatus = Literal["resigned", "game_over", "error"]
SessionPhaseKind = Literal["active", "concluded", "timed_out"]
TerminalReason = Literal["draw", "timeout", "checkmate", "resignation"]
FeedbackKind = Literal["error", "action"]


@dataclass(frozen=True)
class TerminalState:
    """
    Application-level terminal outcome for a session.

    Attributes:
        winner (PlayerSide | None):
            Winning side, or `None` for a draw.

        reason (TerminalReason):
            Reason the session ended.
    """

    winner: PlayerSide | None
    reason: TerminalReason


@dataclass(frozen=True)
class SessionPhase:
    """
    Application-level phase of a session.

    Attributes:
        kind (SessionPhaseKind):
            High-level phase classification for the session.

        side_to_move (PlayerSide | None):
            Side to move while the session is active, or `None` when terminal.

        terminal (TerminalState | None):
            Terminal outcome data when the session has ended.
    """

    kind: SessionPhaseKind
    side_to_move: PlayerSide | None
    terminal: TerminalState | None = None

    @property
    def is_game_over(self) -> bool:
        return self.kind in ("concluded", "timed_out")


@dataclass(frozen=True)
class SessionAvailability:
    """
    UI-facing action availability flags derived for the current session state.

    Each field indicates whether the corresponding action should currently be
    offered by the presentation layer.
    """

    can_confirm_move: bool
    can_undo_halfmove: bool
    can_undo_fullmove: bool
    can_resign: bool


@dataclass(frozen=True)
class TimeControl:
    """
    Chess-clock configuration for a session.

    Attributes:
        initial_seconds (int):
            Starting time for each side.

        increment_seconds (int):
            Time added to the mover's clock after each committed move.
    """

    initial_seconds: int
    increment_seconds: int = 0


@dataclass(frozen=True)
class SessionConfig:
    """
    Startup configuration for a chess session.

    Attributes:
        player_side (PlayerSide):
            The side associated with the local player for session-level policy or
            presentation concerns.

        opponent (OpponentType):
            The opponent mode for the session.

            - "local": two players share the same client
            - "bot": a local human plays against an engine-controlled opponent
            - "online": a local human plays a remote opponent

        time_control (TimeControl | None):
            Optional chess-clock settings for the session. `None` means untimed.
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
class Snapshot:
    """
    Render-ready view of the current session state.

    Attributes:
        board_glyphs (list[list[str]]):
            8x8 matrix of piece and empty-square glyphs in board-render order.

        side_to_move (PlayerSide | None):
            The side to move in the current position, or `None` when the session is
            terminal.

        candidate_moves (set[tuple[Square, Square]]):
            `(from_square, to_square)` pairs highlighted from the current parse
            result.

        last_move_from (Square | None):
            Origin square of the most recently applied move, if any.

        last_move_to (Square | None):
            Destination square of the most recently applied move, if any.

        move_list (list[MoveListItem]):
            Render-friendly move history entries.

        move_draft (MoveDraftView):
            The current move-input text plus its parse state.

        move_autocompletions (list[str]):
            Matching move spellings for the current draft prefix.

        promotion_prompt_position (Square | None):
            Anchor square for the promotion picker when the current ambiguity is only
            the promotion piece.

        check_square (Square | None):
            Square of the checked king for the side to move, if any.

        is_player_checked (bool):
            Whether the side to move is currently in check.

        is_game_over (bool):
            Whether the session is terminal.

        can_confirm_move (bool):
            Whether the current draft can be confirmed as a move.

        can_undo_fullmove (bool):
            Whether a fullmove undo is available.

        can_undo_halfmove (bool):
            Whether a halfmove undo is available.

        can_resign (bool):
            Whether resignation is currently available.

        is_promotion_pending (bool):
            Whether the current draft is waiting on a promotion-piece choice.

        timed_game (TimedGameView | None):
            Render-ready clock state for timed games, or `None` for untimed games.

        outcome (OutcomeView | None):
            Terminal outcome data for concluded sessions, or `None` while the game is
            still active.

        feedback (FeedbackView | None):
            Most recent user-facing action or failure message, if any.
    """

    board_glyphs: list[list[str]]
    side_to_move: PlayerSide | None
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

    timed_game: TimedGameView | None

    outcome: OutcomeView | None
    feedback: FeedbackView | None


@dataclass(frozen=True)
class MoveAttemptResult:
    """
    Stable result returned by `GameSession.confirm_move_draft()`.

    Attributes:
        ok (bool):
            Whether the move was successfully applied.

        status (MoveAttemptStatus):
            Machine-friendly outcome code for the attempt.
    """

    ok: bool
    status: MoveAttemptStatus


@dataclass(frozen=True)
class UndoResult:
    """
    Stable result returned by `GameSession.undo()`.

    Attributes:
        ok (bool):
            Whether undo succeeded.

        status (UndoStatus):
            Machine-friendly outcome code for the attempt.
    """

    ok: bool
    status: UndoStatus


@dataclass(frozen=True)
class ResignResult:
    """
    Stable result returned by `GameSession.resign()`.

    Attributes:
        ok (bool):
            Whether resignation succeeded.

        status (ResignStatus):
            Machine-friendly outcome code for the attempt.
    """

    ok: bool
    status: ResignStatus


@dataclass(frozen=True)
class DrawActionResult:
    """
    Stable result returned by `GameSession.handle_draw_offer()`.

    Attributes:
        ok (bool):
            Whether the draw offer handle succeeded.

        status (DrawActionStatus):
            Machine-friendly outcome code for the attempt.
    """

    ok: bool
    status: DrawActionStatus
