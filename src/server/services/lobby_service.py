from src.server.stores.memory_store import LobbyRecord, MemoryStore
from src.shared.ids import LobbyId, PlayerId


class LobbyNotFoundError(Exception):
    pass


class LobbyService:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def create_lobby(
        self,
        *,
        white_player_id: PlayerId,
        black_player_id: PlayerId,
    ) -> LobbyId:
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
        lobby = self.store.lobbies.get(lobby_id)
        if lobby is None:
            raise LobbyNotFoundError(f"Unknown lobby: {lobby_id}")
        return lobby
