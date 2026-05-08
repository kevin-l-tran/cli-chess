from dataclasses import dataclass

from src.application.viewer_types import ViewerSessionView
from src.shared.ids import PlayerId
from src.shared.protocol_types import GameEventKind, PlayerSide


@dataclass(frozen=True)
class GameEvent:
    seq: int
    kind: GameEventKind
    ply: int
    actor: PlayerId | None
    side: PlayerSide | None
    move_text: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class EventBatch:
    events: list[GameEvent]
    view: ViewerSessionView
    from_seq: int
    to_seq: int
