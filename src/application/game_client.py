from typing import Protocol

from src.application.command_types import CommandResult, GameEvent
from src.application.viewer_types import ViewerSessionView
from src.shared.ids import RequestId


class GameClient(Protocol):
    def get_view(self) -> ViewerSessionView:
        """Return the latest viewer-specific authoritative view."""
        ...

    def submit_move(
        self,
        move_text: str,
        *,
        request_id: RequestId,
        expected_ply: int,
        offer_draw: bool = False,
    ) -> CommandResult:
        """Submit a committed move for the current viewer."""
        ...

    def accept_draw_offer(
        self,
        *,
        request_id: RequestId,
        expected_ply: int,
    ) -> CommandResult:
        """Accept a pending draw offer if eligible."""
        ...

    def resign(
        self,
        *,
        request_id: RequestId,
    ) -> CommandResult:
        """Resign on behalf of the current viewer."""
        ...

    def request_undo(
        self,
        *,
        request_id: RequestId,
    ) -> CommandResult:
        """Request an undo if supported."""
        ...

    def events_since(self, last_seen_seq: int) -> list[GameEvent]:
        """Return events visible to this viewer after last_seen_seq."""
        ...

    def tick(self) -> None:
        """Advance clocks, bot state, or transport state."""
        ...
