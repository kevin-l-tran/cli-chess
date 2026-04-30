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


def freeze_clock(clock: ClockState | None) -> None:
    if clock is None:
        return
    clock.active_side = None
    clock.last_updated_ms = None


def advance_clock(
    clock: ClockState | None,
    now_ms: int,
    is_game_over: bool,
) -> bool:
    if clock is None or clock.active_side is None:
        return False

    if is_game_over or clock.timeout_side is not None:
        freeze_clock(clock)
        return False

    last = clock.last_updated_ms
    if last is None:
        clock.last_updated_ms = now_ms
        return False

    elapsed_ms = max(0, now_ms - last)
    if elapsed_ms == 0:
        return False

    if clock.active_side == "white":
        clock.white_remaining_ms = max(0, clock.white_remaining_ms - elapsed_ms)
        timed_out = clock.white_remaining_ms == 0
        if timed_out:
            clock.timeout_side = "white"
    else:
        clock.black_remaining_ms = max(0, clock.black_remaining_ms - elapsed_ms)
        timed_out = clock.black_remaining_ms == 0
        if timed_out:
            clock.timeout_side = "black"

    if timed_out:
        clock.active_side = None
        clock.last_updated_ms = None
        return True

    clock.last_updated_ms = now_ms
    return False
