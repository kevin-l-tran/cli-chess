from dataclasses import dataclass

from src.application.command_types import GameEvent
from src.application.viewer_types import ViewerSessionView


@dataclass(frozen=True)
class EventBatch:
    events: list[GameEvent]
    view: ViewerSessionView
    from_seq: int
    to_seq: int
