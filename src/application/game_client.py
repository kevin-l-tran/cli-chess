from typing import Protocol

from src.application.command_types import CommandResult
from src.application.viewer_types import ViewerSessionView
from src.shared.ids import RequestId


class GameClient(Protocol):
    """
    Async UI-facing interface for committed game state and commands.

    Implementations may be local, bot-backed, or remote. Local clients can
    return immediately, while remote clients can await network I/O.
    """

    async def get_view(self) -> ViewerSessionView:
        """Return the latest viewer-specific authoritative view."""
        ...

    async def submit_move(
        self,
        move_text: str,
        *,
        request_id: RequestId,
        expected_ply: int,
        offer_draw: bool = False,
    ) -> CommandResult:
        """Submit a committed move for the current viewer."""
        ...

    async def accept_draw_offer(
        self,
        *,
        request_id: RequestId,
        expected_ply: int,
    ) -> CommandResult:
        """Accept a pending draw offer if eligible."""
        ...

    async def resign(
        self,
        *,
        request_id: RequestId,
    ) -> CommandResult:
        """Resign on behalf of the current viewer."""
        ...

    async def request_undo(
        self,
        *,
        request_id: RequestId,
    ) -> CommandResult:
        """Request an undo if supported."""
        ...
