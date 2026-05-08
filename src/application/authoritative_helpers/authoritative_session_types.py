from dataclasses import dataclass
from typing import Literal

from src.application.viewer_types import FeedbackView, TerminalReason
from src.shared.ids import LobbyId, RequestId
from src.shared.protocol_types import CommandStatus, GameMode, PlayerSide, Square


UndoScope = Literal["halfmove", "fullmove"]
SessionPhaseKind = Literal["active", "concluded", "timed_out"]


@dataclass(frozen=True)
class TimeControl:
    initial_seconds: int
    increment_seconds: int = 0


@dataclass(frozen=True)
class TerminalState:
    winner: PlayerSide | None
    reason: TerminalReason


@dataclass(frozen=True)
class SessionPhase:
    kind: SessionPhaseKind
    side_to_move: PlayerSide | None
    terminal: TerminalState | None = None

    @property
    def is_game_over(self) -> bool:
        return self.kind in ("concluded", "timed_out")


@dataclass(frozen=True, init=False)
class AuthoritativeSessionConfig:
    lobby_id: LobbyId
    mode: GameMode
    time_control: TimeControl | None
    include_preview_hints: bool

    def __init__(
        self,
        lobby_id: LobbyId,
        mode: GameMode = "local",
        time_control: TimeControl | None = None,
        include_preview_hints: bool = True,
    ) -> None:
        object.__setattr__(self, "lobby_id", lobby_id)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "time_control", time_control)
        object.__setattr__(self, "include_preview_hints", include_preview_hints)

    @property
    def opponent(self) -> GameMode:
        return self.mode


@dataclass(frozen=True)
class CachedCommandResult:
    fingerprint: str
    ok: bool
    status: CommandStatus
    message: str | None


@dataclass(frozen=True)
class BotPendingState:
    request_id: RequestId | None = None
    side: PlayerSide | None = None


@dataclass
class CommittedSessionState:
    last_move_from: Square | None = None
    last_move_to: Square | None = None
    feedback: FeedbackView | None = None
