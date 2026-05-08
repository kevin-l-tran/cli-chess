import time

from dataclasses import dataclass, field
from typing import Callable

from src.shared.protocol_types import PlayerSide

from .authoritative_session_types import TimeControl


TimeSource = Callable[[], int]


def system_time_ms() -> int:
    return time.monotonic_ns() // 1_000_000


@dataclass(frozen=True)
class ClockFrame:
    white_remaining_ms: int
    black_remaining_ms: int
    active_side: PlayerSide | None
    timeout_side: PlayerSide | None


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
    *,
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


@dataclass
class SessionTiming:
    clock_state: ClockState | None
    time_control: TimeControl | None
    time_source: TimeSource

    def sync(self, *, engine_game_over: bool) -> bool:
        return advance_clock(
            self.clock_state,
            now_ms=self.time_source(),
            is_game_over=engine_game_over,
        )

    def timeout_side(self) -> PlayerSide | None:
        if self.clock_state is None:
            return None
        return self.clock_state.timeout_side

    def freeze(self) -> None:
        freeze_clock(self.clock_state)

    def push_frame(self) -> None:
        clock = self.clock_state
        if clock is None:
            return
        clock.history.append(
            ClockFrame(
                white_remaining_ms=clock.white_remaining_ms,
                black_remaining_ms=clock.black_remaining_ms,
                active_side=clock.active_side,
                timeout_side=clock.timeout_side,
            )
        )

    def pop_frame(self) -> None:
        clock = self.clock_state
        if clock is None or not clock.history:
            return
        frame = clock.history.pop()
        clock.white_remaining_ms = frame.white_remaining_ms
        clock.black_remaining_ms = frame.black_remaining_ms
        clock.active_side = frame.active_side
        clock.timeout_side = frame.timeout_side
        clock.last_updated_ms = None

    def on_move_committed(self, *, next_side: PlayerSide) -> None:
        clock = self.clock_state
        time_control = self.time_control
        if clock is None or time_control is None:
            return

        mover = "black" if next_side == "white" else "white"
        increment_ms = time_control.increment_seconds * 1000
        if mover == "white":
            clock.white_remaining_ms += increment_ms
        else:
            clock.black_remaining_ms += increment_ms

        clock.active_side = next_side
        clock.timeout_side = None
        clock.last_updated_ms = self.time_source()

    def on_position_ready(
        self,
        *,
        side_to_move: PlayerSide,
        engine_game_over: bool,
    ) -> None:
        clock = self.clock_state
        if clock is None:
            return
        if engine_game_over or clock.timeout_side is not None:
            self.freeze()
            return
        clock.active_side = side_to_move
        if clock.last_updated_ms is None:
            clock.last_updated_ms = self.time_source()
