import asyncio
from dataclasses import dataclass, field
from uuid import uuid4

from src.application.session import GameSession
from src.application.session_helpers.session_types import SessionConfig
from src.shared.ids import LobbyId, PlayerId
from src.shared.protocol_types import PlayerSide


@dataclass
class LobbyRecord:
    """
    In-memory representation of a game lobby and its participants.
    """

    lobby_id: LobbyId
    white_player_id: PlayerId
    black_player_id: PlayerId
    spectators: set[PlayerId] = field(default_factory=set)

    def side_for(self, player_id: PlayerId) -> PlayerSide | None:
        """
        Return the seated side for a player, if any.

        Spectators and unknown participants return None because they are not
        allowed to issue player-only game commands.
        """
        if player_id == self.white_player_id:
            return "white"
        if player_id == self.black_player_id:
            return "black"
        return None

    def contains(self, player_id: PlayerId) -> bool:
        """
        Return whether the player is part of this lobby.
        """
        return (
            player_id == self.white_player_id
            or player_id == self.black_player_id
            or player_id in self.spectators
        )


class MemoryStore:
    """
    In-memory backing store for lobbies, sessions, and per-lobby locks.

    This store is suitable for early development and tests; it does not provide
    persistence across process restarts.
    """

    def __init__(self) -> None:
        self.lobbies: dict[LobbyId, LobbyRecord] = {}
        self.sessions: dict[LobbyId, GameSession] = {}
        self.locks: dict[LobbyId, asyncio.Lock] = {}

    def new_lobby_id(self) -> LobbyId:
        """
        Generate a unique lobby ID for a new in-memory lobby.
        """
        return LobbyId(f"lobby_{uuid4().hex}")

    def lock_for(self, lobby_id: LobbyId) -> asyncio.Lock:
        """
        Return the asyncio lock associated with a lobby ID.
        """
        if lobby_id not in self.locks:
            self.locks[lobby_id] = asyncio.Lock()
        return self.locks[lobby_id]

    def create_session_for_lobby(self, lobby: LobbyRecord) -> GameSession:
        """
        Create and store an online game session for a lobby record.

        Preview hints are disabled for online mode at the moment. Before
        enabling hints, extra infrastructure needs to be created to ensure
        that MovePreviewHints DTOs can be reconstructed from JSON.
        """
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
