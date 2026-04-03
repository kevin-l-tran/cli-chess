from dataclasses import dataclass
from typing import Literal


PlayerSide = Literal["white", "black"]
OpponentType = Literal["local", "bot"]
Square = tuple[int, int]


@dataclass(frozen=True)
class TimeControl:
    initial_seconds: int
    increment_seconds: int = 0


@dataclass(frozen=True)
class SessionConfig:
    player_side: PlayerSide
    opponent: OpponentType = "local"
    time_control: TimeControl | None = None


@dataclass(frozen=True)
class MoveListItem:
    ply: int
    notation: str


@dataclass(frozen=True)
class Snapshot:
    board_glyphs: list[list[str]]
    side_to_move: PlayerSide
    flipped: bool

    cursor: Square | None
    selected: Square | None
    legal_targets: set[Square]

    last_move_from: Square | None
    last_move_to: Square | None
    check_square: Square | None

    move_list: list[MoveListItem]

    status_text: str
    outcome_banner: str | None
    last_error_message: str | None
