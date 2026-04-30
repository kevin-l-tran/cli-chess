from dataclasses import dataclass, field
import time
from typing import Callable

from .session_types import PlayerSide

TimeSource = Callable[[], int]


def system_time_ms() -> int:
    return time.monotonic_ns() // 1_000_000


@dataclass(frozen=True)
class ClockFrame:
    white_remaining_ms: int
    black_remaining_ms: int
    active_side: PlayerSide | None
    timeout_side: PlayerSide | None
    last_updated_ms: int | None


@dataclass
class ClockState:
    white_remaining_ms: int
    black_remaining_ms: int
    active_side: PlayerSide | None
    timeout_side: PlayerSide | None
    last_updated_ms: int | None
    history: list[ClockFrame] = field(default_factory=list)
