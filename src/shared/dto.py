from pydantic import BaseModel, Field


class CreateLobbyRequestDTO(BaseModel):
    """Request payload for creating a lobby with two players."""

    white_player_id: str = Field(min_length=1)
    black_player_id: str = Field(min_length=1)


class CreateLobbyResponseDTO(BaseModel):
    """Response payload returned after a lobby is created."""

    lobby_id: str


class SubmitMoveRequestDTO(BaseModel):
    """Request payload for submitting a move command."""

    request_id: str = Field(min_length=1)
    expected_ply: int
    move_text: str = Field(min_length=1)
    offer_draw: bool = False


class ExpectedPlyCommandDTO(BaseModel):
    """Request payload for commands tied to a specific ply."""

    request_id: str = Field(min_length=1)
    expected_ply: int


class RequestIdCommandDTO(BaseModel):
    """Request payload for commands that only require idempotency."""

    request_id: str = Field(min_length=1)
