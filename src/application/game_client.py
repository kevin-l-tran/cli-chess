from typing import Protocol

from src.application.command_types import CommandResult, GameEvent
from src.application.viewer_types import ViewerSessionView
from src.shared.ids import RequestId


class GameClient(Protocol):
    def get_view(self) -> ViewerSessionView: ...
    def submit_move(
        self,
        move_text: str,
        *,
        request_id: RequestId,
        expected_ply: int,
        offer_draw: bool = False,
    ) -> CommandResult: ...
    def accept_draw_offer(
        self, *, request_id: RequestId, expected_ply: int
    ) -> CommandResult: ...
    def resign(self, *, request_id: RequestId) -> CommandResult: ...
    def request_undo(self, *, request_id: RequestId) -> CommandResult: ...
    def events_since(self, last_seen_seq: int) -> list[GameEvent]: ...
    def tick(self) -> None: ...
