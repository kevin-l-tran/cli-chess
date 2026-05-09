import asyncio
from dataclasses import dataclass, field
from uuid import uuid4

from src.application.session import GameSession
from src.application.session_helpers.session_types import SessionConfig
from src.shared.ids import LobbyId, PlayerId
from src.shared.protocol_types import PlayerSide


@dataclass
class LobbyRecord:
    lobby_id: LobbyId
    white_player_id: PlayerId
    black_player_id: PlayerId
    spectators: set[PlayerId] = field(default_factory=set)

    def side_for(self, player_id: PlayerId) -> PlayerSide | None:
        if player_id == self.white_player_id:
            return "white"
        if player_id == self.black_player_id:
            return "black"
        return None

    def contains(self, player_id: PlayerId) -> bool:
        return (
            player_id == self.white_player_id
            or player_id == self.black_player_id
            or player_id in self.spectators
        )


class MemoryStore:
    def __init__(self) -> None:
        self.lobbies: dict[LobbyId, LobbyRecord] = {}
        self.sessions: dict[LobbyId, GameSession] = {}
        self.locks: dict[LobbyId, asyncio.Lock] = {}

    def new_lobby_id(self) -> LobbyId:
        return LobbyId(f"lobby_{uuid4().hex}")

    def lock_for(self, lobby_id: LobbyId) -> asyncio.Lock:
        if lobby_id not in self.locks:
            self.locks[lobby_id] = asyncio.Lock()
        return self.locks[lobby_id]

    def create_session_for_lobby(self, lobby: LobbyRecord) -> GameSession:
        session = GameSession(
            SessionConfig(
                lobby_id=lobby.lobby_id,
                mode="online",
                include_preview_hints=False,
            ),
            player_sides={
                lobby.white_player_id: "white",
                lobby.black_player_id: "black",
            },
        )
        self.sessions[lobby.lobby_id] = session
        return session
