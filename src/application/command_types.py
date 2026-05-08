from dataclasses import dataclass

from src.application.viewer_types import ViewerSessionView
from src.shared.ids import PlayerId
from src.shared.protocol_types import CommandStatus, GameEventKind, PlayerSide


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    status: CommandStatus
    message: str | None = None
    event_seq: int | None = None
    view: ViewerSessionView | None = None


@dataclass(frozen=True)
class GameEvent:
    seq: int
    kind: GameEventKind
    ply: int
    actor: PlayerId | None
    side: PlayerSide | None
    move_text: str | None = None
    message: str | None = None
