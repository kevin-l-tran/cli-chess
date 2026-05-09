from fastapi import Header, HTTPException

from src.server.services.lobby_service import LobbyNotFoundError
from src.server.services.game_service import UnauthorizedLobbyAccessError
from src.shared.ids import PlayerId


def require_player_id(x_player_id: str | None = Header(default=None)) -> PlayerId:
    if not x_player_id:
        raise HTTPException(
            status_code=401,
            detail="Missing X-Player-Id header.",
        )
    return PlayerId(x_player_id)


def map_domain_error(error: Exception) -> HTTPException:
    if isinstance(error, LobbyNotFoundError):
        return HTTPException(status_code=404, detail=str(error))

    if isinstance(error, UnauthorizedLobbyAccessError):
        return HTTPException(status_code=403, detail=str(error))

    return HTTPException(status_code=500, detail="Internal server error.")
