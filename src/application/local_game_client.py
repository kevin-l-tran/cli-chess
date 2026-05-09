from src.application.command_types import CommandResult
from src.application.game_client import GameClient
from src.application.session import GameSession
from src.application.session_helpers.session_types import TimeControl
from src.application.viewer_types import ViewerSessionView
from src.shared.ids import PlayerId, RequestId


class LocalGameClient(GameClient):
    """
    Async game client backed by an in-process GameSession.

    Methods return immediately but use the same awaitable interface as remote
    clients, keeping UI code independent of the execution mode.
    """

    def __init__(self, session: GameSession, viewer_id: PlayerId) -> None:
        """Store the in-process session and viewer identity for commands."""
        self.session = session
        self.viewer_id = viewer_id

    @classmethod
    def local(cls, *, time_control: TimeControl | None = None) -> "LocalGameClient":
        """
        Create a local same-client game with a synthetic local viewer.

        The returned client uses async methods even though all state changes are
        performed in process.
        """
        viewer_id = PlayerId("local")
        session = GameSession.local(time_control=time_control)
        return cls(session=session, viewer_id=viewer_id)

    async def get_view(self) -> ViewerSessionView:
        """Return the latest viewer-specific view from the local session."""
        return self.session.snapshot_for(self.viewer_id)

    async def submit_move(
        self,
        move_text: str,
        *,
        request_id: RequestId,
        expected_ply: int,
        offer_draw: bool = False,
    ) -> CommandResult:
        """Submit a move to the in-process session for the local viewer."""
        return self.session.submit_move(
            self.viewer_id,
            move_text,
            request_id=request_id,
            expected_ply=expected_ply,
            offer_draw=offer_draw,
        )

    async def accept_draw_offer(
        self,
        *,
        request_id: RequestId,
        expected_ply: int,
    ) -> CommandResult:
        """Accept a draw offer through the in-process session."""
        return self.session.accept_draw_offer(
            self.viewer_id,
            request_id=request_id,
            expected_ply=expected_ply,
        )

    async def resign(self, *, request_id: RequestId) -> CommandResult:
        """Resign the local session on behalf of the current viewer."""
        return self.session.resign(self.viewer_id, request_id=request_id)

    async def request_undo(self, *, request_id: RequestId) -> CommandResult:
        """Request an undo from the in-process session."""
        return self.session.request_undo(self.viewer_id, request_id=request_id)
