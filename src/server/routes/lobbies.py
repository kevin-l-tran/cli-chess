from fastapi import APIRouter

from src.shared.dto import CreateLobbyRequestDTO, CreateLobbyResponseDTO
from src.server.services.lobby_service import LobbyService
from src.server.routes.helpers import map_domain_error
from src.server.serialization import to_jsonable
from src.shared.ids import LobbyId, PlayerId


def make_lobby_router(lobby_service: LobbyService) -> APIRouter:
    router = APIRouter(prefix="/lobbies", tags=["lobbies"])

    @router.post("", response_model=CreateLobbyResponseDTO)
    def create_lobby(dto: CreateLobbyRequestDTO) -> CreateLobbyResponseDTO:
        lobby_id = lobby_service.create_lobby(
            white_player_id=PlayerId(dto.white_player_id),
            black_player_id=PlayerId(dto.black_player_id),
        )
        return CreateLobbyResponseDTO(lobby_id=str(lobby_id))

    @router.get("/{lobby_id}")
    def get_lobby(lobby_id: str):
        try:
            lobby = lobby_service.get_lobby(LobbyId(lobby_id))
            return to_jsonable(lobby)
        except Exception as error:
            raise map_domain_error(error)

    return router
