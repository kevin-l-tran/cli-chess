from pydantic import BaseModel, Field


class CreateLobbyRequestDTO(BaseModel):
    white_player_id: str = Field(min_length=1)
    black_player_id: str = Field(min_length=1)


class CreateLobbyResponseDTO(BaseModel):
    lobby_id: str


class SubmitMoveRequestDTO(BaseModel):
    request_id: str = Field(min_length=1)
    expected_ply: int
    move_text: str = Field(min_length=1)
    offer_draw: bool = False


class ExpectedPlyCommandDTO(BaseModel):
    request_id: str = Field(min_length=1)
    expected_ply: int


class RequestIdCommandDTO(BaseModel):
    request_id: str = Field(min_length=1)
