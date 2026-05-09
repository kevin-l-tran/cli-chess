from fastapi import APIRouter, Depends

from src.shared.dto import (
    ExpectedPlyCommandDTO,
    RequestIdCommandDTO,
    SubmitMoveRequestDTO,
)
from src.server.routes.helpers import map_domain_error, require_player_id
from src.server.serialization import to_jsonable
from src.server.services.game_service import ServerGameService
from src.shared.ids import LobbyId, PlayerId, RequestId


def make_game_router(game_service: ServerGameService) -> APIRouter:
    """
    Build the FastAPI router for game-specific lobby endpoints.

    The returned router delegates all authoritative game behavior to the
    provided server game service and only handles request/response translation.
    """
    router = APIRouter(prefix="/lobbies/{lobby_id}", tags=["games"])

    @router.get("/view")
    async def get_view(
        lobby_id: str,
        player_id: PlayerId = Depends(require_player_id),
    ):
        """
        Return the latest viewer-specific game view for a lobby.

        The authenticated player may be a player or spectator, subject to the
        service's lobby access checks.
        """
        try:
            view = await game_service.get_view(
                lobby_id=LobbyId(lobby_id),
                viewer_id=player_id,
            )
            return to_jsonable(view)
        except Exception as error:
            raise map_domain_error(error)

    @router.post("/moves")
    async def submit_move(
        lobby_id: str,
        dto: SubmitMoveRequestDTO,
        player_id: PlayerId = Depends(require_player_id),
    ):
        """
        Submit a move command for the authenticated player.

        The route converts wire DTO fields to domain IDs and delegates move
        validation, idempotency, and state mutation to the service layer.
        """
        try:
            result = await game_service.submit_move(
                lobby_id=LobbyId(lobby_id),
                player_id=player_id,
                request_id=RequestId(dto.request_id),
                expected_ply=dto.expected_ply,
                move_text=dto.move_text,
                offer_draw=dto.offer_draw,
            )
            return to_jsonable(result)
        except Exception as error:
            raise map_domain_error(error)

    @router.post("/draw/accept")
    async def accept_draw_offer(
        lobby_id: str,
        dto: ExpectedPlyCommandDTO,
        player_id: PlayerId = Depends(require_player_id),
    ):
        """
        Accept a pending draw offer in the target lobby.

        The expected ply guards against accepting a draw offer against a stale
        client position.
        """
        try:
            result = await game_service.accept_draw_offer(
                lobby_id=LobbyId(lobby_id),
                player_id=player_id,
                request_id=RequestId(dto.request_id),
                expected_ply=dto.expected_ply,
            )
            return to_jsonable(result)
        except Exception as error:
            raise map_domain_error(error)

    @router.post("/resign")
    async def resign(
        lobby_id: str,
        dto: RequestIdCommandDTO,
        player_id: PlayerId = Depends(require_player_id),
    ):
        """
        Resign the active game on behalf of the authenticated player.

        The request ID lets the service treat retries as idempotent commands.
        """
        try:
            result = await game_service.resign(
                lobby_id=LobbyId(lobby_id),
                player_id=player_id,
                request_id=RequestId(dto.request_id),
            )
            return to_jsonable(result)
        except Exception as error:
            raise map_domain_error(error)

    @router.post("/undo")
    async def request_undo(
        lobby_id: str,
        dto: RequestIdCommandDTO,
        player_id: PlayerId = Depends(require_player_id),
    ):
        """
        Request an undo for the authenticated player.

        Online undo availability is determined by the service/session policy,
        not by the route handler.
        """
        try:
            result = await game_service.request_undo(
                lobby_id=LobbyId(lobby_id),
                player_id=player_id,
                request_id=RequestId(dto.request_id),
            )
            return to_jsonable(result)
        except Exception as error:
            raise map_domain_error(error)

    return router
