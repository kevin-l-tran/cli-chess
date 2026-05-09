from src.server.stores.memory_store import LobbyRecord, MemoryStore
from src.shared.ids import LobbyId, PlayerId


class LobbyNotFoundError(Exception):
    """
    Raised when a requested lobby ID is not present in the store.

    Route helpers can translate this domain error into the API's missing-lobby
    HTTP response without exposing storage details.
    """


class LobbyService:
    """
    Provides lobby creation and lookup operations over the backing store.

    Creating a lobby also initializes its associated authoritative game session
    and per-lobby lock so game routes can operate immediately.
    """

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def create_lobby(
        self,
        *,
        white_player_id: PlayerId,
        black_player_id: PlayerId,
    ) -> LobbyId:
        """
        Create a lobby for the supplied white and black players.

        The new lobby is stored, paired with a fresh online game session, and
        returned by its generated lobby ID.
        """
        lobby_id = self.store.new_lobby_id()
        lobby = LobbyRecord(
            lobby_id=lobby_id,
            white_player_id=white_player_id,
            black_player_id=black_player_id,
        )

        self.store.lobbies[lobby_id] = lobby
        self.store.create_session_for_lobby(lobby)
        self.store.lock_for(lobby_id)

        return lobby_id

    def get_lobby(self, lobby_id: LobbyId) -> LobbyRecord:
        """
        Return the stored lobby record for a lobby ID.

        Raises LobbyNotFoundError when the ID is unknown to the backing store.
        """
        lobby = self.store.lobbies.get(lobby_id)
        if lobby is None:
            raise LobbyNotFoundError(f"Unknown lobby: {lobby_id}")
        return lobby
