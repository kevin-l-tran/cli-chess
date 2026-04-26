from dataclasses import dataclass
from typing import Literal

from src.engine.moves import Move


PlayerSide = Literal["white", "black"]
OpponentType = Literal["local", "bot"]


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
class Snapshot:
    board_glyphs: list[list[str]]
    turn_white: bool
    outcome: str
    last_move: Move | None
    legal_moves: set[Move]
    highlights: set[tuple[int, int]]
