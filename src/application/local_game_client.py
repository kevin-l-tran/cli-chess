from src.application.game_client import GameClient
from src.application.session_helpers.session_types import (
    TimeControl,
)
from src.application.session import GameSession
from src.application.command_types import CommandResult
from src.application.viewer_types import ViewerSessionView
from src.shared.ids import PlayerId, RequestId


class LocalGameClient(GameClient):
    def __init__(self, session: GameSession, viewer_id: PlayerId) -> None:
        self.session = session
        self.viewer_id = viewer_id

    @classmethod
    def local(cls, *, time_control: TimeControl | None = None) -> "LocalGameClient":
        viewer_id = PlayerId("local")
        session = GameSession.local(time_control=time_control)
        return cls(session=session, viewer_id=viewer_id)

    def get_view(self) -> ViewerSessionView:
        return self.session.snapshot_for(self.viewer_id)

    def submit_move(
        self,
        move_text: str,
        *,
        request_id: RequestId,
        expected_ply: int,
        offer_draw: bool = False,
    ) -> CommandResult:
        return self.session.submit_move(
            self.viewer_id,
            move_text,
            request_id=request_id,
            expected_ply=expected_ply,
            offer_draw=offer_draw,
        )

    def accept_draw_offer(
        self, *, request_id: RequestId, expected_ply: int
    ) -> CommandResult:
        return self.session.accept_draw_offer(
            self.viewer_id,
            request_id=request_id,
            expected_ply=expected_ply,
        )

    def resign(self, *, request_id: RequestId) -> CommandResult:
        return self.session.resign(self.viewer_id, request_id=request_id)

    def request_undo(self, *, request_id: RequestId) -> CommandResult:
        return self.session.request_undo(self.viewer_id, request_id=request_id)
