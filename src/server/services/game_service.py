from src.application.command_types import CommandResult
from src.application.viewer_types import ViewerSessionView
from src.server.services.lobby_service import LobbyNotFoundError
from src.server.stores.memory_store import MemoryStore
from src.shared.ids import LobbyId, PlayerId, RequestId


class UnauthorizedLobbyAccessError(Exception):
    """
    Raised when a viewer or player is not authorized for a lobby.

    This separates access-control failures from missing-lobby failures so route
    helpers can map each case to the appropriate HTTP response.
    """


class ServerGameService:
    """
    Coordinates online game commands against in-memory lobby sessions.

    The service enforces lobby membership, serializes per-lobby mutations with
    locks, and delegates chess-specific behavior to the application session.
    """

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def _get_session(self, lobby_id: LobbyId):
        session = self.store.sessions.get(lobby_id)
        if session is None:
            raise LobbyNotFoundError(f"Unknown lobby: {lobby_id}")
        return session

    def _authorize_viewer(self, lobby_id: LobbyId, viewer_id: PlayerId) -> None:
        lobby = self.store.lobbies.get(lobby_id)
        if lobby is None:
            raise LobbyNotFoundError(f"Unknown lobby: {lobby_id}")

        if not lobby.contains(viewer_id):
            raise UnauthorizedLobbyAccessError(
                f"Player {viewer_id} is not in lobby {lobby_id}"
            )

    def _authorize_player(self, lobby_id: LobbyId, player_id: PlayerId) -> None:
        lobby = self.store.lobbies.get(lobby_id)
        if lobby is None:
            raise LobbyNotFoundError(f"Unknown lobby: {lobby_id}")

        if lobby.side_for(player_id) is None:
            raise UnauthorizedLobbyAccessError(
                f"Player {player_id} is not a player in lobby {lobby_id}"
            )

    async def get_view(
        self,
        *,
        lobby_id: LobbyId,
        viewer_id: PlayerId,
    ) -> ViewerSessionView:
        """
        Return the current viewer-specific session view for a lobby.

        The method authorizes players and spectators, then reads the snapshot
        under the lobby lock because clock synchronization can mutate state.
        """
        self._authorize_viewer(lobby_id, viewer_id)
        session = self._get_session(lobby_id)

        # snapshot_for may sync clocks, so keep it serialized with commands.
        async with self.store.lock_for(lobby_id):
            return session.snapshot_for(viewer_id, connection_state="connected")

    async def submit_move(
        self,
        *,
        lobby_id: LobbyId,
        player_id: PlayerId,
        request_id: RequestId,
        expected_ply: int,
        move_text: str,
        offer_draw: bool = False,
    ) -> CommandResult:
        """
        Submit a move command for a player in a lobby.

        Authorization happens before acquiring the lobby lock; the session then
        validates turn order, stale ply, move legality, and request idempotency.
        """
        self._authorize_player(lobby_id, player_id)

        async with self.store.lock_for(lobby_id):
            session = self._get_session(lobby_id)
            return session.submit_move(
                player_id,
                move_text,
                request_id=request_id,
                expected_ply=expected_ply,
                offer_draw=offer_draw,
            )

    async def accept_draw_offer(
        self,
        *,
        lobby_id: LobbyId,
        player_id: PlayerId,
        request_id: RequestId,
        expected_ply: int,
    ) -> CommandResult:
        """
        Accept the opponent's pending draw offer for a lobby game.

        The session applies draw availability rules and returns a fresh command
        result with the caller's updated view.
        """
        self._authorize_player(lobby_id, player_id)

        async with self.store.lock_for(lobby_id):
            session = self._get_session(lobby_id)
            return session.accept_draw_offer(
                player_id,
                request_id=request_id,
                expected_ply=expected_ply,
            )

    async def resign(
        self,
        *,
        lobby_id: LobbyId,
        player_id: PlayerId,
        request_id: RequestId,
    ) -> CommandResult:
        """
        Resign the current game for a lobby player.

        The operation is serialized with other lobby commands so resignation
        cannot race with move submission or draw acceptance.
        """
        self._authorize_player(lobby_id, player_id)

        async with self.store.lock_for(lobby_id):
            session = self._get_session(lobby_id)
            return session.resign(player_id, request_id=request_id)

    async def request_undo(
        self,
        *,
        lobby_id: LobbyId,
        player_id: PlayerId,
        request_id: RequestId,
    ) -> CommandResult:
        """
        Request an undo through the authoritative session policy.

        The service only authorizes and serializes the command; the session
        decides whether undo is available for the configured game mode.
        """
        self._authorize_player(lobby_id, player_id)

        async with self.store.lock_for(lobby_id):
            session = self._get_session(lobby_id)
            return session.request_undo(player_id, request_id=request_id)
